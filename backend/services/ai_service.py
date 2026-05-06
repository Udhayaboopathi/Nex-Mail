from __future__ import annotations

from sqlalchemy import case, select

from backend.database import AsyncSessionLocal
from backend.models import Mailbox


async def health() -> dict[str, str]:
    return {"service": "ok"}


async def rank_mailboxes_by_usage(limit: int = 20) -> list[dict[str, float | str]]:
    usage_score = case((Mailbox.quota_mb > 0, Mailbox.used_mb / Mailbox.quota_mb), else_=0.0)
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Mailbox.full_address, Mailbox.used_mb, Mailbox.quota_mb, usage_score.label("priority_score"))
                .order_by(usage_score.desc())
                .limit(limit)
            )
        ).all()
    return [
        {
            "full_address": str(address),
            "used_mb": float(used or 0),
            "quota_mb": float(quota or 0),
            "priority_score": float(score or 0),
        }
        for address, used, quota, score in rows
    ]
