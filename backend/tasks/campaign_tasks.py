from sqlalchemy import select

from backend.tasks.celery_app import celery_app
from backend.tasks.task_db import task_db_session, run_async
from backend.models import Campaign
from backend.services.campaign_service import send_campaign


@celery_app.task(queue='email')
def process_scheduled_campaigns() -> str:
    with task_db_session() as db:
        rows = db.execute(
            select(Campaign.id).where(Campaign.status == "scheduled")
        ).all()

    sent = 0
    for (campaign_id,) in rows:
        result = run_async(send_campaign(str(campaign_id)))
        sent += result.get("sent", 0)

    return f"campaigns-processed:{sent}"
