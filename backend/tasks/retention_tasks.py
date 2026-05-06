from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.tasks.celery_app import celery_app
from backend.tasks.task_db import task_db_session
from backend.models import BackupJob


@celery_app.task(queue='default')
def enforce_retention() -> str:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)

    with task_db_session() as db:
        jobs = db.execute(
            select(BackupJob).where(
                BackupJob.completed_at.is_not(None),
                BackupJob.completed_at < cutoff,
            )
        ).scalars().all()

        deleted = len(jobs)
        for job in jobs:
            db.delete(job)

    return f"retention-enforced:{deleted}"
