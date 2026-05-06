"""
Full authentication router:
  POST /login            — email+password, returns JWT or TOTP challenge
  POST /totp/verify      — completes TOTP step, returns full JWT
  POST /totp/setup       — generate new TOTP secret (QR + backup codes)
  POST /totp/enable      — confirm TOTP code and activate 2FA
  POST /totp/disable     — deactivate 2FA after password confirmation
  POST /logout           — invalidate refresh token / session
  POST /password-reset/request  — send reset email
  POST /password-reset/confirm  — set new password via token
  POST /accept-invite    — accept domain invite, set password
  GET  /login-activity   — last 20 login events for current user
  GET  /sessions         — active sessions
  DELETE /sessions/{id}  — revoke a session
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db
from backend.config import settings
from backend.core.security import (
    create_token,
    hash_password,
    verify_password,
)
from backend.models.all_models import (
    AuditLog,
    DomainInvite,
    LoginActivity,
    Mailbox,
    PasswordResetToken,
    Session,
    TotpSecret,
    User,
)

router = APIRouter(tags=["auth"])

# ─── Pydantic schemas ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    requires_totp: bool = False
    temp_token: str | None = None
    access_token: str | None = None
    token_type: str = "bearer"
    role: str | None = None


class TotpVerifyRequest(BaseModel):
    temp_token: str
    code: str = Field(min_length=6, max_length=8)


class TotpEnableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TotpDisableRequest(BaseModel):
    password: str


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetConfirmBody(BaseModel):
    token: str
    password: str = Field(min_length=8)


class AcceptInviteBody(BaseModel):
    token: str
    password: str = Field(min_length=8)


class TotpSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: list[str]


class SessionItem(BaseModel):
    id: str
    ip_address: str | None
    created_at: str
    expires_at: str | None


class LoginActivityItem(BaseModel):
    id: str
    ip_address: str | None
    user_agent: str | None
    device_type: str | None
    success: bool | None
    failure_reason: str | None
    created_at: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_access_token(user: User) -> str:
    return create_token(
        str(user.id),
        timedelta(minutes=settings.access_token_expire_minutes),
        extra={"role": user.role, "email": user.email},
    )


def _make_temp_token(user_id: str) -> str:
    """Short-lived token used only to complete TOTP verification."""
    return create_token(user_id, timedelta(minutes=5), extra={"totp_pending": True})


async def _log_activity(
    db: AsyncSession,
    user_id: str,
    request: Request,
    success: bool,
    failure_reason: str | None = None,
) -> None:
    ua = request.headers.get("user-agent", "")[:500]
    ip = request.client.host if request.client else None
    device = "mobile" if "Mobile" in ua else "desktop"
    db.add(
        LoginActivity(
            user_id=user_id,  # type: ignore[arg-type]
            ip_address=ip,
            user_agent=ua,
            device_type=device,
            success=success,
            failure_reason=failure_reason,
        )
    )
    db.add(
        AuditLog(
            user_id=user_id,  # type: ignore[arg-type]
            action="login_success" if success else "login_failed",
            ip_address=ip,
            user_agent=ua,
        )
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    # Look up user by email
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user: User | None = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        if user:
            await _log_activity(db, str(user.id), request, success=False, failure_reason="bad_password")
            await db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    # Check TOTP
    totp_row: TotpSecret | None = (
        await db.execute(select(TotpSecret).where(TotpSecret.user_id == user.id))
    ).scalar_one_or_none()

    if totp_row and totp_row.is_enabled:
        await _log_activity(db, str(user.id), request, success=False, failure_reason="totp_required")
        await db.commit()
        return LoginResponse(requires_totp=True, temp_token=_make_temp_token(str(user.id)))

    await _log_activity(db, str(user.id), request, success=True)
    await db.commit()
    return LoginResponse(
        access_token=_make_access_token(user),
        role=user.role,
    )


@router.post("/totp/verify", response_model=LoginResponse)
async def totp_verify(
    payload: TotpVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    from jose import JWTError
    from backend.core.security import decode_token

    try:
        data = decode_token(payload.temp_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired temp token.")

    if not data.get("totp_pending"):
        raise HTTPException(status_code=400, detail="Not a TOTP challenge token.")

    user_id = data["sub"]
    user: User | None = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    totp_row: TotpSecret | None = (
        await db.execute(select(TotpSecret).where(TotpSecret.user_id == user.id))
    ).scalar_one_or_none()

    if not totp_row or not totp_row.is_enabled:
        raise HTTPException(status_code=400, detail="TOTP not configured.")

    # Accept 6-digit TOTP or 8-char backup code
    totp = pyotp.TOTP(totp_row.secret)
    valid = totp.verify(payload.code, valid_window=1)
    if not valid and payload.code in (totp_row.backup_codes or []):
        # consume backup code
        remaining = [c for c in totp_row.backup_codes if c != payload.code]
        totp_row.backup_codes = remaining
        valid = True

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid TOTP code.")

    await db.commit()
    return LoginResponse(access_token=_make_access_token(user), role=user.role)


@router.post("/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TotpSetupResponse:
    user: User = (
        await db.execute(select(User).where(User.id == current_user["id"]))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    qr_uri = totp.provisioning_uri(name=user.email, issuer_name="Nex Mail")
    backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]

    existing: TotpSecret | None = (
        await db.execute(select(TotpSecret).where(TotpSecret.user_id == user.id))
    ).scalar_one_or_none()
    if existing:
        existing.secret = secret
        existing.backup_codes = backup_codes
        existing.is_enabled = False
    else:
        db.add(TotpSecret(user_id=user.id, secret=secret, backup_codes=backup_codes))
    await db.commit()
    return TotpSetupResponse(secret=secret, qr_uri=qr_uri, backup_codes=backup_codes)


@router.post("/totp/enable")
async def totp_enable(
    payload: TotpEnableRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    totp_row: TotpSecret | None = (
        await db.execute(select(TotpSecret).where(TotpSecret.user_id == current_user["id"]))
    ).scalar_one_or_none()
    if not totp_row or not totp_row.secret:
        raise HTTPException(status_code=400, detail="Call /totp/setup first.")
    if not pyotp.TOTP(totp_row.secret).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code.")
    totp_row.is_enabled = True
    await db.commit()
    return {"detail": "2FA enabled."}


@router.post("/totp/disable")
async def totp_disable(
    payload: TotpDisableRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user: User = (
        await db.execute(select(User).where(User.id == current_user["id"]))
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password.")
    totp_row: TotpSecret | None = (
        await db.execute(select(TotpSecret).where(TotpSecret.user_id == user.id))
    ).scalar_one_or_none()
    if totp_row:
        totp_row.is_enabled = False
    await db.commit()
    return {"detail": "2FA disabled."}


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Revoke all sessions for this user
    sessions = (
        await db.execute(select(Session).where(Session.user_id == current_user["id"]))
    ).scalars().all()
    for s in sessions:
        await db.delete(s)
    await db.commit()
    return {"detail": "Logged out."}


@router.post("/password-reset/request")
async def password_reset_request(
    payload: PasswordResetRequestBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user: User | None = (
        await db.execute(select(User).where(User.email == payload.email.lower()))
    ).scalar_one_or_none()
    # Always return success to avoid user enumeration
    if user:
        token = secrets.token_urlsafe(48)
        expires = datetime.now(tz=timezone.utc) + timedelta(hours=2)
        db.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires))
        await db.commit()
        # TODO: dispatch email via Celery send_reset_email.delay(user.email, token)
    return {"detail": "If that email exists, a reset link was sent."}


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    payload: PasswordResetConfirmBody,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row: PasswordResetToken | None = (
        await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token == payload.token,
                PasswordResetToken.used_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=400, detail="Invalid or already-used token.")
    if row.expires_at and row.expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired.")

    user: User | None = (
        await db.execute(select(User).where(User.id == row.user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = hash_password(payload.password)
    row.used_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return {"detail": "Password updated. You can now log in."}


@router.post("/accept-invite", response_model=LoginResponse)
async def accept_invite(
    payload: AcceptInviteBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    invite: DomainInvite | None = (
        await db.execute(
            select(DomainInvite).where(
                DomainInvite.token == payload.token,
                DomainInvite.accepted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or already-used invite.")
    if invite.expires_at and invite.expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=400, detail="Invite has expired.")

    # Create user + mailbox
    existing = (
        await db.execute(select(User).where(User.email == invite.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Account already exists.")

    user = User(email=invite.email, hashed_password=hash_password(payload.password), role="user")
    db.add(user)
    await db.flush()

    domain_part = invite.email.split("@")[1] if "@" in invite.email else ""
    local_part = invite.email.split("@")[0]
    mb = Mailbox(
        user_id=user.id,
        domain_id=invite.domain_id,
        local_part=local_part,
        full_address=invite.email,
        maildir_path=f"/var/mail/{domain_part}/{local_part}",
    )
    db.add(mb)
    invite.accepted_at = datetime.now(tz=timezone.utc)
    await _log_activity(db, str(user.id), request, success=True)
    await db.commit()
    return LoginResponse(access_token=_make_access_token(user), role=user.role)


@router.get("/login-activity", response_model=list[LoginActivityItem])
async def login_activity(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LoginActivityItem]:
    rows = (
        await db.execute(
            select(LoginActivity)
            .where(LoginActivity.user_id == current_user["id"])
            .order_by(LoginActivity.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    return [
        LoginActivityItem(
            id=str(r.id),
            ip_address=str(r.ip_address) if r.ip_address else None,
            user_agent=r.user_agent,
            device_type=r.device_type,
            success=r.success,
            failure_reason=r.failure_reason,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/sessions", response_model=list[SessionItem])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionItem]:
    rows = (
        await db.execute(
            select(Session)
            .where(Session.user_id == current_user["id"])
            .order_by(Session.created_at.desc())
        )
    ).scalars().all()
    return [
        SessionItem(
            id=str(r.id),
            ip_address=str(r.ip_address) if r.ip_address else None,
            created_at=r.created_at.isoformat(),
            expires_at=r.expires_at.isoformat() if r.expires_at else None,
        )
        for r in rows
    ]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row: Session | None = (
        await db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == current_user["id"],
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")
    await db.delete(row)
    await db.commit()
    return {"detail": "Session revoked."}
