import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from backend.database import AsyncSessionLocal
from backend.api.middleware.rate_limit import add_rate_limiting
from backend.api.middleware.audit import add_audit_logging
from backend.smtp.server import create_smtp_servers
from backend.imap.server import create_imap_server
from backend.api.routers import auth, super_admin, domain_admin, mail, folders, threads, labels, rules, templates, contacts, calendar, tasks, notes, ai, pgp, campaigns, webhooks, api_keys, send_api, tracking, shared_mailboxes, delegation, spam_reports, ediscovery

logger = logging.getLogger(__name__)


async def _init_db() -> None:
    """Create all tables that don't yet exist (safe to run repeatedly)."""
    try:
        from backend.config import settings
        from backend.database import engine
        from backend.models.base import Base
        import backend.models.all_models  # noqa: F401 — registers all mapped classes
        if not settings.metadata_create_all_on_startup:
            logger.info("Skipping metadata create_all (migrations manage schema).")
            return
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified / created.")
    except Exception as exc:
        logger.error("DB init failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.runtime import set_main_loop

    set_main_loop(asyncio.get_running_loop())
    await _init_db()
    smtp25, smtp587 = await create_smtp_servers()
    imap_server = await create_imap_server()
    imap_task = asyncio.create_task(imap_server.serve_forever())
    yield
    smtp25.stop()
    smtp587.stop()
    imap_server.close()
    await imap_server.wait_closed()
    imap_task.cancel()
    from backend.database import engine

    await engine.dispose()

app = FastAPI(lifespan=lifespan)
add_rate_limiting(app)
add_audit_logging(app)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(super_admin.router, prefix="/api/super-admin")
app.include_router(domain_admin.router, prefix="/api/domain-admin")
app.include_router(mail.router, prefix="/api/mail")
app.include_router(folders.router, prefix="/api/folders")
app.include_router(threads.router, prefix="/api/threads")
app.include_router(labels.router, prefix="/api/labels")
app.include_router(rules.router, prefix="/api/rules")
app.include_router(templates.router, prefix="/api/templates")
app.include_router(contacts.router, prefix="/api/contacts")
app.include_router(calendar.router, prefix="/api/calendar")
app.include_router(tasks.router, prefix="/api/tasks")
app.include_router(notes.router, prefix="/api/notes")
app.include_router(ai.router, prefix="/api/ai")
app.include_router(pgp.router, prefix="/api/pgp")
app.include_router(campaigns.router, prefix="/api/campaigns")
app.include_router(webhooks.router, prefix="/api/webhooks")
app.include_router(api_keys.router, prefix="/api/keys")
app.include_router(send_api.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/track")
app.include_router(shared_mailboxes.router, prefix="/api/shared-mailboxes")
app.include_router(delegation.router, prefix="/api/delegation")
app.include_router(spam_reports.router, prefix="/api/mail/report")
app.include_router(ediscovery.router, prefix="/api/admin/ediscovery")

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> dict[str, str]:
    """Checks DB connectivity. Call if /health is OK but login returns 504."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception as exc:
        logger.warning("readiness DB check failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"database_unreachable:{exc}",
        ) from exc
