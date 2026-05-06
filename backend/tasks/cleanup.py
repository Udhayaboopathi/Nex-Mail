from backend.tasks.celery_app import celery_app
from datetime import datetime, timezone

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import PasswordResetToken, Session

@celery_app.task(queue='default')
def cleanup_expired_tokens() -> str:
    import asyncio

    async def _run() -> int:
        now = datetime.now(tz=timezone.utc)
        async with AsyncSessionLocal() as db:
            sessions = (await db.execute(select(Session).where(Session.expires_at < now))).scalars().all()
            resets = (
                await db.execute(
                    select(PasswordResetToken).where(
                        PasswordResetToken.expires_at < now,
                        PasswordResetToken.used_at.is_(None),
                    )
                )
            ).scalars().all()
            cleaned = len(sessions) + len(resets)
            for record in sessions:
                await db.delete(record)
            for record in resets:
                await db.delete(record)
            await db.commit()
            return cleaned

    return f"cleanup-done:{asyncio.run(_run())}"
