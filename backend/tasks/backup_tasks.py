from backend.tasks.celery_app import celery_app


@celery_app.task(queue='backup')
def run_scheduled_backup() -> str:
    from backend.tasks.task_db import run_async
    from backend.services.backup_service import auto_backup

    job_id = run_async(auto_backup(db=None))
    return f"backup-done:{job_id}"
