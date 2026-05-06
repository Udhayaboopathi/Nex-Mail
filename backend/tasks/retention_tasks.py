from backend.tasks.celery_app import celery_app
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import BackupJob

@celery_app.task(queue='default')
def enforce_retention() -> str:
    import asyncio

    async def _run() -> int:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
        async with AsyncSessionLocal() as db:
            jobs = (
                await db.execute(
                    select(BackupJob).where(
                        BackupJob.completed_at.is_not(None),
                        BackupJob.completed_at < cutoff,
                    )
                )
            ).scalars().all()
            deleted = len(jobs)
            for job in jobs:
                await db.delete(job)
            await db.commit()
            return deleted

    deleted_count = asyncio.run(_run())
    return f"retention-enforced:{deleted_count}"
