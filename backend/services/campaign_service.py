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

        # Resolve recipient list from campaign.recipients (JSONB list of email strings)
        recipients: list[str] = []
        raw = campaign.recipients
        if isinstance(raw, list):
            recipients = [str(r).strip() for r in raw if r]
        elif isinstance(raw, str) and raw:
            recipients = [r.strip() for r in raw.split(",") if r.strip()]

        # If no explicit list, fall back to all active mailboxes on this mailbox's domain
        if not recipients:
            from sqlalchemy import select as _select
            mailbox_row = (await db.execute(
                _select(Mailbox).where(Mailbox.id == campaign.mailbox_id)
            )).scalar_one_or_none()
            if mailbox_row:
                domain_mailboxes = (await db.execute(
                    _select(Mailbox.full_address).where(
                        Mailbox.domain_id == mailbox_row.domain_id,
                        Mailbox.is_active == True,
                    )
                )).scalars().all()
                recipients = list(domain_mailboxes)

        sent = 0
        failed = 0

        for recipient in recipients:
            try:
                from backend.tasks.delivery import deliver_email  # lazy import
                deliver_email.delay({
                    "from_addr": campaign.from_address or f"campaigns@{campaign.domain_id}",
                    "to_list": [recipient],
                    "subject": campaign.subject or "(No subject)",
                    "body_html": campaign.body_html or "",
                    "body_text": campaign.body_text or "",
                    "campaign_id": str(campaign.id),
                })
                sent += 1
            except Exception:
                failed += 1

        campaign.status = "sending"
        campaign.sent_count = sent
        campaign.failed_count = failed
        campaign.started_at = datetime.now(tz=timezone.utc)
        await db.commit()

    return {"sent": sent, "failed": failed}
