from backend.tasks.celery_app import celery_app
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Campaign
from backend.services.campaign_service import send_campaign

@celery_app.task(queue='email')
def process_scheduled_campaigns() -> str:
    import asyncio

    async def _run() -> int:
        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(select(Campaign.id).where(Campaign.status == "scheduled"))
            ).all()
        sent = 0
        for (campaign_id,) in rows:
            result = await send_campaign(str(campaign_id))
            sent += result["sent"]
        return sent

    sent_total = asyncio.run(_run())
    return f"campaigns-processed:{sent_total}"
