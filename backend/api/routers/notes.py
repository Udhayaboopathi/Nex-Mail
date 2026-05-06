from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Note

router = APIRouter(tags=["notes"])


class NoteItem(BaseModel):
    id: str
    title: str | None = None
    body: str
    linked_email_uid: str | None = None
    created_at: str
    updated_at: str


class CreateNoteRequest(BaseModel):
    mailbox_id: str
    title: str | None = None
    body: str = Field(default="")
    linked_email_uid: str | None = None


class UpdateNoteRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    linked_email_uid: str | None = None


def _to_item(n: Note) -> NoteItem:
    return NoteItem(
        id=str(n.id),
        title=n.title,
        body=n.body or "",
        linked_email_uid=n.linked_email_uid,
        created_at=n.created_at.isoformat() if n.created_at else "",
        updated_at=n.updated_at.isoformat() if n.updated_at else "",
    )


@router.get("/", response_model=list[NoteItem])
async def list_notes(user: dict = Depends(require_any_auth)) -> list[NoteItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Note).order_by(Note.updated_at.desc()))).scalars().all()
    return [_to_item(n) for n in rows]


@router.post("/", response_model=NoteItem)
async def create_note(payload: CreateNoteRequest, user: dict = Depends(require_any_auth)) -> NoteItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        note = Note(mailbox_id=mailbox_uuid, title=payload.title, body=payload.body, linked_email_uid=payload.linked_email_uid)
        db.add(note)
        await db.commit()
        await db.refresh(note)
    return _to_item(note)


@router.patch("/{note_id}", response_model=NoteItem)
async def update_note(note_id: str, payload: UpdateNoteRequest, user: dict = Depends(require_any_auth)) -> NoteItem:
    try:
        note_uuid = UUID(note_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid note_id") from exc
    async with AsyncSessionLocal() as db:
        note = (await db.execute(select(Note).where(Note.id == note_uuid))).scalar_one_or_none()
        if note is None:
            raise HTTPException(status_code=404, detail="Note not found")
        if payload.title is not None:
            note.title = payload.title
        if payload.body is not None:
            note.body = payload.body
        if payload.linked_email_uid is not None:
            note.linked_email_uid = payload.linked_email_uid
        note.updated_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await db.refresh(note)
    return _to_item(note)


@router.delete("/{note_id}")
async def delete_note(note_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        note_uuid = UUID(note_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid note_id") from exc
    async with AsyncSessionLocal() as db:
        note = (await db.execute(select(Note).where(Note.id == note_uuid))).scalar_one_or_none()
        if note is None:
            raise HTTPException(status_code=404, detail="Note not found")
        await db.delete(note)
        await db.commit()
    return {"ok": True}
