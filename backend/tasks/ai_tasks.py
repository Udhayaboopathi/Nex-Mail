from backend.tasks.celery_app import celery_app
from backend.services.ai_service import rank_mailboxes_by_usage

@celery_app.task(queue='ai')
def process_priority_inbox() -> str:
    import asyncio

    ranked = asyncio.run(rank_mailboxes_by_usage(limit=25))
    return f"priority-inbox-updated:{len(ranked)}"
