from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from backend.api.deps import require_any_auth, require_domain_admin
from backend.database import AsyncSessionLocal
from backend.models import Alias, AuditLog, Domain, Mailbox, User

router = APIRouter(tags=["domain_admin"])


# ── Pydantic models ─────────────────────────────────────────────────────────

class DomainAdminStats(BaseModel):
    domains: int
    mailboxes: int
    aliases: int
    suspended_domains: int
    used_storage_gb: float
    storage_quota_gb: int


class OnboardingStep(BaseModel):
    key: str
    label: str
    done: bool


class OnboardingResponse(BaseModel):
    steps: list[OnboardingStep]
    complete: bool


class MailboxItem(BaseModel):
    id: str
    user_id: str
    domain_id: str
    local_part: str
    display_name: str | None = None
    full_address: str
    quota_mb: int
    used_mb: float
    is_active: bool
    last_login_at: str | None = None
    created_at: str | None = None


class MailboxListResponse(BaseModel):
    items: list[MailboxItem]
    total: int


class CreateMailboxRequest(BaseModel):
    local_part: str = Field(min_length=1, max_length=64, description="Email alias before @ (e.g. udhaya)")
    password: str = Field(min_length=8, max_length=256)
    quota_mb: int = Field(default=1024, ge=64, le=102400)
    display_name: str | None = Field(default=None, max_length=200, description="Full display name for the user")


class AdminDomainContext(BaseModel):
    id: str
    name: str
    storage_quota_gb: int
    used_storage_gb: float


class UpdateMailboxRequest(BaseModel):
    quota_mb: int | None = Field(default=None, ge=64, le=102400)
    is_active: bool | None = None
    display_name: str | None = Field(default=None, max_length=200)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


class AliasItem(BaseModel):
    id: str
    domain_id: str
    source_address: str
    destination_address: str
    is_catch_all: bool
    is_active: bool
    created_at: str | None = None


class AliasListResponse(BaseModel):
    items: list[AliasItem]


class CreateAliasRequest(BaseModel):
    domain_id: str
    source_address: EmailStr
    destination_address: EmailStr
    is_catch_all: bool = False


class UpdateAliasRequest(BaseModel):
    destination_address: str | None = None
    is_active: bool | None = None


class WhitelabelData(BaseModel):
    logo_url: str | None = None
    primary_color: str = "#6366f1"
    company_name: str | None = None


class RetentionData(BaseModel):
    retention_days: int = Field(default=0, ge=0, le=3650)


class DnsStatusRecord(BaseModel):
    type: str
    name: str
    expected: str
    current: str | None = None
    valid: bool


class DnsStatusResponse(BaseModel):
    records: list[DnsStatusRecord]
    all_valid: bool
    ptr_note: str


class AuditLogItem(BaseModel):
    id: str
    user_id: str | None = None
    action: str
    target: str | None = None
    ip_address: str | None = None
    created_at: str


# ── Helpers ─────────────────────────────────────────────────────────────────

def _mb_item(m: Mailbox) -> MailboxItem:
    return MailboxItem(
        id=str(m.id),
        user_id=str(m.user_id),
        domain_id=str(m.domain_id),
        local_part=m.local_part or "",
        display_name=m.display_name,
        full_address=m.full_address or "",
        quota_mb=int(m.quota_mb or 0),
        used_mb=float(m.used_mb or 0),
        is_active=bool(m.is_active),
        last_login_at=m.last_login_at.isoformat() if m.last_login_at else None,
        created_at=m.created_at.isoformat() if m.created_at else None,
    )


async def _scoped_domain(user: dict) -> Domain | None:
    """Domain for this admin (assigned domain, or first domain for super_admin)."""
    async with AsyncSessionLocal() as db:
        uid = UUID(user["id"])
        if user.get("role") == "super_admin":
            return (
                await db.execute(select(Domain).order_by(Domain.created_at.asc()).limit(1))
            ).scalar_one_or_none()
        return (
            await db.execute(
                select(Domain)
                .where(Domain.admin_user_id == uid)
                .order_by(Domain.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()


def _alias_item(a: Alias) -> AliasItem:
    return AliasItem(
        id=str(a.id),
        domain_id=str(a.domain_id),
        source_address=a.source_address or "",
        destination_address=a.destination_address or "",
        is_catch_all=bool(a.is_catch_all),
        is_active=bool(a.is_active),
        created_at=a.created_at.isoformat() if a.created_at else None,
    )


# ── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=DomainAdminStats)
async def get_stats(user: dict = Depends(require_any_auth)) -> DomainAdminStats:
    async with AsyncSessionLocal() as db:
        domains = int(await db.scalar(select(func.count(Domain.id))) or 0)
        mailboxes = int(await db.scalar(select(func.count(Mailbox.id))) or 0)
        aliases = int(await db.scalar(select(func.count(Alias.id))) or 0)
        suspended = int(await db.scalar(select(func.count(Domain.id)).where(Domain.is_suspended == True)) or 0)
        used = float(await db.scalar(select(func.coalesce(func.sum(Domain.used_storage_gb), 0))) or 0)
        quota = int(await db.scalar(select(func.coalesce(func.sum(Domain.storage_quota_gb), 10))) or 10)
    return DomainAdminStats(
        domains=domains, mailboxes=mailboxes, aliases=aliases,
        suspended_domains=suspended, used_storage_gb=used, storage_quota_gb=quota,
    )


# ── Onboarding ───────────────────────────────────────────────────────────────

@router.get("/onboarding", response_model=OnboardingResponse)
async def get_onboarding(user: dict = Depends(require_any_auth)) -> OnboardingResponse:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
        mailbox_count = int(await db.scalar(select(func.count(Mailbox.id))) or 0)
        alias_count = int(await db.scalar(select(func.count(Alias.id))) or 0)

    dns_verified = bool(domain and domain.dns_verified)
    dkim_set = bool(domain and domain.dkim_private_key_encrypted)
    has_mailbox = mailbox_count > 0

    steps = [
        OnboardingStep(key="domain_added", label="Domain added", done=domain is not None),
        OnboardingStep(key="dns_verified", label="DNS records verified", done=dns_verified),
        OnboardingStep(key="dkim_configured", label="DKIM key configured", done=dkim_set),
        OnboardingStep(key="mailbox_created", label="First mailbox created", done=has_mailbox),
    ]
    return OnboardingResponse(steps=steps, complete=all(s.done for s in steps))


# ── Mailboxes ────────────────────────────────────────────────────────────────

@router.get("/domain", response_model=AdminDomainContext)
async def get_admin_domain(user: dict = Depends(require_domain_admin)) -> AdminDomainContext:
    d = await _scoped_domain(user)
    if d is None:
        raise HTTPException(status_code=404, detail="No domain found for this account.")
    return AdminDomainContext(
        id=str(d.id),
        name=d.name,
        storage_quota_gb=int(d.storage_quota_gb or 10),
        used_storage_gb=float(d.used_storage_gb or 0),
    )


@router.get("/mailboxes", response_model=MailboxListResponse)
async def list_mailboxes(
    search: str = "",
    status: str = "",
    page: int = 1,
    limit: int = 50,
    user: dict = Depends(require_domain_admin),
) -> MailboxListResponse:
    dom = await _scoped_domain(user)
    if user.get("role") != "super_admin" and dom is None:
        return MailboxListResponse(items=[], total=0)
    async with AsyncSessionLocal() as db:
        stmt = select(Mailbox).order_by(Mailbox.created_at.desc())
        if user.get("role") != "super_admin" and dom is not None:
            stmt = stmt.where(Mailbox.domain_id == dom.id)
        if search:
            stmt = stmt.where(Mailbox.full_address.ilike(f"%{search}%"))
        if status == "active":
            stmt = stmt.where(Mailbox.is_active == True)
        elif status == "inactive":
            stmt = stmt.where(Mailbox.is_active == False)
        total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        rows = (await db.execute(stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
    return MailboxListResponse(items=[_mb_item(m) for m in rows], total=total)


@router.post("/mailboxes", response_model=MailboxItem)
async def create_mailbox(payload: CreateMailboxRequest, user: dict = Depends(require_domain_admin)) -> MailboxItem:
    d = await _scoped_domain(user)
    if d is None:
        raise HTTPException(
            status_code=400,
            detail="No domain is assigned to this account. A super-admin must add a domain and assign you as domain admin.",
        )
    from backend.services.mailbox_service import create_mailbox as mailbox_create

    try:
        await mailbox_create(
            domain_id=str(d.id),
            local_part=payload.local_part,
            password=payload.password,
            quota_mb=payload.quota_mb,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        msg = str(exc)
        if "already exists" in msg.lower():
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc

    local = payload.local_part.strip().lower()
    full = f"{local}@{d.name.lower()}"
    async with AsyncSessionLocal() as db:
        mb = (await db.execute(select(Mailbox).where(Mailbox.full_address == full))).scalar_one()
    return _mb_item(mb)


@router.get("/mailboxes/{mailbox_id}", response_model=MailboxItem)
async def get_mailbox(mailbox_id: str, user: dict = Depends(require_domain_admin)) -> MailboxItem:
    try:
        mid = UUID(mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        mb = (await db.execute(select(Mailbox).where(Mailbox.id == mid))).scalar_one_or_none()
    if mb is None:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return _mb_item(mb)


@router.patch("/mailboxes/{mailbox_id}", response_model=MailboxItem)
async def update_mailbox(mailbox_id: str, payload: UpdateMailboxRequest, user: dict = Depends(require_domain_admin)) -> MailboxItem:
    try:
        mid = UUID(mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        mb = (await db.execute(select(Mailbox).where(Mailbox.id == mid))).scalar_one_or_none()
        if mb is None:
            raise HTTPException(status_code=404, detail="Mailbox not found")
        if payload.quota_mb is not None:
            dom = (await db.execute(select(Domain).where(Domain.id == mb.domain_id))).scalar_one_or_none()
            if dom:
                pool_mb = max(int(dom.storage_quota_gb or 10), 1) * 1024
                others = int(
                    await db.scalar(
                        select(func.coalesce(func.sum(Mailbox.quota_mb), 0)).where(
                            Mailbox.domain_id == mb.domain_id,
                            Mailbox.id != mb.id,
                        )
                    )
                    or 0
                )
                if others + int(payload.quota_mb) > pool_mb:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Mailbox quota would exceed domain storage pool ({pool_mb} MB).",
                    )
            mb.quota_mb = payload.quota_mb
        if payload.is_active is not None:
            mb.is_active = payload.is_active
        if payload.display_name is not None:
            mb.display_name = payload.display_name.strip() or None
        await db.commit()
        await db.refresh(mb)
    return _mb_item(mb)


@router.post("/mailboxes/{mailbox_id}/reset-password")
async def reset_mailbox_password(mailbox_id: str, payload: ResetPasswordRequest, user: dict = Depends(require_domain_admin)) -> dict[str, bool]:
    try:
        mid = UUID(mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    from backend.core.security import hash_password
    async with AsyncSessionLocal() as db:
        mb = (await db.execute(select(Mailbox).where(Mailbox.id == mid))).scalar_one_or_none()
        if mb is None:
            raise HTTPException(status_code=404, detail="Mailbox not found")
        user_row = (await db.execute(select(User).where(User.id == mb.user_id))).scalar_one_or_none()
        if user_row:
            user_row.hashed_password = hash_password(payload.new_password)
            await db.commit()
    return {"ok": True}


@router.delete("/mailboxes/{mailbox_id}")
async def delete_mailbox(mailbox_id: str, user: dict = Depends(require_domain_admin)) -> dict[str, bool]:
    try:
        mid = UUID(mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        mb = (await db.execute(select(Mailbox).where(Mailbox.id == mid))).scalar_one_or_none()
        if mb is None:
            raise HTTPException(status_code=404, detail="Mailbox not found")
        uid = mb.user_id
        await db.delete(mb)
        await db.flush()
        orphan = (await db.execute(select(User).where(User.id == uid))).scalar_one_or_none()
        if orphan:
            await db.delete(orphan)
        await db.commit()
    return {"ok": True}


@router.get("/mailboxes/{mailbox_id}/activity")
async def get_mailbox_activity(mailbox_id: str, user: dict = Depends(require_any_auth)) -> dict:
    return {"items": [], "total": 0}


# ── Aliases ───────────────────────────────────────────────────────────────────

@router.get("/aliases", response_model=AliasListResponse)
async def list_aliases(user: dict = Depends(require_any_auth)) -> AliasListResponse:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Alias).order_by(Alias.created_at.desc()))).scalars().all()
    return AliasListResponse(items=[_alias_item(a) for a in rows])


@router.post("/aliases", response_model=AliasItem)
async def create_alias(payload: CreateAliasRequest, user: dict = Depends(require_any_auth)) -> AliasItem:
    try:
        domain_id = UUID(payload.domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain_id") from exc
    async with AsyncSessionLocal() as db:
        domain_row = (await db.execute(select(Domain).where(Domain.id == domain_id))).scalar_one_or_none()
        if domain_row is None:
            raise HTTPException(status_code=404, detail="Domain not found")
        alias = Alias(domain_id=domain_id, source_address=str(payload.source_address), destination_address=str(payload.destination_address), is_catch_all=payload.is_catch_all, is_active=True)
        db.add(alias)
        await db.commit()
        await db.refresh(alias)
    return _alias_item(alias)


@router.patch("/aliases/{alias_id}", response_model=AliasItem)
async def update_alias(alias_id: str, payload: UpdateAliasRequest, user: dict = Depends(require_any_auth)) -> AliasItem:
    try:
        aid = UUID(alias_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid alias_id") from exc
    async with AsyncSessionLocal() as db:
        alias = (await db.execute(select(Alias).where(Alias.id == aid))).scalar_one_or_none()
        if alias is None:
            raise HTTPException(status_code=404, detail="Alias not found")
        if payload.destination_address is not None:
            alias.destination_address = payload.destination_address
        if payload.is_active is not None:
            alias.is_active = payload.is_active
        await db.commit()
        await db.refresh(alias)
    return _alias_item(alias)


@router.delete("/aliases/{alias_id}")
async def delete_alias(alias_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        aid = UUID(alias_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid alias_id") from exc
    async with AsyncSessionLocal() as db:
        alias = (await db.execute(select(Alias).where(Alias.id == aid))).scalar_one_or_none()
        if alias is None:
            raise HTTPException(status_code=404, detail="Alias not found")
        await db.delete(alias)
        await db.commit()
    return {"ok": True}


# ── DNS ───────────────────────────────────────────────────────────────────────

@router.get("/dns/status", response_model=DnsStatusResponse)
async def get_dns_status(user: dict = Depends(require_any_auth)) -> DnsStatusResponse:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
    if domain is None:
        return DnsStatusResponse(records=[], all_valid=False, ptr_note="No domain configured")

    dn = domain.name
    records = [
        DnsStatusRecord(type="MX", name=dn, expected=f"10 mail.{dn}", valid=False),
        DnsStatusRecord(type="A", name=f"mail.{dn}", expected="YOUR_IP", valid=False),
        DnsStatusRecord(type="TXT", name=dn, expected=f"v=spf1 mx a:{dn} ~all", valid=domain.dns_verified),
        DnsStatusRecord(type="TXT", name=f"mail._domainkey.{dn}", expected="v=DKIM1; k=rsa; p=...", valid=bool(domain.dkim_private_key_encrypted)),
        DnsStatusRecord(type="TXT", name=f"_dmarc.{dn}", expected=f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{dn}", valid=domain.dns_verified),
    ]
    return DnsStatusResponse(records=records, all_valid=domain.dns_verified, ptr_note=f"Set PTR record for YOUR_IP → mail.{dn} in Contabo panel")


@router.get("/dns/guide")
async def get_dns_guide(user: dict = Depends(require_any_auth)) -> dict:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
    if domain is None:
        raise HTTPException(status_code=404, detail="No domain found")
    dn = domain.name
    return {
        "domain": dn,
        "records": {
            "mx": {"type": "MX", "name": dn, "value": f"10 mail.{dn}"},
            "a": {"type": "A", "name": f"mail.{dn}", "value": "YOUR_SERVER_IP"},
            "spf": {"type": "TXT", "name": dn, "value": domain.spf_record or f"v=spf1 mx a:{dn} ~all"},
            "dkim": {"type": "TXT", "name": f"{domain.dkim_selector}._domainkey.{dn}", "value": "v=DKIM1; k=rsa; p=<public-key>"},
            "dmarc": {"type": "TXT", "name": f"_dmarc.{dn}", "value": domain.dmarc_record or f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{dn}"},
        },
    }


@router.post("/dns/verify")
async def verify_dns(user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="No domain found")
        domain.dns_verified = True
        domain.dns_verified_at = datetime.now(tz=timezone.utc)
        await db.commit()
    return {"ok": True, "dns_verified": True}


@router.post("/dns/auto")
async def configure_dns_auto(user: dict = Depends(require_any_auth)) -> dict[str, str]:
    return {"status": "queued", "message": "Auto DNS configuration queued"}


# ── Backup ────────────────────────────────────────────────────────────────────

@router.post("/backup")
async def trigger_backup(user: dict = Depends(require_any_auth)) -> dict[str, str]:
    from backend.services.backup_service import create_full_backup
    job_id = await create_full_backup()
    return {"job_id": job_id, "status": "started"}


@router.get("/backup/jobs")
async def list_backup_jobs(user: dict = Depends(require_any_auth)) -> dict:
    from backend.models import BackupJob
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(BackupJob).order_by(BackupJob.created_at.desc()).limit(20))).scalars().all()
    items = [
        {
            "id": str(j.id),
            "type": j.type or "full",
            "status": j.status or "pending",
            "file_size_mb": float(j.file_size_mb) if j.file_size_mb is not None else None,
            "total_messages": j.total_messages,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat() if j.created_at else "",
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in rows
    ]
    return {"items": items}


@router.get("/backup/jobs/{job_id}/download")
async def download_backup(job_id: str, user: dict = Depends(require_any_auth)) -> dict:
    raise HTTPException(status_code=404, detail="Backup file not available")


@router.post("/backup/restore")
async def restore_backup(user: dict = Depends(require_any_auth)) -> dict[str, str]:
    return {"status": "restore_initiated"}


# ── Whitelabel ────────────────────────────────────────────────────────────────

@router.get("/whitelabel", response_model=WhitelabelData)
async def get_whitelabel(user: dict = Depends(require_any_auth)) -> WhitelabelData:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
    if domain is None:
        return WhitelabelData()
    return WhitelabelData(logo_url=domain.whitelabel_logo_url, primary_color=domain.whitelabel_primary_color or "#6366f1", company_name=domain.whitelabel_company_name)


@router.patch("/whitelabel", response_model=WhitelabelData)
async def update_whitelabel(payload: WhitelabelData, user: dict = Depends(require_any_auth)) -> WhitelabelData:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="No domain found")
        if payload.logo_url is not None:
            domain.whitelabel_logo_url = payload.logo_url
        if payload.primary_color:
            domain.whitelabel_primary_color = payload.primary_color
        if payload.company_name is not None:
            domain.whitelabel_company_name = payload.company_name
        await db.commit()
        await db.refresh(domain)
    return WhitelabelData(logo_url=domain.whitelabel_logo_url, primary_color=domain.whitelabel_primary_color or "#6366f1", company_name=domain.whitelabel_company_name)


# ── Retention ─────────────────────────────────────────────────────────────────

@router.get("/retention", response_model=RetentionData)
async def get_retention(user: dict = Depends(require_any_auth)) -> RetentionData:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
    return RetentionData(retention_days=int(domain.retention_days or 0) if domain else 0)


@router.patch("/retention", response_model=RetentionData)
async def update_retention(payload: RetentionData, user: dict = Depends(require_any_auth)) -> RetentionData:
    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).limit(1))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="No domain found")
        domain.retention_days = payload.retention_days
        await db.commit()
    return RetentionData(retention_days=payload.retention_days)


# ── eDiscovery ────────────────────────────────────────────────────────────────

@router.post("/ediscovery/search")
async def ediscovery_search(body: dict, user: dict = Depends(require_any_auth)) -> dict:
    return {"results": [], "total": 0}


@router.post("/ediscovery/export")
async def ediscovery_export(body: dict, user: dict = Depends(require_any_auth)) -> dict[str, str]:
    return {"export_id": "", "status": "pending"}


@router.get("/ediscovery/exports")
async def list_ediscovery_exports(user: dict = Depends(require_any_auth)) -> dict:
    return {"items": []}


@router.get("/ediscovery/exports/{export_id}/download")
async def download_ediscovery_export(export_id: str, user: dict = Depends(require_any_auth)) -> dict:
    raise HTTPException(status_code=404, detail="Export not found")


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=list[AuditLogItem])
async def get_audit_logs(user: dict = Depends(require_any_auth)) -> list[AuditLogItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100))).scalars().all()
    return [
        AuditLogItem(
            id=str(r.id),
            user_id=str(r.user_id) if r.user_id else None,
            action=r.action or "",
            target=r.target,
            ip_address=str(r.ip_address) if r.ip_address else None,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
