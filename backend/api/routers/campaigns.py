from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import require_any_auth
from backend.database import AsyncSessionLocal
from backend.models import Campaign
from backend.services.campaign_service import send_campaign

router = APIRouter(tags=["campaigns"])


class CampaignItem(BaseModel):
    id: str
    name: str
    subject: str | None = None
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int
    open_count: int
    click_count: int
    unsubscribe_count: int
    created_at: str
    scheduled_at: str | None = None


class CreateCampaignRequest(BaseModel):
    mailbox_id: str
    name: str = Field(min_length=1, max_length=100)
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    from_name: str | None = None


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    from_name: str | None = None
    scheduled_at: str | None = None


class CampaignSendResponse(BaseModel):
    sent: int
    failed: int


def _to_item(c: Campaign) -> CampaignItem:
    return CampaignItem(
        id=str(c.id),
        name=c.name or "Untitled",
        subject=c.subject,
        status=c.status or "draft",
        total_recipients=int(c.total_recipients or 0),
        sent_count=int(c.sent_count or 0),
        failed_count=int(c.failed_count or 0),
        open_count=int(c.open_count or 0),
        click_count=int(c.click_count or 0),
        unsubscribe_count=int(c.unsubscribe_count or 0),
        created_at=c.created_at.isoformat() if c.created_at else "",
        scheduled_at=c.scheduled_at.isoformat() if c.scheduled_at else None,
    )


@router.get("/", response_model=list[CampaignItem])
async def list_campaigns(user: dict = Depends(require_any_auth)) -> list[CampaignItem]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))).scalars().all()
    return [_to_item(c) for c in rows]


@router.post("/", response_model=CampaignItem)
async def create_campaign(payload: CreateCampaignRequest, user: dict = Depends(require_any_auth)) -> CampaignItem:
    try:
        mailbox_uuid = UUID(payload.mailbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailbox_id") from exc
    async with AsyncSessionLocal() as db:
        campaign = Campaign(
            mailbox_id=mailbox_uuid,
            name=payload.name,
            subject=payload.subject,
            body_html=payload.body_html,
            body_text=payload.body_text,
            from_name=payload.from_name,
            status="draft",
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
    return _to_item(campaign)


@router.patch("/{campaign_id}", response_model=CampaignItem)
async def update_campaign(campaign_id: str, payload: UpdateCampaignRequest, user: dict = Depends(require_any_auth)) -> CampaignItem:
    try:
        c_uuid = UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid campaign_id") from exc
    async with AsyncSessionLocal() as db:
        campaign = (await db.execute(select(Campaign).where(Campaign.id == c_uuid))).scalar_one_or_none()
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if payload.name is not None:
            campaign.name = payload.name
        if payload.subject is not None:
            campaign.subject = payload.subject
        if payload.body_html is not None:
            campaign.body_html = payload.body_html
        if payload.body_text is not None:
            campaign.body_text = payload.body_text
        if payload.from_name is not None:
            campaign.from_name = payload.from_name
        if payload.scheduled_at is not None:
            campaign.scheduled_at = datetime.fromisoformat(payload.scheduled_at)
            campaign.status = "scheduled"
        await db.commit()
        await db.refresh(campaign)
    return _to_item(campaign)


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, user: dict = Depends(require_any_auth)) -> dict[str, bool]:
    try:
        c_uuid = UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid campaign_id") from exc
    async with AsyncSessionLocal() as db:
        campaign = (await db.execute(select(Campaign).where(Campaign.id == c_uuid))).scalar_one_or_none()
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found")
        await db.delete(campaign)
        await db.commit()
    return {"ok": True}


@router.post("/{campaign_id}/send", response_model=CampaignSendResponse)
async def send_campaign_now(campaign_id: str, user: dict = Depends(require_any_auth)) -> CampaignSendResponse:
    result = await send_campaign(campaign_id)
    if result["sent"] == 0 and result["failed"] == 0:
        raise HTTPException(status_code=404, detail="Campaign not found or no recipients")
    return CampaignSendResponse(sent=result["sent"], failed=result["failed"])


@router.get("/{campaign_id}/analytics")
async def campaign_analytics(campaign_id: str, user: dict = Depends(require_any_auth)) -> dict:
    try:
        c_uuid = UUID(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid campaign_id") from exc
    async with AsyncSessionLocal() as db:
        campaign = (await db.execute(select(Campaign).where(Campaign.id == c_uuid))).scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    sent = int(campaign.sent_count or 0)
    opens = int(campaign.open_count or 0)
    clicks = int(campaign.click_count or 0)
    unsubs = int(campaign.unsubscribe_count or 0)
    return {
        "sent": sent,
        "opens": opens,
        "clicks": clicks,
        "unsubscribes": unsubs,
        "open_rate": round(opens / max(sent, 1) * 100, 1),
        "click_rate": round(clicks / max(sent, 1) * 100, 1),
        "unsubscribe_rate": round(unsubs / max(sent, 1) * 100, 1),
    }
