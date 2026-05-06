from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import CalendarEvent

router = APIRouter(tags=["calendar"])


class CalendarEventItem(BaseModel):
    id: str
    mailbox_id: str
    uid: str | None = None
    title: str
    description: str | None = None
    location: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    all_day: bool
    rrule: str | None = None
    attendees: list = []


class CreateEventRequest(BaseModel):
    mailbox_id: str
    title: str
    description: str | None = None
    location: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    all_day: bool = False
    rrule: str | None = None
    attendees: list = []


class UpdateEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    all_day: bool | None = None
    rrule: str | None = None
    attendees: list | None = None


def _to_item(e: CalendarEvent) -> CalendarEventItem:
    return CalendarEventItem(
        id=str(e.id),
        mailbox_id=str(e.mailbox_id),
        uid=e.uid,
        title=e.title or "(untitled)",
        description=e.description,
        location=e.location,
        start_at=e.start_at.isoformat() if e.start_at else None,
        end_at=e.end_at.isoformat() if e.end_at else None,
        all_day=bool(e.all_day),
        rrule=e.rrule,
        attendees=list(e.attendees or []),
    )


@router.get("/", response_model=list[CalendarEventItem])
async def list_events(user: dict = Depends(require_any_auth)) -> list[CalendarEventItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(CalendarEvent).order_by(CalendarEvent.start_at.asc()))).scalars().all()
    return [_to_item(e) for e in rows]


@router.post("/", response_model=CalendarEventItem)
async def create_event(payload: CreateEventRequest, user: dict = Depends(require_any_auth)) -> CalendarEventItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    start = datetime.fromisoformat(payload.start_at) if payload.start_at else None
    end = datetime.fromisoformat(payload.end_at) if payload.end_at else None
    async with AsyncSessionLocal() as db:
        import uuid as _uuid
        event = CalendarEvent(
            mailbox_id=mailbox_uuid, uid=str(_uuid.uuid4()),
            title=payload.title, description=payload.description,
            location=payload.location, start_at=start, end_at=end,
            all_day=payload.all_day, rrule=payload.rrule, attendees=payload.attendees,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
    return _to_item(event)


@router.patch("/{event_id}", response_model=CalendarEventItem)
async def update_event(event_id: str, payload: UpdateEventRequest, user: dict = Depends(require_any_auth)) -> CalendarEventItem:
    try:
        ev_uuid = UUID(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid event_id") from exc
    async with AsyncSessionLocal() as db:
        ev = (await db.execute(select(CalendarEvent).where(CalendarEvent.id == ev_uuid))).scalar_one_or_none()
        if ev is None:
            raise HTTPException(status_code=404, detail="Event not found")
        if payload.title is not None:
            ev.title = payload.title
        if payload.description is not None:
            ev.description = payload.description
        if payload.location is not None:
            ev.location = payload.location
        if payload.start_at is not None:
            ev.start_at = datetime.fromisoformat(payload.start_at)
        if payload.end_at is not None:
            ev.end_at = datetime.fromisoformat(payload.end_at)
        if payload.all_day is not None:
            ev.all_day = payload.all_day
        if payload.rrule is not None:
            ev.rrule = payload.rrule
        if payload.attendees is not None:
            ev.attendees = payload.attendees
        ev.updated_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await db.refresh(ev)
    return _to_item(ev)


@router.delete("/{event_id}")
async def delete_event(event_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        ev_uuid = UUID(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid event_id") from exc
    async with AsyncSessionLocal() as db:
        ev = (await db.execute(select(CalendarEvent).where(CalendarEvent.id == ev_uuid))).scalar_one_or_none()
        if ev is None:
            raise HTTPException(status_code=404, detail="Event not found")
        await db.delete(ev)
        await db.commit()
    return {"ok": True}
