from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import CalendarEvent

router = APIRouter(tags=['calendar'])


class CalendarEventItem(BaseModel):
    id: str
    mailbox_id: str
    title: str
    start_at: str | None
    end_at: str | None
    location: str | None
    all_day: bool


class CalendarEventListResponse(BaseModel):
    items: list[CalendarEventItem]


@router.get("/", response_model=CalendarEventListResponse)
async def list_items() -> CalendarEventListResponse:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(CalendarEvent).order_by(CalendarEvent.start_at.asc()))).scalars().all()
    return CalendarEventListResponse(
        items=[
            CalendarEventItem(
                id=str(row.id),
                mailbox_id=str(row.mailbox_id),
                title=row.title or "(untitled)",
                start_at=row.start_at.isoformat() if row.start_at else None,
                end_at=row.end_at.isoformat() if row.end_at else None,
                location=row.location,
                all_day=bool(row.all_day),
            )
            for row in rows
        ]
    )
