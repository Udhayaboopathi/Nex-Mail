"""Synchronous DB pool for code that runs outside the FastAPI event loop (e.g. aiosmtpd thread)."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings


def _sync_database_url(url: str) -> str:
    if "+asyncpg" in url:
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


_kw: dict = {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}
if "postgresql" in settings.database_url:
    _kw["connect_args"] = {"connect_timeout": 15}

sync_engine = create_engine(_sync_database_url(settings.database_url), **_kw)
SessionLocalSync = sessionmaker(bind=sync_engine, expire_on_commit=False)
