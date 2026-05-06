from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from backend.database import AsyncSessionLocal
from backend.models import Alias, Domain, Mailbox, User

router = APIRouter(tags=["domain_admin"])


class DomainAdminStats(BaseModel):
    domains: int
    mailboxes: int
    aliases: int
    suspended_domains: int


class MailboxItem(BaseModel):
    id: str
    user_id: str
    domain_id: str
    local_part: str
    full_address: str
    quota_mb: int
    used_mb: float
    is_active: bool


class MailboxListResponse(BaseModel):
    items: list[MailboxItem]


class CreateMailboxRequest(BaseModel):
    user_id: str
    domain_id: str
    local_part: str = Field(min_length=1, max_length=64)
    quota_mb: int = Field(default=1024, ge=64, le=102400)


class UpdateMailboxRequest(BaseModel):
    quota_mb: int | None = Field(default=None, ge=64, le=102400)
    is_active: bool | None = None


class AliasItem(BaseModel):
    id: str
    domain_id: str
    source_address: str
    destination_address: str
    is_catch_all: bool
    is_active: bool


class AliasListResponse(BaseModel):
    items: list[AliasItem]


class CreateAliasRequest(BaseModel):
    domain_id: str
    source_address: EmailStr
    destination_address: EmailStr
    is_catch_all: bool = False


@router.get("/stats", response_model=DomainAdminStats)
async def get_stats() -> DomainAdminStats:
    async with AsyncSessionLocal() as db:
        domains = int(await db.scalar(select(func.count(Domain.id))) or 0)
        mailboxes = int(await db.scalar(select(func.count(Mailbox.id))) or 0)
        aliases = int(await db.scalar(select(func.count(Alias.id))) or 0)
        suspended = int(await db.scalar(select(func.count(Domain.id)).where(Domain.is_suspended == True)) or 0)
    return DomainAdminStats(
        domains=domains,
        mailboxes=mailboxes,
        aliases=aliases,
        suspended_domains=suspended,
    )


@router.get("/mailboxes", response_model=MailboxListResponse)
async def list_mailboxes() -> MailboxListResponse:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Mailbox).order_by(Mailbox.created_at.desc()))).scalars().all()
    return MailboxListResponse(
        items=[
            MailboxItem(
                id=str(m.id),
                user_id=str(m.user_id),
                domain_id=str(m.domain_id),
                local_part=m.local_part,
                full_address=m.full_address,
                quota_mb=int(m.quota_mb or 0),
                used_mb=float(m.used_mb or 0),
                is_active=bool(m.is_active),
            )
            for m in rows
        ]
    )


@router.post("/mailboxes", response_model=MailboxItem)
async def create_mailbox(payload: CreateMailboxRequest) -> MailboxItem:
    try:
        domain_id = UUID(payload.domain_id)
        user_id = UUID(payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain_id or user_id") from exc
    async with AsyncSessionLocal() as db:
        domain_exists = await db.scalar(select(Domain.id).where(Domain.id == domain_id))
        user_exists = await db.scalar(select(User.id).where(User.id == user_id))
        if domain_exists is None or user_exists is None:
            raise HTTPException(status_code=404, detail="Domain or user not found")
        domain_name = (await db.scalar(select(Domain.name).where(Domain.id == domain_id))) or ""
        full_address = f"{payload.local_part.strip().lower()}@{domain_name.lower()}"
        mailbox = Mailbox(
            user_id=user_id,
            domain_id=domain_id,
            local_part=payload.local_part.strip().lower(),
            full_address=full_address,
            quota_mb=payload.quota_mb,
            is_active=True,
        )
        db.add(mailbox)
        await db.commit()
        await db.refresh(mailbox)
    return MailboxItem(
        id=str(mailbox.id),
        user_id=str(mailbox.user_id),
        domain_id=str(mailbox.domain_id),
        local_part=mailbox.local_part,
        full_address=mailbox.full_address,
        quota_mb=int(mailbox.quota_mb or 0),
        used_mb=float(mailbox.used_mb or 0),
        is_active=bool(mailbox.is_active),
    )


@router.patch("/mailboxes/{mailbox_id}", response_model=MailboxItem)
async def update_mailbox(mailbox_id: str, payload: UpdateMailboxRequest) -> MailboxItem:
    try:
        mailbox_uuid = UUID(mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        mailbox = (await db.execute(select(Mailbox).where(Mailbox.id == mailbox_uuid))).scalar_one_or_none()
        if mailbox is None:
            raise HTTPException(status_code=404, detail="Mailbox not found")
        if payload.quota_mb is not None:
            mailbox.quota_mb = payload.quota_mb
        if payload.is_active is not None:
            mailbox.is_active = payload.is_active
        await db.commit()
        await db.refresh(mailbox)
    return MailboxItem(
        id=str(mailbox.id),
        user_id=str(mailbox.user_id),
        domain_id=str(mailbox.domain_id),
        local_part=mailbox.local_part,
        full_address=mailbox.full_address,
        quota_mb=int(mailbox.quota_mb or 0),
        used_mb=float(mailbox.used_mb or 0),
        is_active=bool(mailbox.is_active),
    )


@router.get("/aliases", response_model=AliasListResponse)
async def list_aliases() -> AliasListResponse:
    async with AsyncSessionLocal() as db:
        aliases = (await db.execute(select(Alias).order_by(Alias.created_at.desc()))).scalars().all()
    return AliasListResponse(
        items=[
            AliasItem(
                id=str(alias.id),
                domain_id=str(alias.domain_id),
                source_address=alias.source_address or "",
                destination_address=alias.destination_address or "",
                is_catch_all=bool(alias.is_catch_all),
                is_active=bool(alias.is_active),
            )
            for alias in aliases
        ]
    )


@router.post("/aliases", response_model=AliasItem)
async def create_alias(payload: CreateAliasRequest) -> AliasItem:
    try:
        domain_id = UUID(payload.domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid domain_id") from exc
    async with AsyncSessionLocal() as db:
        domain_exists = await db.scalar(select(Domain.id).where(Domain.id == domain_id))
        if domain_exists is None:
            raise HTTPException(status_code=404, detail="Domain not found")
        alias = Alias(
            domain_id=domain_id,
            source_address=str(payload.source_address),
            destination_address=str(payload.destination_address),
            is_catch_all=payload.is_catch_all,
            is_active=True,
        )
        db.add(alias)
        await db.commit()
        await db.refresh(alias)
    return AliasItem(
        id=str(alias.id),
        domain_id=str(alias.domain_id),
        source_address=alias.source_address or "",
        destination_address=alias.destination_address or "",
        is_catch_all=bool(alias.is_catch_all),
        is_active=bool(alias.is_active),
    )
