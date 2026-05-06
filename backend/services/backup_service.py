from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from backend.database import AsyncSessionLocal
from backend.models import BackupJob, Mailbox


async def health() -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(BackupJob.id)))
    return {"service": "ok", "jobs": str(count or 0)}


async def create_full_backup() -> str:
    async with AsyncSessionLocal() as db:
        mailbox_count = await db.scalar(select(func.count(Mailbox.id)))
        job = BackupJob(
            type="full",
            status="completed",
            total_messages=int(mailbox_count or 0),
            file_path=f"/tmp/backups/full-{int(datetime.now(tz=timezone.utc).timestamp())}.zip",
            completed_at=datetime.now(tz=timezone.utc),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return str(job.id)


async def auto_backup() -> str:
    return await create_full_backup()
