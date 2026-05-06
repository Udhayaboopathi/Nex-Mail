from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from backend.database import AsyncSessionLocal
from backend.models import BackupJob, Domain, Mailbox, User
from backend.services.backup_service import create_full_backup
from backend.services.domain_service import verify_dns

router = APIRouter(tags=["super_admin"])


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
    email: str


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


@router.get("/domains", response_model=list[DomainItem])
async def list_domains() -> list[DomainItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Domain).order_by(Domain.created_at.desc()))).scalars().all()
    return [_domain_to_item(d) for d in rows]


@router.post("/domains", response_model=DomainItem)
async def create_domain(payload: CreateDomainRequest) -> DomainItem:
    name = payload.name.strip().lower()
    async with AsyncSessionLocal() as db:
        exists = await db.scalar(select(Domain.id).where(Domain.name == name))
        if exists:
            raise HTTPException(status_code=409, detail="Domain already exists")
        domain = Domain(name=name)
        db.add(domain)
        await db.commit()
        await db.refresh(domain)
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


@router.post("/domains/{domain_id}/assign-admin")
async def assign_admin(domain_id: str, payload: AssignAdminRequest) -> dict[str, bool]:
    try:
        domain_uuid = UUID(domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain id") from exc

    async with AsyncSessionLocal() as db:
        domain = (await db.execute(select(Domain).where(Domain.id == domain_uuid))).scalar_one_or_none()
        if domain is None:
            raise HTTPException(status_code=404, detail="Domain not found")

        user = (await db.execute(select(User).where(User.email == payload.email.lower().strip()))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        domain.admin_user_id = user.id
        await db.commit()
    return {"ok": True}


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
