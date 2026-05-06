from backend.tasks.celery_app import celery_app
from datetime import datetime, timezone

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import ScheduledEmail
from backend.smtp.outbound import send_direct

@celery_app.task(queue='email')
def process_scheduled_emails() -> str:
    import asyncio

    async def _run() -> int:
        now = datetime.now(tz=timezone.utc)
        async with AsyncSessionLocal() as db:
            pending = (
                await db.execute(
                    select(ScheduledEmail).where(
                        ScheduledEmail.status == "pending",
                        ScheduledEmail.send_at <= now,
                    )
                )
            ).scalars().all()
            for email in pending:
                recipients = [addr for addr in (email.to_addresses or []) if isinstance(addr, str) and addr]
                try:
                    await send_direct(
                        from_addr="no-reply@localhost",
                        to_list=recipients,
                        subject=email.subject or "(no subject)",
                        body_text=email.body_text or "",
                        body_html=email.body_html,
                    )
                    email.status = "sent"
                    email.error_message = None
                except Exception as exc:
                    email.status = "failed"
                    email.error_message = str(exc)
            await db.commit()
            return len(pending)

    processed = asyncio.run(_run())
    return f"scheduled-emails-processed:{processed}"
