from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from backend.config import settings

celery_app = Celery("email_platform", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_queues = (
    Queue("default"),
    Queue("email"),
    Queue("backup"),
    Queue("ai"),
)
celery_app.conf.beat_schedule = {
    "scheduled-backup": {
        "task": "backend.tasks.backup_tasks.run_scheduled_backup",
        "schedule": crontab(hour=settings.backup_schedule_hour, minute=0),
        "options": {"queue": "backup"},
    },
    "check-storage-alerts": {
        "task": "backend.tasks.storage_alert_tasks.check_storage_alerts",
        "schedule": 3600.0,
        "options": {"queue": "default"},
    },
    "process-scheduled-emails": {
        "task": "backend.tasks.scheduled_email_tasks.process_scheduled_emails",
        "schedule": 60.0,
        "options": {"queue": "email"},
    },
    "process-scheduled-campaigns": {
        "task": "backend.tasks.campaign_tasks.process_scheduled_campaigns",
        "schedule": 300.0,
        "options": {"queue": "email"},
    },
    "enforce-retention": {
        "task": "backend.tasks.retention_tasks.enforce_retention",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "default"},
    },
    "process-priority-inbox": {
        "task": "backend.tasks.ai_tasks.process_priority_inbox",
        "schedule": 1800.0,
        "options": {"queue": "ai"},
    },
    "cleanup-expired-tokens": {
        "task": "backend.tasks.cleanup.cleanup_expired_tokens",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "default"},
    },
}
celery_app.conf.task_routes = {
    "backend.tasks.delivery.*": {"queue": "email"},
    "backend.tasks.backup_tasks.*": {"queue": "backup"},
    "backend.tasks.ai_tasks.*": {"queue": "ai"},
    "backend.tasks.cleanup.*": {"queue": "default"},
}
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True
celery_app.autodiscover_tasks(
    [
        "backend.tasks.delivery",
        "backend.tasks.cleanup",
        "backend.tasks.backup_tasks",
        "backend.tasks.campaign_tasks",
        "backend.tasks.scheduled_email_tasks",
        "backend.tasks.storage_alert_tasks",
        "backend.tasks.retention_tasks",
        "backend.tasks.ai_tasks",
    ]
)
