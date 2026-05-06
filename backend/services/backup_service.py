from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models import BackupJob, Mailbox


async def health() -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(BackupJob.id)))
    return {"service": "ok", "jobs": str(count or 0)}


async def create_full_backup(db: AsyncSession | None = None) -> str:
    async def _do(session: AsyncSession) -> str:
        mailbox_count = await session.scalar(select(func.count(Mailbox.id)))
        job = BackupJob(
            type="full",
            status="completed",
            total_messages=int(mailbox_count or 0),
            file_path=f"/tmp/backups/full-{int(datetime.now(tz=timezone.utc).timestamp())}.zip",
            completed_at=datetime.now(tz=timezone.utc),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return str(job.id)

    if db is not None:
        return await _do(db)
    async with AsyncSessionLocal() as fresh:
        return await _do(fresh)


async def auto_backup(db: AsyncSession | None = None) -> str:
    return await create_full_backup(db)
