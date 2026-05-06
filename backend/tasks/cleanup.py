from datetime import datetime, timezone

from sqlalchemy import select

from backend.tasks.celery_app import celery_app
from backend.tasks.task_db import task_db_session
from backend.models import PasswordResetToken, Session


@celery_app.task(queue='default')
def cleanup_expired_tokens() -> str:
    now = datetime.now(tz=timezone.utc)

    with task_db_session() as db:
        sessions = db.execute(
            select(Session).where(Session.expires_at < now)
        ).scalars().all()

        resets = db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.expires_at < now,
                PasswordResetToken.used_at.is_(None),
            )
        ).scalars().all()

        cleaned = len(sessions) + len(resets)

        for record in sessions:
            db.delete(record)
        for record in resets:
            db.delete(record)

    return f"cleanup-done:{cleaned}"
