import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Webhook

router = APIRouter(tags=["webhooks"])


class WebhookItem(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool
    failure_count: int
    last_triggered_at: str | None = None
    created_at: str


class CreateWebhookRequest(BaseModel):
    mailbox_id: str
    url: str = Field(min_length=1)
    events: list[str] = ["receive", "send"]


class UpdateWebhookRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


def _to_item(w: Webhook) -> WebhookItem:
    return WebhookItem(
        id=str(w.id),
        url=w.url or "",
        events=list(w.events or []),
        is_active=bool(w.is_active),
        failure_count=int(w.failure_count or 0),
        last_triggered_at=w.last_triggered_at.isoformat() if w.last_triggered_at else None,
        created_at=w.created_at.isoformat() if w.created_at else "",
    )


@router.get("/", response_model=list[WebhookItem])
async def list_webhooks(user: dict = Depends(require_any_auth)) -> list[WebhookItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))).scalars().all()
    return [_to_item(w) for w in rows]


@router.post("/", response_model=WebhookItem)
async def create_webhook(payload: CreateWebhookRequest, user: dict = Depends(require_any_auth)) -> WebhookItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        webhook = Webhook(
            mailbox_id=mailbox_uuid,
            url=payload.url,
            events=payload.events,
            secret=secrets.token_hex(32),
        )
        db.add(webhook)
        await db.commit()
        await db.refresh(webhook)
    return _to_item(webhook)


@router.patch("/{webhook_id}", response_model=WebhookItem)
async def update_webhook(webhook_id: str, payload: UpdateWebhookRequest, user: dict = Depends(require_any_auth)) -> WebhookItem:
    try:
        wh_uuid = UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook_id") from exc
    async with AsyncSessionLocal() as db:
        webhook = (await db.execute(select(Webhook).where(Webhook.id == wh_uuid))).scalar_one_or_none()
        if webhook is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        if payload.url is not None:
            webhook.url = payload.url
        if payload.events is not None:
            webhook.events = payload.events
        if payload.is_active is not None:
            webhook.is_active = payload.is_active
        await db.commit()
        await db.refresh(webhook)
    return _to_item(webhook)


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        wh_uuid = UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook_id") from exc
    async with AsyncSessionLocal() as db:
        webhook = (await db.execute(select(Webhook).where(Webhook.id == wh_uuid))).scalar_one_or_none()
        if webhook is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        await db.delete(webhook)
        await db.commit()
    return {"ok": True}


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str, user: dict = Depends(require_any_auth)) -> dict[str, str]:
    try:
        _ = UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook_id") from exc
    return {"status": "test_queued"}
