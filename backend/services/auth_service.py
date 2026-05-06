from __future__ import annotations

from datetime import timedelta

from backend.config import settings
from backend.core.security import create_token


async def create_access_token(user_id: str) -> str:
    return create_token(user_id, timedelta(minutes=settings.access_token_expire_minutes))


async def create_refresh_token(user_id: str) -> str:
    return create_token(user_id, timedelta(days=settings.refresh_token_expire_days))
