from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Label

router = APIRouter(tags=["labels"])


class LabelItem(BaseModel):
    id: str
    name: str
    color: str
    mailbox_id: str
    created_at: str


class CreateLabelRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    mailbox_id: str


class UpdateLabelRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


def _to_item(l: Label) -> LabelItem:
    return LabelItem(
        id=str(l.id),
        name=l.name or "",
        color=l.color or "#6366f1",
        mailbox_id=str(l.mailbox_id),
        created_at=l.created_at.isoformat() if l.created_at else "",
    )


@router.get("/", response_model=list[LabelItem])
async def list_labels(user: dict = Depends(require_any_auth)) -> list[LabelItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Label).order_by(Label.created_at.desc()))).scalars().all()
    return [_to_item(l) for l in rows]


@router.post("/", response_model=LabelItem)
async def create_label(payload: CreateLabelRequest, user: dict = Depends(require_any_auth)) -> LabelItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        label = Label(mailbox_id=mailbox_uuid, name=payload.name, color=payload.color)
        db.add(label)
        await db.commit()
        await db.refresh(label)
    return _to_item(label)


@router.patch("/{label_id}", response_model=LabelItem)
async def update_label(label_id: str, payload: UpdateLabelRequest, user: dict = Depends(require_any_auth)) -> LabelItem:
    try:
        label_uuid = UUID(label_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid label_id") from exc
    async with AsyncSessionLocal() as db:
        label = (await db.execute(select(Label).where(Label.id == label_uuid))).scalar_one_or_none()
        if label is None:
            raise HTTPException(status_code=404, detail="Label not found")
        if payload.name is not None:
            label.name = payload.name
        if payload.color is not None:
            label.color = payload.color
        await db.commit()
        await db.refresh(label)
    return _to_item(label)


@router.delete("/{label_id}")
async def delete_label(label_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        label_uuid = UUID(label_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid label_id") from exc
    async with AsyncSessionLocal() as db:
        label = (await db.execute(select(Label).where(Label.id == label_uuid))).scalar_one_or_none()
        if label is None:
            raise HTTPException(status_code=404, detail="Label not found")
        await db.delete(label)
        await db.commit()
    return {"ok": True}


@router.post("/{label_id}/apply")
async def apply_label_to_email(label_id: str, body: dict, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    return {"ok": True}


@router.delete("/{label_id}/email/{uid}")
async def remove_label_from_email(label_id: str, uid: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    return {"ok": True}
