from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Contact

router = APIRouter(tags=["contacts"])


class ContactItem(BaseModel):
    id: str
    email: str
    name: str | None = None
    notes: str | None = None
    created_at: str


class CreateContactRequest(BaseModel):
    user_id: str
    email: str = Field(min_length=1)
    name: str | None = None
    notes: str | None = None


class UpdateContactRequest(BaseModel):
    email: str | None = None
    name: str | None = None
    notes: str | None = None


def _to_item(c: Contact) -> ContactItem:
    return ContactItem(
        id=str(c.id),
        email=c.email or "",
        name=c.name,
        notes=c.notes,
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


@router.get("/", response_model=list[ContactItem])
async def list_contacts(
    q: str = Query(default=""),
    user: dict = Depends(require_any_auth),
) -> list[ContactItem]:
    async with AsyncSessionLocal() as db:
        stmt = select(Contact).order_by(Contact.created_at.desc())
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Contact.email.ilike(like), Contact.name.ilike(like)))
        rows = (await db.execute(stmt)).scalars().all()
    return [_to_item(c) for c in rows]


@router.post("/", response_model=ContactItem)
async def create_contact(payload: CreateContactRequest, user: dict = Depends(require_any_auth)) -> ContactItem:
    try:
        user_uuid = UUID(payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user_id") from exc
    async with AsyncSessionLocal() as db:
        contact = Contact(user_id=user_uuid, email=payload.email, name=payload.name, notes=payload.notes)
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
    return _to_item(contact)


@router.patch("/{contact_id}", response_model=ContactItem)
async def update_contact(contact_id: str, payload: UpdateContactRequest, user: dict = Depends(require_any_auth)) -> ContactItem:
    try:
        contact_uuid = UUID(contact_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid contact_id") from exc
    async with AsyncSessionLocal() as db:
        contact = (await db.execute(select(Contact).where(Contact.id == contact_uuid))).scalar_one_or_none()
        if contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        if payload.email is not None:
            contact.email = payload.email
        if payload.name is not None:
            contact.name = payload.name
        if payload.notes is not None:
            contact.notes = payload.notes
        await db.commit()
        await db.refresh(contact)
    return _to_item(contact)


@router.delete("/{contact_id}")
async def delete_contact(contact_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        contact_uuid = UUID(contact_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid contact_id") from exc
    async with AsyncSessionLocal() as db:
        contact = (await db.execute(select(Contact).where(Contact.id == contact_uuid))).scalar_one_or_none()
        if contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        await db.delete(contact)
        await db.commit()
    return {"ok": True}
