from backend.tasks.celery_app import celery_app


@celery_app.task(queue='ai')
def process_priority_inbox() -> str:
    from backend.tasks.task_db import run_async
    from backend.services.ai_service import rank_mailboxes_by_usage

    ranked = run_async(rank_mailboxes_by_usage(limit=25, db=None))
    return f"priority-inbox-updated:{len(ranked)}"
