from backend.tasks.celery_app import celery_app
from backend.services.backup_service import auto_backup

@celery_app.task(queue='backup')
def run_scheduled_backup() -> str:
    import asyncio

    return asyncio.run(auto_backup())
