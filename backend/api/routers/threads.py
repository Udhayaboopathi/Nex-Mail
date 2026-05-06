from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import EmailThread

router = APIRouter(tags=["threads"])


class ThreadItem(BaseModel):
    id: str
    subject: str
    participants: list[str]
    last_message_at: str | None
    message_count: int
    has_unread: bool


@router.get("/{folder}", response_model=list[ThreadItem])
async def list_threads(folder: str, user: dict = Depends(require_any_auth)) -> list[ThreadItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(EmailThread).order_by(EmailThread.last_message_at.desc()).limit(50)
        )).scalars().all()
    return [
        ThreadItem(
            id=str(t.id),
            subject=t.subject or "(no subject)",
            participants=list(t.participants or []),
            last_message_at=t.last_message_at.isoformat() if t.last_message_at else None,
            message_count=int(t.message_count or 1),
            has_unread=bool(t.has_unread),
        )
        for t in rows
    ]


@router.get("/{thread_id}/messages", response_model=list[dict])
async def get_thread_messages(thread_id: str, user: dict = Depends(require_any_auth)) -> list[dict]:
    return []
