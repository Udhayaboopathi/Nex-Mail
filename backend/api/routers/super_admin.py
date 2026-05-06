from datetime import datetime, timezone
from uuid import UUID

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from backend.api.deps import require_super_admin
from backend.config import settings
from backend.core.encryption import encrypt_value
from backend.core.security import hash_password
from backend.database import AsyncSessionLocal
from backend.models import BackupJob, Domain, Mailbox, User
from backend.services.backup_service import create_full_backup
from backend.services.domain_service import (
    build_dkim_txt_record,
    create_domain as provision_domain_with_dkim,
    dkim_txt_dns_name,
    fetch_cloudflare_zone_id,
    verify_dns,
)
from backend.smtp.outbound import SMTPDeliveryError, outbound_relay_uses_implicit_tls, send_direct
from backend.smtp.submission_send import SubmissionSMTPError, send_via_submission

logger = logging.getLogger(__name__)

router = APIRouter(tags=["super_admin"], dependencies=[Depends(require_super_admin)])


def _submission_tcp_host() -> str:
    """SMTP client TCP target; may differ from logical SMTP_SUBMISSION_HOST (Docker hairpin)."""
    conn = (settings.smtp_submission_connect_host or "").strip()
    if conn:
        return conn
    return (settings.smtp_submission_host or "").strip()


def _submission_validate_certs_for_tcp(tcp_host: str) -> bool:
    if settings.smtp_submission_tls_insecure:
        return False
    h = tcp_host.strip().lower()
    if h in ("127.0.0.1", "localhost", "::1"):
        return False
    return True


def _outbound_relay_smtp_ready() -> bool:
    """Host + AUTH credentials for SMTP_OUTBOUND_RELAY_* (e.g. Brevo)."""
    h = (settings.smtp_outbound_relay_host or "").strip()
    u = (settings.smtp_outbound_relay_user or "").strip()
    p = (settings.smtp_outbound_relay_password or "").strip()
    return bool(h and u and p)


def _local_submission_ready() -> bool:
    return bool((settings.smtp_submission_host or "").strip() and (settings.smtp_submission_user or "").strip())


def _mail_test_from_addr() -> str:
    return (settings.smtp_test_mail_from or "").strip() or settings.super_admin_email or ""


def _mail_test_sends_via() -> str | None:
    """Primary route for the super-admin test: own submission when configured, else relay-only."""
    if _local_submission_ready():
        return "local_submission"
    if _outbound_relay_smtp_ready():
        return "outbound_relay"
    return None


async def _send_via_outbound_relay_smarthost(
    *,
    mail_from: str,
    mail_to: str,
    subject: str,
    body_text: str,
) -> None:
    """Send via SMTP_OUTBOUND_RELAY_* (Brevo, etc.) — used only as fallback when your own server path fails."""
    relay_h = (settings.smtp_outbound_relay_host or "").strip()
    relay_user = (settings.smtp_outbound_relay_user or "").strip()
    relay_pw = (settings.smtp_outbound_relay_password or "").strip()
    if not (relay_h and relay_user and relay_pw):
        raise SubmissionSMTPError("SMTP_OUTBOUND_RELAY_* is not fully configured")
    implicit = outbound_relay_uses_implicit_tls()
    await send_via_submission(
        host=relay_h,
        port=int(settings.smtp_outbound_relay_port),
        username=relay_user,
        password=relay_pw,
        mail_from=mail_from,
        mail_to=mail_to,
        subject=subject,
        body_text=body_text,
        use_starttls=bool(settings.smtp_outbound_relay_use_tls) and not implicit,
        implicit_tls=implicit,
        validate_certs=True,
    )


def _smtp_connect_timeout_hint() -> str:
    return (
        " Outbound SMTP may be blocked (587 is often filtered). Try SMTP_OUTBOUND_RELAY_PORT=2525 with Brevo, "
        "or port 465 with SMTP_OUTBOUND_RELAY_IMPLICIT_TLS=true (465 enables implicit TLS automatically). "
        "Test from the VPS: nc -zv smtp-relay.brevo.com 587 && nc -zv smtp-relay.brevo.com 2525 && nc -zv smtp-relay.brevo.com 465"
    )


class SuperAdminStats(BaseModel):
    total_domains: int
    active_domains: int
    total_mailboxes: int
    total_messages_today: int


class DomainItem(BaseModel):
    id: str
    name: str
    is_active: bool
    is_suspended: bool
    suspended_reason: str | None = None
    storage_quota_gb: int
    used_storage_gb: float
    dns_verified: bool
    dkim_selector: str
    # Copy-paste for DNS: TXT name (under your domain zone) and full value.
    dkim_dns_name: str | None = None
    dkim_txt_record: str | None = None
    cloudflare_auto_dns: bool
    whitelabel_company_name: str | None = None
    whitelabel_primary_color: str
    whitelabel_logo_url: str | None = None
    retention_days: int
    ediscovery_enabled: bool
    admin_user_id: str | None = None
    created_at: str


class CreateDomainRequest(BaseModel):
    name: str = Field(min_length=3, max_length=253)


class UpdateDomainRequest(BaseModel):
    is_active: bool | None = None
    storage_quota_gb: int | None = Field(default=None, ge=1, le=2048)
    retention_days: int | None = Field(default=None, ge=0, le=3650)
    whitelabel_company_name: str | None = None
    whitelabel_primary_color: str | None = None
    whitelabel_logo_url: str | None = None
    ediscovery_enabled: bool | None = None


class SuspendDomainRequest(BaseModel):
    reason: str = ""


class AssignAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    cloudflare_api_token: str = Field(min_length=10, max_length=512)


class AssignAdminResponse(BaseModel):
    ok: bool = True
    welcome_email_sent: bool = False
    welcome_email_error: str | None = None
    # When True, welcome mail runs after HTTP returns (avoids UI hang if port 25 is slow/blocked).
    welcome_email_queued: bool = False


class TestMailRequest(BaseModel):
    to: EmailStr


class TestMailResponse(BaseModel):
    ok: bool = True
    detail: str | None = None


class MailTestStatusResponse(BaseModel):
    submission_configured: bool
    host: str | None = None
    port: int | None = None
    from_hint: str | None = None
    # Actual TCP connect target (SMTP_SUBMISSION_CONNECT_HOST or SMTP_SUBMISSION_HOST).
    submission_tcp_target: str | None = None
    outbound_relay_configured: bool = False
    outbound_relay_ready: bool = False
    outbound_relay_host: str | None = None
    outbound_relay_port: int | None = None
    can_send_test_mail: bool = False
    # outbound_relay preferred when both relay and local submission are configured.
    mail_test_sends_via: str | None = None


def _is_consumer_gmail(email: str) -> bool:
    addr = email.lower().strip()
    return addr.endswith("@gmail.com") or addr.endswith("@googlemail.com")


async def _send_assign_welcome_email(
    email_norm: str,
    domain_name: str,
    login_url: str,
    password: str,
) -> None:
    subject = f"Domain admin access for {domain_name}"
    body_text = (
        f"You have been assigned as domain administrator for {domain_name}.\n\n"
        f"Login URL: {login_url}\n"
        f"Login ID (email): {email_norm}\n"
        f"Password: {password}\n\n"
        "Please sign in and change your password after first login.\n"
    )
    from_addr = f"no-reply@{domain_name}"
    try:
        await send_direct(
            from_addr=from_addr,
            to_list=[email_norm],
            subject=subject,
            body_text=body_text,
        )
        return
    except (SMTPDeliveryError, Exception) as direct_exc:
        sub_host = (settings.smtp_submission_host or "").strip()
        sub_user = (settings.smtp_submission_user or "").strip()
        if not sub_host or not sub_user:
            logger.warning(
                "Assign-admin welcome email failed for %s (direct MX blocked or unreachable; "
                "set SMTP_SUBMISSION_HOST and SMTP_SUBMISSION_USER for port 587 fallback): %s",
                email_norm,
                direct_exc,
            )
            return
        mail_from = (
            (settings.smtp_test_mail_from or "").strip()
            or settings.super_admin_email
            or from_addr
        )
        try:
            tcp = _submission_tcp_host()
            await send_via_submission(
                host=tcp,
                port=int(settings.smtp_submission_port),
                username=sub_user,
                password=(settings.smtp_submission_password or "").strip() or "unused",
                mail_from=mail_from,
                mail_to=email_norm,
                subject=subject,
                body_text=body_text,
                use_starttls=bool(settings.smtp_submission_use_tls),
                validate_certs=_submission_validate_certs_for_tcp(tcp),
            )
            logger.info("Assign-admin welcome email for %s delivered via SMTP submission (%s)", email_norm, sub_host)
        except SubmissionSMTPError as sub_exc:
            if _outbound_relay_smtp_ready():
                try:
                    await _send_via_outbound_relay_smarthost(
                        mail_from=mail_from,
                        mail_to=email_norm,
                        subject=subject,
                        body_text=body_text,
                    )
                    logger.info(
                        "Assign-admin welcome email for %s delivered via SMTP_OUTBOUND_RELAY fallback (after MX + local submission failed)",
                        email_norm,
                    )
                    return
                except SubmissionSMTPError as relay_exc:
                    logger.warning(
                        "Assign-admin welcome email failed for %s (direct MX: %s; submission: %s; relay: %s)",
                        email_norm,
                        direct_exc,
                        sub_exc,
                        relay_exc,
                    )
                    return
            logger.warning(
                "Assign-admin welcome email failed for %s (direct MX: %s; submission: %s)",
                email_norm,
                direct_exc,
                sub_exc,
            )


class BackupJobItem(BaseModel):
    id: str
    type: str
    status: str
    file_size_mb: float | None = None
    total_messages: int | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


def _domain_to_item(d: Domain) -> DomainItem:
    dkim_txt = build_dkim_txt_record(d)
    return DomainItem(
        id=str(d.id),
        name=d.name,
        is_active=bool(d.is_active),
        is_suspended=bool(d.is_suspended),
        suspended_reason=d.suspended_reason,
        storage_quota_gb=int(d.storage_quota_gb or 0),
        used_storage_gb=float(d.used_storage_gb or 0),
        dns_verified=bool(d.dns_verified),
        dkim_selector=d.dkim_selector or "mail",
        dkim_dns_name=dkim_txt_dns_name(d) if dkim_txt else None,
        dkim_txt_record=dkim_txt,
        cloudflare_auto_dns=bool(d.cloudflare_auto_dns),
        whitelabel_company_name=d.whitelabel_company_name,
        whitelabel_primary_color=d.whitelabel_primary_color or "#6366f1",
        whitelabel_logo_url=d.whitelabel_logo_url,
        retention_days=int(d.retention_days or 0),
        ediscovery_enabled=bool(d.ediscovery_enabled),
        admin_user_id=str(d.admin_user_id) if d.admin_user_id else None,
        created_at=d.created_at.isoformat() if d.created_at else datetime.now(tz=timezone.utc).isoformat(),
    )


@router.get("/stats", response_model=SuperAdminStats)
async def get_stats() -> SuperAdminStats:
    async with AsyncSessionLocal() as db:
        total_domains = int(await db.scalar(select(func.count(Domain.id))) or 0)
        active_domains = int(await db.scalar(select(func.count(Domain.id)).where(Domain.is_active == True, Domain.is_suspended == False)) or 0)
        total_mailboxes = int(await db.scalar(select(func.count(Mailbox.id))) or 0)
        _users = int(await db.scalar(select(func.count(User.id))) or 0)
    return SuperAdminStats(
        total_domains=total_domains,
        active_domains=active_domains,
        total_mailboxes=total_mailboxes,
        total_messages_today=0,
    )


@router.get("/mail/test-status", response_model=MailTestStatusResponse)
async def mail_test_status() -> MailTestStatusResponse:
    host = (settings.smtp_submission_host or "").strip()
    user = (settings.smtp_submission_user or "").strip()
    # Password optional for self-hosted Nex Mail (port 587 stub-auth). Required for real external SMTP.
    configured = bool(host and user)
    from_hint = (settings.smtp_test_mail_from or "").strip() or settings.super_admin_email
    relay_host = (settings.smtp_outbound_relay_host or "").strip()
    relay_ready = _outbound_relay_smtp_ready()
    tcp_target = _submission_tcp_host() if configured else ""
    route = _mail_test_sends_via()
    from_ok = bool(_mail_test_from_addr())
    return MailTestStatusResponse(
        submission_configured=configured,
        host=host or None,
        port=settings.smtp_submission_port,
        from_hint=from_hint or None,
        submission_tcp_target=tcp_target or None,
        outbound_relay_configured=bool(relay_host),
        outbound_relay_ready=relay_ready,
        outbound_relay_host=relay_host or None,
        outbound_relay_port=int(settings.smtp_outbound_relay_port) if relay_host else None,
        can_send_test_mail=bool(route) and from_ok,
        mail_test_sends_via=route,
    )


@router.post("/mail/test", response_model=TestMailResponse)
async def send_test_mail(payload: TestMailRequest) -> TestMailResponse:
    mail_from = _mail_test_from_addr()
    if not mail_from:
        raise HTTPException(
            status_code=400,
            detail="Set SMTP_TEST_MAIL_FROM or SUPER_ADMIN_EMAIL as the From address.",
        )
    to_addr = str(payload.to).lower().strip()
    subject = "Nex Mail — super-admin SMTP test"
    body = (
        "This is a test message sent from the Nex Mail super-admin panel.\n\n"
        "If you received it, authenticated SMTP submission (typically port 587) is working.\n"
    )

    relay_h = (settings.smtp_outbound_relay_host or "").strip()
    relay_user = (settings.smtp_outbound_relay_user or "").strip()
    relay_pw = (settings.smtp_outbound_relay_password or "").strip()
    relay_ready = bool(relay_h and relay_user and relay_pw)

    host = (settings.smtp_submission_host or "").strip()
    user = (settings.smtp_submission_user or "").strip()
    password = (settings.smtp_submission_password or "").strip() or "unused"
    local_ready = bool(host and user)

    if not relay_ready and not local_ready:
        raise HTTPException(
            status_code=400,
            detail=(
                "Configure SMTP_SUBMISSION_HOST + SMTP_SUBMISSION_USER for your own server, and/or full "
                "SMTP_OUTBOUND_RELAY_* as fallback. See .env.example."
            ),
        )

    if local_ready:
        tcp = _submission_tcp_host()
        try:
            await send_via_submission(
                host=tcp,
                port=int(settings.smtp_submission_port),
                username=user,
                password=password,
                mail_from=mail_from,
                mail_to=to_addr,
                subject=subject,
                body_text=body,
                use_starttls=bool(settings.smtp_submission_use_tls),
                validate_certs=_submission_validate_certs_for_tcp(tcp),
            )
        except SubmissionSMTPError as local_exc:
            msg_local = str(local_exc)
            logger.warning(
                "Super-admin mail test: local submission failed tcp=%s:%s mail_from=%s to=%s: %s",
                tcp,
                settings.smtp_submission_port,
                mail_from,
                to_addr,
                msg_local,
            )
            if relay_ready:
                try:
                    await _send_via_outbound_relay_smarthost(
                        mail_from=mail_from,
                        mail_to=to_addr,
                        subject=subject,
                        body_text=body,
                    )
                except SubmissionSMTPError as relay_exc:
                    msg_r = str(relay_exc)
                    logger.error(
                        "Super-admin mail test: relay fallback also failed mail_from=%s to=%s: %s",
                        mail_from,
                        to_addr,
                        msg_r,
                    )
                    combined = f"Your server submission failed: {msg_local}. SMTP_OUTBOUND_RELAY_* fallback failed: {msg_r}."
                    if "Timed out connecting" in msg_r or "SMTPConnectTimeoutError" in msg_r:
                        combined += _smtp_connect_timeout_hint()
                    raise HTTPException(status_code=502, detail=combined) from relay_exc
                return TestMailResponse(
                    ok=True,
                    detail=(
                        "Your Nex Mail submission failed, so this test used SMTP_OUTBOUND_RELAY_* fallback. "
                        "Fix local :587 if you want all mail to go through your server first."
                    ),
                )
            if "timed out" in msg_local.lower():
                msg_local += (
                    " Common fix in Docker: SMTP_SUBMISSION_CONNECT_HOST=127.0.0.1. "
                    "Optional: set SMTP_OUTBOUND_RELAY_* for a fallback smarthost."
                )
            raise HTTPException(status_code=502, detail=msg_local) from local_exc
        detail = (
            "Message accepted on your Nex Mail server (:587). External delivery tries direct MX from your IP first; "
        )
        detail += (
            "SMTP_OUTBOUND_RELAY_* is used only if that fails (blocked port 25, blacklists, etc.)."
            if relay_ready
            else "Configure SMTP_OUTBOUND_RELAY_* for a smarthost fallback after direct MX fails."
        )
        return TestMailResponse(ok=True, detail=detail)

    try:
        await _send_via_outbound_relay_smarthost(
            mail_from=mail_from,
            mail_to=to_addr,
            subject=subject,
            body_text=body,
        )
    except SubmissionSMTPError as exc:
        msg = str(exc)
        logger.error(
            "Super-admin mail test failed (relay-only %s:%s mail_from=%s to=%s): %s",
            relay_h,
            settings.smtp_outbound_relay_port,
            mail_from,
            to_addr,
            msg,
        )
        if "Timed out connecting" in msg or "SMTPConnectTimeoutError" in msg:
            msg += _smtp_connect_timeout_hint()
        raise HTTPException(status_code=502, detail=msg) from exc
    return TestMailResponse(
        ok=True,
        detail="Message sent via SMTP_OUTBOUND_RELAY_* only (local submission not configured). Prefer SMTP_SUBMISSION_* to use your own server first.",
    )


@router.get("/domains", response_model=list[DomainItem])
async def list_domains() -> list[DomainItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Domain).order_by(Domain.created_at.desc()))).scalars().all()
    return [_domain_to_item(d) for d in rows]


@router.post("/domains", response_model=DomainItem)
async def create_domain(payload: CreateDomainRequest) -> DomainItem:
    name = payload.name.strip().lower()
    try:
        await provision_domain_with_dkim(name)
    except ValueError as exc:
        if "already exists" in str(exc).lower():
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.name == name))).scalar_one()
    return _domain_to_item(domain)


@router.patch("/domains/{domain_id}", response_model=DomainItem)
async def update_domain(domain_id: str, payload: UpdateDomainRequest) -> DomainItem:
    try:
        domain_uuid = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == domain_uuid))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="Domain not found")

        data = payload.model_dump(exclude_none=True)
        for k, v in data.items():
            setattr(domain, k, v)

        await db.commit()
        await db.refresh(domain)
    return _domain_to_item(domain)


@router.delete("/domains/{domain_id}")
async def delete_domain(domain_id: str) -> dict[str, bool]:
    try:
        domain_uuid = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == domain_uuid))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="Domain not found")
        await db.delete(domain)
        await db.commit()
    return {"ok": True}


@router.post("/domains/{domain_id}/assign-admin", response_model=AssignAdminResponse)
async def assign_admin(
    domain_id: str,
    payload: AssignAdminRequest,
    background_tasks: BackgroundTasks,
) -> AssignAdminResponse:
    try:
        domain_uuid = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc

    email_norm = str(payload.email).lower().strip()
    welcome_sent = False
    welcome_err: str | None = None
    welcome_queued = False

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == domain_uuid))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="Domain not found")

        user = (await db.execute(select(User).where(User.email == email_norm))).scalar_one_or_none()
        if user is None:
            user = User(
                email=email_norm,
                hashed_password=hash_password(payload.password),
                role="domain_admin",
                is_active=True,
            )
            db.add(user)
            await db.flush()
        else:
            user.hashed_password = hash_password(payload.password)
            if user.role != "super_admin":
                user.role = "domain_admin"

        domain.admin_user_id = user.id
        domain.cloudflare_token_encrypted = encrypt_value(payload.cloudflare_api_token.strip())
        zone_id = await fetch_cloudflare_zone_id(payload.cloudflare_api_token.strip(), domain.name)
        if zone_id:
            domain.cloudflare_zone_id = zone_id
            domain.cloudflare_auto_dns = True

        await db.commit()

        domain_name = domain.name

    # Send plaintext credentials only to Gmail / GoogleMail (explicit product choice).
    # Run in background so Cloudflare + DB commit return quickly; direct MX can block on port 25.
    if _is_consumer_gmail(email_norm):
        login_url = str(settings.frontend_url).rstrip("/") + "/login"
        background_tasks.add_task(
            _send_assign_welcome_email,
            email_norm,
            domain_name,
            login_url,
            payload.password,
        )
        welcome_queued = True

    return AssignAdminResponse(
        ok=True,
        welcome_email_sent=welcome_sent,
        welcome_email_error=welcome_err,
        welcome_email_queued=welcome_queued,
    )


@router.post("/domains/{domain_id}/suspend")
async def suspend_domain(domain_id: str, payload: SuspendDomainRequest) -> dict[str, bool]:
    try:
        domain_uuid = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == domain_uuid))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="Domain not found")
        domain.is_suspended = True
        domain.suspended_reason = payload.reason
        await db.commit()
    return {"ok": True}


@router.post("/domains/{domain_id}/unsuspend")
async def unsuspend_domain(domain_id: str) -> dict[str, bool]:
    try:
        domain_uuid = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == domain_uuid))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="Domain not found")
        domain.is_suspended = False
        domain.suspended_reason = None
        await db.commit()
    return {"ok": True}


@router.post("/domains/{domain_id}/dns/verify")
async def verify_domain_dns(domain_id: str) -> dict:
    try:
        _ = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc
    try:
        result = await verify_dns(domain_id)
        records = result.get("records", {})
        return {
            "mx": {"type": "MX", "name": result.get("domain", ""), "value": records.get("mx", {}).get("value", ""), "valid": bool(records.get("mx", {}).get("ok")), "current": records.get("mx", {}).get("value")},
            "a": {"type": "A", "name": result.get("domain", ""), "value": result.get("domain", ""), "valid": True},
            "spf": {"type": "TXT", "name": result.get("domain", ""), "value": records.get("spf", {}).get("value", ""), "valid": bool(records.get("spf", {}).get("ok")), "current": records.get("spf", {}).get("value")},
            "dkim": {"type": "TXT", "name": f"mail._domainkey.{result.get('domain', '')}", "value": records.get("dkim", {}).get("value", ""), "valid": bool(records.get("dkim", {}).get("ok")), "current": records.get("dkim", {}).get("value")},
            "dmarc": {"type": "TXT", "name": f"_dmarc.{result.get('domain', '')}", "value": records.get("dmarc", {}).get("value", ""), "valid": bool(records.get("dmarc", {}).get("ok")), "current": records.get("dmarc", {}).get("value")},
            "all_valid": bool(result.get("all_ok")),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/domains/{domain_id}/dns/guide")
async def get_dns_guide(domain_id: str) -> dict:
    try:
        domain_uuid = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == domain_uuid))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="Domain not found")

    return {
        "domain": domain.name,
        "records": {
            "mx": {"type": "MX", "name": domain.name, "value": f"10 mail.{domain.name}"},
            "a": {"type": "A", "name": f"mail.{domain.name}", "value": "YOUR_SERVER_IP"},
            "spf": {"type": "TXT", "name": domain.name, "value": domain.spf_record or f"v=spf1 mx a:{domain.name} ~all"},
            "dkim": {"type": "TXT", "name": f"{domain.dkim_selector}._domainkey.{domain.name}", "value": "v=DKIM1; k=rsa; p=<public-key>"},
            "dmarc": {"type": "TXT", "name": f"_dmarc.{domain.name}", "value": domain.dmarc_record or f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain.name}"},
        },
    }


@router.get("/backups", response_model=list[BackupJobItem])
async def get_backups() -> list[BackupJobItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(BackupJob).order_by(BackupJob.created_at.desc()))).scalars().all()
    return [
        BackupJobItem(
            id=str(j.id),
            type=j.type or "full",
            status=j.status or "pending",
            file_size_mb=float(j.file_size_mb) if j.file_size_mb is not None else None,
            total_messages=j.total_messages,
            error_message=j.error_message,
            created_at=j.created_at.isoformat() if j.created_at else datetime.now(tz=timezone.utc).isoformat(),
            completed_at=j.completed_at.isoformat() if j.completed_at else None,
        )
        for j in rows
    ]


@router.post("/backup/full")
async def trigger_full_backup() -> dict[str, str]:
    job_id = await create_full_backup()
    return {"job_id": job_id}


class AuditLogItem(BaseModel):
    id: str
    user_id: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    ip_address: str | None = None
    details: dict | None = None
    created_at: str


@router.get("/audit-logs")
async def get_audit_logs(page: int = 1, per_page: int = 50) -> dict:
    """Return paginated audit log entries."""
    from backend.models.all_models import AuditLog
    offset = max(0, (page - 1) * per_page)
    try:
        async with AsyncSessionLocal() as db:
            total = int(await db.scalar(select(func.count(AuditLog.id))) or 0)
            rows = (
                await db.execute(
                    select(AuditLog).order_by(AuditLog.created_at.desc()).limit(per_page).offset(offset)
                )
            ).scalars().all()
        items = [
            {
                "id": str(r.id),
                "user_id": str(r.user_id) if r.user_id else None,
                "action": r.action or "",
                "target": r.target,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]
        return {"items": items, "total": total, "page": page, "per_page": per_page}
    except Exception:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}
