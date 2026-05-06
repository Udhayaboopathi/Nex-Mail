"""Campaign delivery service.

send_campaign — fetches a campaign, resolves recipients, and dispatches
each message via the async SMTP outbound pipeline (or Celery task queue).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models.all_models import Campaign, Mailbox


async def send_campaign(campaign_id: str) -> dict[str, int]:
    """
    Dispatch all pending messages for a campaign.

    Returns {"sent": N, "failed": M}.
    """
    async with AsyncSessionLocal() as db:
        campaign: Campaign | None = (
            await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        ).scalar_one_or_none()

        if not campaign:
            return {"sent": 0, "failed": 0}

        if campaign.status not in ("draft", "scheduled"):
            return {"sent": int(campaign.sent_count or 0), "failed": int(campaign.failed_count or 0)}

        # Resolve recipient list from campaign.recipient_list (comma-separated emails or mailbox IDs)
        recipients: list[str] = []
        raw = campaign.recipient_list or ""
        if raw:
            recipients = [r.strip() for r in raw.split(",") if r.strip()]

        # If no explicit list, fall back to all active mailboxes in the domain
        if not recipients and campaign.domain_id:
            mailboxes = (
                await db.execute(
                    select(Mailbox.full_address).where(
                        Mailbox.domain_id == campaign.domain_id,
                        Mailbox.is_active == True,
                    )
                )
            ).scalars().all()
            recipients = list(mailboxes)

        sent = 0
        failed = 0

        for recipient in recipients:
            try:
                # Enqueue via Celery for real async delivery
                from backend.tasks.delivery import send_email_task  # lazy import
                send_email_task.delay(
                    from_address=campaign.from_address or f"campaigns@{campaign.domain_id}",
                    to_address=recipient,
                    subject=campaign.subject or "(No subject)",
                    body_html=campaign.body_html or "",
                    body_text=campaign.body_text or "",
                    campaign_id=str(campaign.id),
                )
                sent += 1
            except Exception:
                failed += 1

        campaign.status = "sending"
        campaign.sent_count = sent
        campaign.failed_count = failed
        campaign.sent_at = datetime.now(tz=timezone.utc)
        await db.commit()

    return {"sent": sent, "failed": failed}
