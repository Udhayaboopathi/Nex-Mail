from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Campaign
from backend.smtp.outbound import send_direct


async def health() -> dict[str, str]:
    return {"service": "ok"}


async def send_campaign(campaign_id: str) -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        campaign_result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = campaign_result.scalar_one_or_none()
        if campaign is None:
            return {"sent": 0, "failed": 0}
        recipients = [item.get("email", "") for item in (campaign.recipients or []) if isinstance(item, dict) and item.get("email")]
        sent = 0
        failed = 0
        if recipients:
            delivery = await send_direct(
                from_addr="no-reply@localhost",
                to_list=recipients,
                subject=campaign.subject or "(no subject)",
                body_text=campaign.body_text or "",
                body_html=campaign.body_html,
            )
            failed = len([x for x in delivery["failed_recipients"] if isinstance(x, str)])
            sent = len(recipients) - failed
        campaign.status = "sent" if failed == 0 else "partial"
        campaign.started_at = campaign.started_at or datetime.now(tz=timezone.utc)
        campaign.completed_at = datetime.now(tz=timezone.utc)
        campaign.sent_count = sent
        campaign.failed_count = failed
        await db.commit()
        return {"sent": sent, "failed": failed}
