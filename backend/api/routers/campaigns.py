from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Campaign
from backend.services.campaign_service import send_campaign

router = APIRouter(tags=["campaigns"])


class CampaignSummary(BaseModel):
    id: str
    name: str
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int


class CampaignListResponse(BaseModel):
    items: list[CampaignSummary]


class CampaignSendResponse(BaseModel):
    sent: int
    failed: int


@router.get("/", response_model=CampaignListResponse)
async def list_campaigns() -> CampaignListResponse:
    async with AsyncSessionLocal() as db:
        campaigns = (await db.execute(select(Campaign))).scalars().all()
    items = [
        CampaignSummary(
            id=str(c.id),
            name=c.name or "Untitled campaign",
            status=c.status,
            total_recipients=int(c.total_recipients or 0),
            sent_count=int(c.sent_count or 0),
            failed_count=int(c.failed_count or 0),
        )
        for c in campaigns
    ]
    return CampaignListResponse(items=items)


@router.post("/{campaign_id}/send", response_model=CampaignSendResponse)
async def send_campaign_now(campaign_id: str) -> CampaignSendResponse:
    result = await send_campaign(campaign_id)
    if result["sent"] == 0 and result["failed"] == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignSendResponse(sent=result["sent"], failed=result["failed"])
