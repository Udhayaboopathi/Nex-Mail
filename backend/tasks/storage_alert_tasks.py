from backend.tasks.celery_app import celery_app
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models import Domain

@celery_app.task(queue='default')
def check_storage_alerts() -> str:
    import asyncio

    async def _run() -> int:
        async with AsyncSessionLocal() as db:
            domains = (await db.execute(select(Domain))).scalars().all()
            threshold_hits = 0
            for domain in domains:
                quota_mb = max(int(domain.storage_quota_gb or 0) * 1024, 1)
                used_mb = int((domain.used_storage_gb or 0) * 1024)
                if used_mb >= int(quota_mb * 0.9):
                    threshold_hits += 1
            return threshold_hits

    alerts = asyncio.run(_run())
    return f"storage-alerts-checked:{alerts}"
