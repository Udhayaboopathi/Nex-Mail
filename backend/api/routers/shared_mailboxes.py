from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import SharedMailbox, SharedMailboxMember

router = APIRouter(tags=["shared_mailboxes"])


class MemberItem(BaseModel):
    user_id: str
    permission: str
    added_at: str | None = None


class SharedMailboxItem(BaseModel):
    id: str
    mailbox_id: str
    display_name: str
    members: list[MemberItem]
    created_at: str


class CreateSharedMailboxRequest(BaseModel):
    mailbox_id: str
    domain_id: str
    display_name: str = Field(min_length=1, max_length=100)


class AddMemberRequest(BaseModel):
    user_id: str
    permission: str = "read_write"


@router.get("/", response_model=list[SharedMailboxItem])
async def list_shared_mailboxes(user: dict = Depends(require_any_auth)) -> list[SharedMailboxItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(SharedMailbox).order_by(SharedMailbox.created_at.desc()))).scalars().all()
        result = []
        for sm in rows:
            members_rows = (await db.execute(
                select(SharedMailboxMember).where(SharedMailboxMember.shared_mailbox_id == sm.id)
            )).scalars().all()
            result.append(SharedMailboxItem(
                id=str(sm.id),
                mailbox_id=str(sm.mailbox_id),
                display_name=sm.display_name or "",
                members=[MemberItem(user_id=str(m.user_id), permission=m.permission or "read_write",
                                    added_at=m.added_at.isoformat() if m.added_at else None) for m in members_rows],
                created_at=sm.created_at.isoformat() if sm.created_at else "",
            ))
    return result


@router.post("/", response_model=SharedMailboxItem)
async def create_shared_mailbox(payload: CreateSharedMailboxRequest, user: dict = Depends(require_any_auth)) -> SharedMailboxItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
        domain_uuid = UUID(payload.domain_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id or domain_id") from exc
    async with AsyncSessionLocal() as db:
        sm = SharedMailbox(mailbox_id=mailbox_uuid, domain_id=domain_uuid, display_name=payload.display_name)
        db.add(sm)
        await db.commit()
        await db.refresh(sm)
    return SharedMailboxItem(id=str(sm.id), mailbox_id=str(sm.mailbox_id), display_name=sm.display_name or "", members=[], created_at=sm.created_at.isoformat() if sm.created_at else "")


@router.post("/{shared_mailbox_id}/members")
async def add_member(shared_mailbox_id: str, payload: AddMemberRequest, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        sm_uuid = UUID(shared_mailbox_id)
        user_uuid = UUID(payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc
    async with AsyncSessionLocal() as db:
        member = SharedMailboxMember(shared_mailbox_id=sm_uuid, user_id=user_uuid, permission=payload.permission)
        db.add(member)
        await db.commit()
    return {"ok": True}


@router.delete("/{shared_mailbox_id}/members/{uid}")
async def remove_member(shared_mailbox_id: str, uid: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        sm_uuid = UUID(shared_mailbox_id)
        user_uuid = UUID(uid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc
    async with AsyncSessionLocal() as db:
        member = (await db.execute(
            select(SharedMailboxMember).where(
                SharedMailboxMember.shared_mailbox_id == sm_uuid,
                SharedMailboxMember.user_id == user_uuid,
            )
        )).scalar_one_or_none()
        if member:
            await db.delete(member)
            await db.commit()
    return {"ok": True}


@router.delete("/{shared_mailbox_id}")
async def delete_shared_mailbox(shared_mailbox_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        sm_uuid = UUID(shared_mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc
    async with AsyncSessionLocal() as db:
        sm = (await db.execute(select(SharedMailbox).where(SharedMailbox.id == sm_uuid))).scalar_one_or_none()
        if sm:
            await db.delete(sm)
            await db.commit()
    return {"ok": True}
