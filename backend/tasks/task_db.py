"""
Synchronous database session for Celery tasks.

Celery workers run tasks in forked child processes.  Each call to
asyncio.run() creates a brand-new event loop, but asyncpg connections are
loop-bound – reusing them across asyncio.run() calls raises
"Future attached to a different loop".

The simplest, most robust fix is to use a *synchronous* psycopg2-based
session for all Celery task DB work.  This avoids asyncio entirely inside
the worker process and eliminates the cross-loop problem completely.

Public API
----------
task_db_session() – synchronous context manager; yields a sqlalchemy Session.
run_async(coro)   – runs the coroutine in a one-off event loop and disposes
                    the shared async engine pool afterward so asyncpg
                    connections are never reused across loops.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from backend.config import settings


def _sync_url() -> str:
    url = settings.database_url
    # Convert postgresql+asyncpg://... → postgresql+psycopg2://...
    url = url.replace("+asyncpg", "+psycopg2")
    # plain postgresql:// is already psycopg2-compatible
    return url


def _make_sync_engine():
    return create_engine(_sync_url(), poolclass=NullPool, future=True)


@contextmanager
def task_db_session() -> Generator[Session, None, None]:
    """Yield a synchronous SQLAlchemy Session for use inside Celery tasks."""
    engine = _make_sync_engine()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


def run_async(coro):
    """Run an async coroutine in a fresh event loop.

    Use this when you need to call an async service helper from a Celery
    task.  A new event loop is created and destroyed for each call.

    The process-wide async engine (``backend.database.engine``) pools
    asyncpg connections that are bound to the loop that created them.
    Without disposing the pool after each run, the next ``run_async`` call
    can pull a stale connection and raise *Future attached to a different
    loop* or *another operation is in progress*.
    """
    import asyncio

    from backend.database import engine

    async def _run_with_cleanup():
        try:
            return await coro
        finally:
            await engine.dispose()

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_with_cleanup())
    finally:
        try:
            # Cancel any pending tasks and close the loop cleanly.
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
