"""AI / priority-inbox service.

rank_mailboxes_by_usage — returns the N mailboxes with the highest
storage utilisation ratio, acting as a simple proxy for "priority".
When an Anthropic key is configured this could be extended to call
Claude for richer ranking; for now it is a pure DB query.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models.all_models import Mailbox


async def rank_mailboxes_by_usage(limit: int = 20) -> list[dict]:
    """Return mailboxes sorted by used_mb / quota_mb descending."""
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Mailbox)
                .where(Mailbox.is_active == True)
                .order_by((Mailbox.used_mb / (Mailbox.quota_mb + 1)).desc())
                .limit(limit)
            )
        ).scalars().all()

    return [
        {
            "full_address": r.full_address or "",
            "used_mb": float(r.used_mb or 0),
            "quota_mb": float(r.quota_mb or 1024),
            "priority_score": round(float(r.used_mb or 0) / max(float(r.quota_mb or 1), 1), 4),
        }
        for r in rows
    ]
