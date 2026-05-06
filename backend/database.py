from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import settings

_engine_kwargs: dict = {
    "future": True,
    "echo": False,
    "pool_pre_ping": True,
    "pool_timeout": 25,
}

# Fail fast instead of hanging (Traefik→504) when Postgres is misconfigured or unreachable.
if "+asyncpg" in settings.database_url:
    _engine_kwargs["connect_args"] = {"timeout": 15, "command_timeout": 30}

engine = create_async_engine(settings.database_url, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
