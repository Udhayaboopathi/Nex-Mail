"""AI service — priority inbox, summarization, smart reply, label suggestions.

Uses Anthropic Claude when ANTHROPIC_API_KEY is configured.
Falls back to rule-based responses when the key is missing or unavailable.
"""
from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models.all_models import Mailbox


async def rank_mailboxes_by_usage(limit: int = 20, db: AsyncSession | None = None) -> list[dict]:
    """Return mailboxes sorted by used_mb / quota_mb descending."""
    async def _query(session: AsyncSession) -> list:
        rows = (
            await session.execute(
                select(Mailbox)
                .where(Mailbox.is_active == True)
                .order_by((Mailbox.used_mb / (Mailbox.quota_mb + 1)).desc())
                .limit(limit)
            )
        ).scalars().all()
        return rows

    if db is not None:
        rows = await _query(db)
    else:
        async with AsyncSessionLocal() as fresh:
            rows = await _query(fresh)

    return [
        {
            "full_address": r.full_address or "",
            "used_mb": float(r.used_mb or 0),
            "quota_mb": float(r.quota_mb or 1024),
            "priority_score": round(float(r.used_mb or 0) / max(float(r.quota_mb or 1), 1), 4),
        }
        for r in rows
    ]


def _get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or not api_key.startswith("sk-"):
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except Exception:
        return None


async def summarize_thread(thread_id: str) -> str:
    """Summarize an email thread using Claude or fallback."""
    client = _get_client()
    if client is None:
        return "AI summary not available — configure ANTHROPIC_API_KEY."
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": f"Summarize this email thread (ID: {thread_id}) in 2-3 sentences."}],
        )
        return msg.content[0].text if msg.content else "No summary available."
    except Exception as exc:
        return f"Summary unavailable: {exc}"


async def smart_reply_suggestions(message_id: str) -> list[str]:
    """Generate 3 smart reply suggestions for a message."""
    client = _get_client()
    if client is None:
        return [
            "Thank you for your email. I'll review this and get back to you shortly.",
            "I appreciate your message. Could you provide more details?",
            "Thanks for reaching out. I'll follow up on this soon.",
        ]
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"Generate 3 concise, professional email reply options for message {message_id}. Return as JSON array of strings.",
            }],
        )
        import json
        text = msg.content[0].text if msg.content else "[]"
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(s) for s in parsed[:3]]
    except Exception:
        pass
    return ["Thank you for your message.", "I will respond shortly.", "Could you provide more details?"]


async def suggest_labels(message_id: str) -> list[str]:
    """Suggest labels for an email message."""
    client = _get_client()
    if client is None:
        return []
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": f"Suggest 1-3 label names for email {message_id} from: Work, Personal, Finance, Travel, Shopping, Newsletter, Social, Important. Return as JSON array.",
            }],
        )
        import json
        text = msg.content[0].text if msg.content else "[]"
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(s) for s in parsed[:3]]
    except Exception:
        pass
    return []
