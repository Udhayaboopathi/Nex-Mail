from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Delegation

router = APIRouter(tags=["delegation"])


class DelegationItem(BaseModel):
    id: str
    owner_mailbox_id: str
    delegate_user_id: str
    permission: str
    created_at: str


class GrantDelegationRequest(BaseModel):
    owner_mailbox_id: str
    delegate_user_id: str
    permission: str = "send_on_behalf"


@router.get("/granted", response_model=list[DelegationItem])
async def list_granted(user: dict = Depends(require_any_auth)) -> list[DelegationItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Delegation).order_by(Delegation.created_at.desc()))).scalars().all()
    return [
        DelegationItem(
            id=str(d.id),
            owner_mailbox_id=str(d.owner_mailbox_id),
            delegate_user_id=str(d.delegate_user_id),
            permission=d.permission or "send_on_behalf",
            created_at=d.created_at.isoformat() if d.created_at else "",
        )
        for d in rows
    ]


@router.get("/received", response_model=list[DelegationItem])
async def list_received(user: dict = Depends(require_any_auth)) -> list[DelegationItem]:
    return []


@router.post("/grant", response_model=DelegationItem)
async def grant_delegation(payload: GrantDelegationRequest, user: dict = Depends(require_any_auth)) -> DelegationItem:
    try:
        owner_uuid = UUID(payload.owner_mailbox_id)
        delegate_uuid = UUID(payload.delegate_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc
    async with AsyncSessionLocal() as db:
        delegation = Delegation(owner_mailbox_id=owner_uuid, delegate_user_id=delegate_uuid, permission=payload.permission)
        db.add(delegation)
        await db.commit()
        await db.refresh(delegation)
    return DelegationItem(
        id=str(delegation.id),
        owner_mailbox_id=str(delegation.owner_mailbox_id),
        delegate_user_id=str(delegation.delegate_user_id),
        permission=delegation.permission or "send_on_behalf",
        created_at=delegation.created_at.isoformat() if delegation.created_at else "",
    )


@router.delete("/revoke/{delegation_id}")
async def revoke_delegation(delegation_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        d_uuid = UUID(delegation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc
    async with AsyncSessionLocal() as db:
        d = (await db.execute(select(Delegation).where(Delegation.id == d_uuid))).scalar_one_or_none()
        if d:
            await db.delete(d)
            await db.commit()
    return {"ok": True}
