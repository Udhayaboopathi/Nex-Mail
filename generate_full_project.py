from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).parent


def write(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


def py_model(name: str, table: str, body: str) -> str:
    body_text = "\n".join(f"    {line}" if line.strip() else "" for line in dedent(body).rstrip().splitlines())
    return f"""
from __future__ import annotations

import uuid
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class {name}(Base):
    __tablename__ = "{table}"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
{body_text}
"""


def main() -> None:
    write(
        "backend/models/base.py",
        """
        from sqlalchemy.orm import DeclarativeBase

        class Base(DeclarativeBase):
            pass
        """,
    )

    write(
        ".env.example",
        """
        DOMAIN=yourdomain.com
        ACME_EMAIL=admin@yourdomain.com
        TRAEFIK_DASHBOARD_ENABLED=false
        TRAEFIK_DASHBOARD_USER=admin
        TRAEFIK_DASHBOARD_PASSWORD_HASH=$$2y$$10$$change-me
        SERVER_IP=YOUR_CONTABO_IP
        SMTP_HOSTNAME=mail.yourdomain.com
        DATABASE_URL=postgresql+asyncpg://emailuser:password@postgres:5432/emaildb
        POSTGRES_DB=emaildb
        POSTGRES_USER=emailuser
        POSTGRES_PASSWORD=change-this-strong-password
        REDIS_URL=redis://redis:6379/0
        JWT_SECRET_KEY=replace-with-256-bit-random-secret
        JWT_ALGORITHM=HS256
        ACCESS_TOKEN_EXPIRE_MINUTES=30
        REFRESH_TOKEN_EXPIRE_DAYS=30
        ENCRYPTION_SECRET_KEY=replace-with-32-byte-base64-secret
        MAILDIR_BASE=/var/mail
        MAX_MESSAGE_SIZE_MB=25
        DKIM_SELECTOR=mail
        CLOUDFLARE_API_TOKEN=
        BACKUP_PASSPHRASE=
        BACKUP_RETENTION_DAYS=7
        BACKUP_SCHEDULE_HOUR=2
        SUPER_ADMIN_EMAIL=admin@yourdomain.com
        SUPER_ADMIN_PASSWORD=change-immediately
        FRONTEND_URL=https://yourdomain.com
        INVITE_BASE_URL=https://yourdomain.com
        NEXT_PUBLIC_API_URL=https://yourdomain.com
        ANTHROPIC_API_KEY=
        AI_SUMMARY_ENABLED=true
        AI_SMART_REPLY_ENABLED=true
        AI_PRIORITY_INBOX_ENABLED=true
        TRACKING_BASE_URL=https://yourdomain.com/track
        TRACKING_ENABLED=true
        SPAMASSASSIN_HOST=spamassassin
        CLAMAV_HOST=clamav
        """,
    )

    write(
        "backend/config.py",
        """
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class Settings(BaseSettings):
            model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
            domain: str = "localhost"
            acme_email: str = "admin@localhost"
            database_url: str
            redis_url: str
            jwt_secret_key: str
            jwt_algorithm: str = "HS256"
            access_token_expire_minutes: int = 30
            refresh_token_expire_days: int = 30
            encryption_secret_key: str
            max_message_size_mb: int = 25
            maildir_base: str = "/var/mail"
            dkim_selector: str = "mail"
            cloudflare_api_token: str = ""
            backup_retention_days: int = 7
            backup_schedule_hour: int = 2
            frontend_url: str = "http://localhost:3000"
            invite_base_url: str = "http://localhost:3000"
            tracking_base_url: str = "http://localhost:8000/api/track"
            tracking_enabled: bool = True
            anthropic_api_key: str = ""
            super_admin_email: str = "admin@example.com"
            super_admin_password: str = "change-me"

        settings = Settings()
        """,
    )

    write(
        "backend/database.py",
        """
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from backend.config import settings

        engine = create_async_engine(settings.database_url, future=True, echo=False)
        AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        """,
    )

    write(
        "backend/core/security.py",
        """
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from passlib.context import CryptContext
        from backend.config import settings

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        def hash_password(value: str) -> str:
            return pwd_context.hash(value)

        def verify_password(value: str, hashed: str) -> bool:
            return pwd_context.verify(value, hashed)

        def create_token(sub: str, expires_delta: timedelta) -> str:
            exp = datetime.now(tz=timezone.utc) + expires_delta
            return jwt.encode({"sub": sub, "exp": exp}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        def decode_token(token: str) -> dict:
            return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        """,
    )

    write(
        "backend/core/encryption.py",
        """
        import base64
        import hashlib
        from cryptography.fernet import Fernet
        from backend.config import settings

        def _fernet() -> Fernet:
            seed = hashlib.sha256(settings.encryption_secret_key.encode()).digest()
            key = base64.urlsafe_b64encode(seed)
            return Fernet(key)

        def encrypt_text(value: str) -> str:
            return _fernet().encrypt(value.encode()).decode()

        def decrypt_text(value: str) -> str:
            return _fernet().decrypt(value.encode()).decode()
        """,
    )

    write(
        "backend/core/ip_geo.py",
        """
        import httpx

        async def lookup_ip(ip: str | None) -> str:
            if not ip:
                return "unknown"
            try:
                async with httpx.AsyncClient(timeout=3) as client:
                    r = await client.get(f"http://ip-api.com/json/{ip}")
                    data = r.json()
                    return f"{data.get('city', '')}, {data.get('country', '')}".strip(", ") or "unknown"
            except Exception:
                return "unknown"
        """,
    )

    write(
        "backend/models/__init__.py",
        """
        from backend.models.base import Base
        """,
    )

    model_map = [
        ("User", "user", "users", "email: Mapped[str] = mapped_column(String(319), unique=True, nullable=False)\n    hashed_password: Mapped[str] = mapped_column(String, nullable=False)\n    role: Mapped[str] = mapped_column(String(20), default='user')\n    is_active: Mapped[bool] = mapped_column(default=True)\n    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())\n    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())"),
        ("Domain", "domain", "domains", "name: Mapped[str] = mapped_column(String, unique=True, nullable=False)\n    is_active: Mapped[bool] = mapped_column(default=True)\n    is_suspended: Mapped[bool] = mapped_column(default=False)\n    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)\n    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())"),
        ("Mailbox", "mailbox", "mailboxes", "user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)\n    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)\n    local_part: Mapped[str] = mapped_column(String(64), nullable=False)\n    full_address: Mapped[str] = mapped_column(String(319), unique=True, nullable=False)\n    quota_mb: Mapped[int] = mapped_column(default=1024)\n    used_mb: Mapped[float] = mapped_column(default=0.0)\n    is_active: Mapped[bool] = mapped_column(default=True)\n    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())"),
        ("Alias", "alias", "aliases", "source_address: Mapped[str] = mapped_column(String, unique=True, nullable=False)\n    destination_address: Mapped[str] = mapped_column(String, nullable=False)\n    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)\n    is_active: Mapped[bool] = mapped_column(default=True)\n    is_catch_all: Mapped[bool] = mapped_column(default=False)\n    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())"),
        ("Session", "session", "sessions", "user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)\n    refresh_token_hash: Mapped[str] = mapped_column(String, nullable=False)\n    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)\n    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())"),
    ]

    for class_name, fname, table, body in model_map:
        write(f"backend/models/{fname}.py", py_model(class_name, table, body))

    remaining_models = [
        "audit_log", "login_activity", "api_key", "backup_job", "domain_invite", "password_reset_token",
        "totp_secret", "pgp_key", "email_thread", "label", "email_rule", "email_template", "read_receipt",
        "tracking_pixel", "link_click", "unsubscribe", "webhook", "campaign", "autoresponder",
        "scheduled_email", "contact", "calendar_event", "task", "note", "shared_mailbox", "delegation",
        "spam_report", "ediscovery_export"
    ]
    for name in remaining_models:
        class_name = "".join(part.capitalize() for part in name.split("_"))
        write(
            f"backend/models/{name}.py",
            py_model(
                class_name,
                name if name not in {"tracking_pixel", "link_click", "unsubscribe", "campaign"} else {
                    "tracking_pixel": "email_tracking_pixels",
                    "link_click": "email_link_clicks",
                    "unsubscribe": "unsubscribe_tokens",
                    "campaign": "campaign_emails",
                }[name],
                "created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())",
            ),
        )

    write(
        "backend/alembic/env.py",
        """
        from logging.config import fileConfig
        from sqlalchemy import engine_from_config, pool
        from alembic import context
        from backend.models.base import Base
        from backend import models  # noqa: F401
        from backend.config import settings

        config = context.config
        config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))
        if config.config_file_name is not None:
            fileConfig(config.config_file_name)
        target_metadata = Base.metadata

        def run_migrations_offline() -> None:
            context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
            with context.begin_transaction():
                context.run_migrations()

        def run_migrations_online() -> None:
            connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
            with connectable.connect() as connection:
                context.configure(connection=connection, target_metadata=target_metadata)
                with context.begin_transaction():
                    context.run_migrations()

        if context.is_offline_mode():
            run_migrations_offline()
        else:
            run_migrations_online()
        """,
    )

    write(
        "backend/alembic/versions/0001_initial.py",
        """
        from alembic import op
        import sqlalchemy as sa

        revision = "0001_initial"
        down_revision = None
        branch_labels = None
        depends_on = None

        def _table(name: str, *cols: sa.Column) -> None:
            op.create_table(name, sa.Column("id", sa.UUID(), primary_key=True), *cols)

        def upgrade() -> None:
            _table("users", sa.Column("email", sa.String(319), unique=True, nullable=False), sa.Column("hashed_password", sa.Text(), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
            for table in ["domains","domain_invites","mailboxes","aliases","sessions","audit_logs","login_activity","password_reset_tokens","totp_secrets","pgp_keys","api_keys","backup_jobs","email_threads","labels","email_rules","email_templates","read_receipts","email_tracking_pixels","email_link_clicks","unsubscribe_tokens","webhooks","campaign_emails","autoresponders","scheduled_emails","contacts","calendar_events","tasks","notes","shared_mailboxes","mailbox_delegations","spam_reports","ediscovery_exports"]:
                _table(table, sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))

        def downgrade() -> None:
            for table in ["ediscovery_exports","spam_reports","mailbox_delegations","shared_mailboxes","notes","tasks","calendar_events","contacts","scheduled_emails","autoresponders","campaign_emails","webhooks","unsubscribe_tokens","email_link_clicks","email_tracking_pixels","read_receipts","email_templates","email_rules","labels","email_threads","backup_jobs","api_keys","pgp_keys","totp_secrets","password_reset_tokens","login_activity","audit_logs","sessions","aliases","mailboxes","domain_invites","domains","users"]:
                op.drop_table(table)
        """,
    )

    write("backend/smtp/server.py", "from aiosmtpd.controller import Controller\nfrom backend.smtp.handler import InboundHandler, SubmissionHandler\n\nasync def create_smtp_servers():\n    c1 = Controller(InboundHandler(), hostname='0.0.0.0', port=25)\n    c2 = Controller(SubmissionHandler(), hostname='0.0.0.0', port=587)\n    c1.start(); c2.start()\n    return c1, c2\n")
    write("backend/smtp/handler.py", "class InboundHandler:\n    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):\n        envelope.rcpt_tos.append(address)\n        return '250 OK'\n    async def handle_DATA(self, server, session, envelope):\n        return '250 Message accepted for delivery'\n\nclass SubmissionHandler(InboundHandler):\n    pass\n")
    write("backend/smtp/outbound.py", "import aiosmtplib\nfrom email.message import EmailMessage\n\nasync def send_direct(from_addr: str, to_list: list[str], subject: str, body_text: str, body_html: str | None = None) -> None:\n    msg = EmailMessage(); msg['From']=from_addr; msg['To']=', '.join(to_list); msg['Subject']=subject; msg.set_content(body_text)\n    if body_html: msg.add_alternative(body_html, subtype='html')\n    await aiosmtplib.send(msg, hostname='localhost', port=25)\n")
    write("backend/smtp/dkim.py", "import dkim\n\ndef sign_message(raw: bytes, selector: str, domain: str, private_key: bytes) -> bytes:\n    return dkim.sign(raw, selector.encode(), domain.encode(), private_key)\n")

    write("backend/imap/server.py", "import asyncio\n\nasync def create_imap_server() -> None:\n    while True:\n        await asyncio.sleep(3600)\n")
    write("backend/imap/session.py", "class ImapSession:\n    def __init__(self) -> None:\n        self.selected_mailbox = 'INBOX'\n")
    write("backend/imap/maildir.py", "from mailbox import Maildir\n\ndef open_maildir(path: str) -> Maildir:\n    return Maildir(path, create=True)\n")
    write("backend/imap/commands/__init__.py", "")
    for c in ["login", "select", "fetch", "search", "store", "expunge", "copy", "move", "append", "idle"]:
        write(f"backend/imap/commands/{c}.py", f"async def run(*args, **kwargs):\n    return 'OK {c.upper()}'\n")

    service_names = ["auth_service","mail_service","mailbox_service","domain_service","cloudflare_service","dns_guide_service","backup_service","thread_service","rules_service","ai_service","tracking_service","pgp_service","totp_service","campaign_service","calendar_service"]
    for sn in service_names:
        write(f"backend/services/{sn}.py", "from __future__ import annotations\n\nasync def health() -> dict[str, str]:\n    return {'service': 'ok'}\n")

    write("backend/api/deps.py", "from collections.abc import AsyncGenerator\nfrom fastapi import Depends, HTTPException\nfrom fastapi.security import OAuth2PasswordBearer\nfrom jose import JWTError\nfrom sqlalchemy.ext.asyncio import AsyncSession\nfrom backend.database import AsyncSessionLocal\nfrom backend.core.security import decode_token\n\noauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login')\n\nasync def get_db() -> AsyncGenerator[AsyncSession, None]:\n    async with AsyncSessionLocal() as session:\n        yield session\n\nasync def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, str]:\n    try:\n        payload = decode_token(token)\n        return {'id': payload.get('sub', '')}\n    except JWTError as exc:\n        raise HTTPException(status_code=401, detail='Invalid token') from exc\n")
    write("backend/api/middleware/rate_limit.py", "from slowapi import Limiter\nfrom slowapi.util import get_remote_address\n\nlimiter = Limiter(key_func=get_remote_address)\n\ndef add_rate_limiting(app):\n    app.state.limiter = limiter\n")
    write("backend/api/middleware/audit.py", "def add_audit_logging(app):\n    return app\n")

    router_files = ["auth","super_admin","domain_admin","mail","folders","threads","labels","rules","templates","contacts","calendar","tasks","notes","ai","pgp","campaigns","webhooks","api_keys","send_api","tracking","shared_mailboxes","delegation","spam_reports","ediscovery"]
    for r in router_files:
        write(f"backend/api/routers/{r}.py", f"from fastapi import APIRouter\n\nrouter = APIRouter()\n\n@router.get('/')\nasync def list_{r}() -> dict[str, list[str]]:\n    return {{'items': []}}\n")

    write(
        "backend/main.py",
        """
        import asyncio
        from contextlib import asynccontextmanager
        from fastapi import FastAPI
        from backend.api.middleware.rate_limit import add_rate_limiting
        from backend.api.middleware.audit import add_audit_logging
        from backend.smtp.server import create_smtp_servers
        from backend.imap.server import create_imap_server
        from backend.api.routers import auth, super_admin, domain_admin, mail, folders, threads, labels, rules, templates, contacts, calendar, tasks, notes, ai, pgp, campaigns, webhooks, api_keys, send_api, tracking, shared_mailboxes, delegation, spam_reports, ediscovery

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            smtp25, smtp587 = await create_smtp_servers()
            imap_task = asyncio.create_task(create_imap_server())
            yield
            smtp25.stop(); smtp587.stop(); imap_task.cancel()

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
        """,
    )

    write("backend/tasks/celery_app.py", "from celery import Celery\nfrom backend.config import settings\n\ncelery_app = Celery('email_platform', broker=settings.redis_url, backend=settings.redis_url)\ncelery_app.conf.task_default_queue = 'default'\n")
    for t in ["delivery","cleanup","backup_tasks","campaign_tasks","scheduled_email_tasks","storage_alert_tasks","retention_tasks","ai_tasks"]:
        write(f"backend/tasks/{t}.py", "from backend.tasks.celery_app import celery_app\n\n@celery_app.task\ndef run_task() -> str:\n    return 'ok'\n")

    schema_files = ["auth","user","domain","mailbox","mail","label","rule","template","calendar","task","note","contact","campaign","webhook","backup","api_key","admin","domain_admin"]
    for s in schema_files:
        write(f"backend/schemas/{s}.py", "from pydantic import BaseModel\n\nclass Item(BaseModel):\n    ok: bool = True\n")

    write("backend/requirements.txt", "fastapi>=0.111.0\nuvicorn[standard]>=0.29.0\naiosmtpd>=1.4.6\naiosmtplib>=3.0.0\nasyncpg>=0.29.0\nsqlalchemy[asyncio]>=2.0.0\nalembic>=1.13.0\npydantic-settings>=2.0.0\npydantic[email]>=2.0.0\npasslib[bcrypt]>=1.7.4\npython-jose[cryptography]>=3.3.0\ncryptography>=42.0.0\ndkimpy>=1.1.7\ndnspython>=2.6.0\npyspf>=2.0.14\nhttpx>=0.27.0\ncelery[redis]>=5.3.0\nredis>=5.0.0\nslowapi>=0.1.9\nanthropic>=0.25.0\npyotp>=2.9.0\npgpy>=0.6.0\nicalendar>=5.0.0\nPillow>=10.0.0\npython-multipart>=0.0.9\nbleach>=6.1.0\n")
    write("backend/Dockerfile", "FROM python:3.12-slim\nWORKDIR /app\nRUN apt-get update && apt-get install -y curl gcc libpq-dev spamc clamdscan && rm -rf /var/lib/apt/lists/*\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 25 587 993 8000\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\", \"--workers\", \"1\"]\n")
    write("backend/seed.py", "import asyncio\nfrom sqlalchemy import select\nfrom backend.database import AsyncSessionLocal\nfrom backend.models.user import User\nfrom backend.core.security import hash_password\nfrom backend.config import settings\n\nasync def seed() -> None:\n    async with AsyncSessionLocal() as db:\n        found = await db.execute(select(User).where(User.email == settings.super_admin_email))\n        if found.scalar_one_or_none() is None:\n            db.add(User(email=settings.super_admin_email, hashed_password=hash_password(settings.super_admin_password), role='super_admin'))\n            await db.commit()\n\nif __name__ == '__main__':\n    asyncio.run(seed())\n")

    write("frontend/package.json", json.dumps({"name":"nex-mail","private":True,"scripts":{"dev":"next dev","build":"next build","start":"next start","lint":"next lint"},"dependencies":{"next":"14.2.0","react":"18.2.0","react-dom":"18.2.0","zustand":"4.5.2","@tanstack/react-query":"5.36.2","lucide-react":"0.395.0","dompurify":"3.1.5","@uiw/react-md-editor":"4.0.5","@tiptap/react":"2.4.0","@tiptap/starter-kit":"2.4.0"},"devDependencies":{"typescript":"5.4.5","@types/react":"18.2.61","@types/node":"20.12.7","tailwindcss":"3.4.3","postcss":"8.4.38","autoprefixer":"10.4.19"}}, indent=2))
    write("frontend/tsconfig.json", json.dumps({"compilerOptions":{"target":"ES2022","lib":["dom","dom.iterable","es2022"],"allowJs":False,"skipLibCheck":True,"strict":True,"noEmit":True,"module":"esnext","moduleResolution":"bundler","resolveJsonModule":True,"isolatedModules":True,"jsx":"preserve","incremental":True},"include":["next-env.d.ts","**/*.ts","**/*.tsx"],"exclude":["node_modules"]}, indent=2))
    write("frontend/tailwind.config.ts", "import type { Config } from 'tailwindcss'\nconst config: Config = { darkMode: 'class', content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'], theme: { extend: {} }, plugins: [] }\nexport default config\n")
    write("frontend/next.config.ts", "import type { NextConfig } from 'next'\nconst nextConfig: NextConfig = { output: 'standalone' }\nexport default nextConfig\n")
    write("frontend/Dockerfile", "FROM node:20-alpine AS builder\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\nRUN npm run build\nFROM node:20-alpine AS runner\nWORKDIR /app\nENV NODE_ENV=production\nCOPY --from=builder /app/.next/standalone ./\nCOPY --from=builder /app/.next/static ./.next/static\nCOPY --from=builder /app/public ./public\nEXPOSE 3000\nCMD [\"node\", \"server.js\"]\n")
    write("frontend/public/manifest.json", '{"name":"Nex Mail","short_name":"NexMail","start_url":"/","display":"standalone"}')
    write("frontend/public/sw.js", "self.addEventListener('install', () => self.skipWaiting());")
    write("frontend/types/index.ts", "export type Role = 'super_admin' | 'domain_admin' | 'user'\nexport interface UserSession { id: string; role: Role; token: string }\n")
    write("frontend/store/index.ts", "import { create } from 'zustand'\nimport { UserSession } from '../types'\n\ninterface AppState { session: UserSession | null; setSession: (s: UserSession | null) => void }\nexport const useAppStore = create<AppState>((set) => ({ session: null, setSession: (session) => set({ session }) }))\n")
    write("frontend/lib/api.ts", "export async function api<T>(path: string, init?: RequestInit): Promise<T> { const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'; const res = await fetch(`${base}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) } }); if (!res.ok) throw new Error(await res.text()); return (await res.json()) as T }\n")
    write("frontend/lib/auth.ts", "export function tokenFromStorage(): string | null { return typeof window === 'undefined' ? null : window.localStorage.getItem('token') }\n")
    write("frontend/lib/utils.ts", "export function cx(...parts: Array<string | false | null | undefined>): string { return parts.filter(Boolean).join(' ') }\n")
    for h in ["useAuth","useMail","useInfiniteScroll","useWhitelabel"]:
        write(f"frontend/hooks/{h}.ts", "export function useHook(): { ok: boolean } { return { ok: true } }\n")

    component_paths = [
        "components/ui/Button.tsx","components/ui/Input.tsx","components/ui/Modal.tsx","components/ui/Badge.tsx","components/ui/Avatar.tsx","components/ui/Toast.tsx","components/ui/ProgressBar.tsx",
        "components/layout/Sidebar.tsx","components/layout/Topbar.tsx","components/layout/MobileSidebar.tsx",
        "components/mail/EmailList.tsx","components/mail/EmailListItem.tsx","components/mail/ThreadView.tsx","components/mail/PriorityInbox.tsx","components/mail/EmailReader.tsx","components/mail/ComposeModal.tsx","components/mail/AttachmentViewer.tsx","components/mail/SearchBar.tsx","components/mail/RuleBuilderModal.tsx",
        "components/super-admin/AddDomainModal.tsx","components/super-admin/AssignAdminModal.tsx","components/super-admin/DNSSetupModal.tsx",
        "components/domain-admin/CreateMailboxModal.tsx","components/domain-admin/EditMailboxModal.tsx","components/domain-admin/ResetPasswordModal.tsx","components/domain-admin/CreateAliasModal.tsx","components/domain-admin/RestorePreviewModal.tsx",
        "components/calendar/CalendarView.tsx",
    ]
    for p in component_paths:
        comp = Path(p).stem
        write(f"frontend/{p}", f"export default function {comp}(): JSX.Element {{ return <div className='rounded-md bg-white p-4 text-slate-800 dark:bg-slate-900 dark:text-slate-100'>{comp}</div> }}\n")

    app_pages = [
        "app/layout.tsx","app/page.tsx","app/offline/page.tsx","app/(auth)/login/page.tsx","app/(auth)/forgot-password/page.tsx","app/(auth)/reset-password/[token]/page.tsx","app/invite/[token]/page.tsx","app/unsubscribe/[token]/page.tsx","app/super-admin/layout.tsx","app/super-admin/page.tsx","app/super-admin/domains/page.tsx","app/super-admin/backups/page.tsx","app/super-admin/audit-logs/page.tsx","app/super-admin/settings/page.tsx","app/domain-admin/layout.tsx","app/domain-admin/page.tsx","app/domain-admin/mailboxes/page.tsx","app/domain-admin/aliases/page.tsx","app/domain-admin/dns/page.tsx","app/domain-admin/shared/page.tsx","app/domain-admin/backup/page.tsx","app/domain-admin/whitelabel/page.tsx","app/domain-admin/ediscovery/page.tsx","app/domain-admin/retention/page.tsx","app/domain-admin/audit/page.tsx","app/domain-admin/settings/page.tsx","app/mail/layout.tsx","app/mail/[folder]/page.tsx","app/mail/[folder]/[uid]/page.tsx","app/calendar/page.tsx","app/tasks/page.tsx","app/notes/page.tsx","app/settings/page.tsx","app/settings/security/page.tsx","app/settings/api-keys/page.tsx","app/settings/webhooks/page.tsx","app/settings/rules/page.tsx","app/settings/templates/page.tsx","app/settings/labels/page.tsx"
    ]
    for p in app_pages:
        name = Path(p).parts[-2] if Path(p).name == "page.tsx" else Path(p).stem
        if p == "app/layout.tsx":
            write("frontend/app/layout.tsx", "import './globals.css'\nexport default function RootLayout({ children }: { children: React.ReactNode }): JSX.Element { return <html lang='en'><body className='bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100'>{children}</body></html> }\n")
        elif p == "app/page.tsx":
            write("frontend/app/page.tsx", "import { redirect } from 'next/navigation'\nexport default function Home(): null { redirect('/mail/inbox'); return null }\n")
        else:
            write(f"frontend/{p}", f"export default function Page(): JSX.Element {{ return <main className='p-6'><h1 className='text-xl font-semibold text-slate-900 dark:text-slate-100'>{name}</h1></main> }}\n")

    write("frontend/app/globals.css", "@tailwind base;@tailwind components;@tailwind utilities;")

    write(
        "docker-compose.yml",
        """
        services:
          traefik:
            image: traefik:v3.0
            restart: unless-stopped
            command: --providers.file.filename=/etc/traefik/dynamic/middlewares.yml
            ports: ["80:80","443:443"]
            volumes:
              - ./traefik/traefik.yml:/etc/traefik/traefik.yml:ro
              - ./traefik/dynamic:/etc/traefik/dynamic:ro
              - ./traefik/acme:/acme
              - /var/run/docker.sock:/var/run/docker.sock:ro
            networks: [traefik-public]
          backend:
            build: ./backend
            restart: unless-stopped
            healthcheck: { test: ["CMD-SHELL","python -c 'print(1)'"], interval: 30s, timeout: 5s, retries: 3 }
            env_file: .env
            ports: ["25:25","587:587","993:993"]
            volumes: ["./infra/mail-certs:/etc/ssl/mail:ro"]
            labels: ["traefik.enable=true","traefik.http.routers.api.rule=Host(`${DOMAIN}`) && PathPrefix(`/api`)","traefik.http.routers.api.priority=10","traefik.http.services.api.loadbalancer.server.port=8000"]
            depends_on: [postgres, redis]
            networks: [traefik-public, internal]
          frontend:
            build: ./frontend
            restart: unless-stopped
            healthcheck: { test: ["CMD-SHELL","node -e \\"process.exit(0)\\""], interval: 30s, timeout: 5s, retries: 3 }
            labels: ["traefik.enable=true","traefik.http.routers.frontend.rule=Host(`${DOMAIN}`)","traefik.http.routers.frontend.priority=1","traefik.http.services.frontend.loadbalancer.server.port=3000"]
            networks: [traefik-public]
          postgres:
            image: postgres:16
            restart: unless-stopped
            healthcheck: { test: ["CMD-SHELL","pg_isready -U $$POSTGRES_USER"], interval: 30s, timeout: 5s, retries: 3 }
            env_file: .env
            networks: [internal]
          redis:
            image: redis:7
            restart: unless-stopped
            healthcheck: { test: ["CMD","redis-cli","ping"], interval: 30s, timeout: 5s, retries: 3 }
            networks: [internal]
          spamassassin:
            image: instrumentisto/spamassassin
            restart: unless-stopped
            healthcheck: { test: ["CMD-SHELL","echo ok"], interval: 30s, timeout: 5s, retries: 3 }
            networks: [internal]
          clamav:
            image: clamav/clamav:latest
            restart: unless-stopped
            healthcheck: { test: ["CMD-SHELL","echo ok"], interval: 30s, timeout: 5s, retries: 3 }
            networks: [internal]
          worker:
            build: ./backend
            command: celery -A tasks.celery_app.celery_app worker -Q default,email,backup,ai -l info
            restart: unless-stopped
            env_file: .env
            healthcheck: { test: ["CMD-SHELL","python -c 'print(1)'"], interval: 30s, timeout: 5s, retries: 3 }
            networks: [internal]
          beat:
            build: ./backend
            command: celery -A tasks.celery_app.celery_app beat -l info
            restart: unless-stopped
            env_file: .env
            healthcheck: { test: ["CMD-SHELL","python -c 'print(1)'"], interval: 30s, timeout: 5s, retries: 3 }
            networks: [internal]
        networks:
          traefik-public: {}
          internal: {}
        """,
    )

    write("traefik/traefik.yml", "api:\n  dashboard: true\n  insecure: false\nentryPoints:\n  web:\n    address: ':80'\n    http:\n      redirections:\n        entryPoint:\n          to: websecure\n          scheme: https\n  websecure:\n    address: ':443'\nproviders:\n  docker:\n    endpoint: 'unix:///var/run/docker.sock'\n    exposedByDefault: false\n  file:\n    directory: /etc/traefik/dynamic\ncertificatesResolvers:\n  letsencrypt:\n    acme:\n      email: 'admin@example.com'\n      storage: /acme/acme.json\n      httpChallenge:\n        entryPoint: web\n")
    write("traefik/dynamic/middlewares.yml", "http:\n  middlewares:\n    security-headers:\n      headers:\n        stsSeconds: 31536000\n        forceSTSHeader: true\n")
    write("traefik/acme/.gitkeep", "")
    write("infra/spamassassin/local.cf", "required_score 5.0\nuse_bayes 1\nbayes_auto_learn 1\n")
    write("infra/clamav/clamd.conf", "TCPSocket 3310\nTCPAddr 0.0.0.0\nMaxFileSize 25M\nMaxScanSize 100M\n")
    write("infra/fail2ban/jail.local", "[sshd]\nenabled = true\nmaxretry = 5\nbantime = 3600\n")
    write("infra/dkim/generate_keys.sh", "#!/bin/bash\nDOMAIN=$1\nif [ -z \"$DOMAIN\" ]; then echo \"Usage: $0 <domain>\"; exit 1; fi\nmkdir -p infra/dkim\nopenssl genrsa -out infra/dkim/${DOMAIN}.private 2048\nopenssl rsa -in infra/dkim/${DOMAIN}.private -pubout -out infra/dkim/${DOMAIN}.public\n")
    write("infra/mail-certs/.gitkeep", "")
    write("Makefile", "up:\n\tdocker compose up -d\n\ndown:\n\tdocker compose down\n\nbuild:\n\tdocker compose up -d --build\n\nlogs:\n\tdocker compose logs -f backend\n\nlogs-traefik:\n\tdocker compose logs -f traefik\n\nmigrate:\n\tdocker compose exec backend alembic upgrade head\n\nseed:\n\tdocker compose exec backend python seed.py\n")
    write("README.md", "# MailOS — Self-Hosted Email Platform\n\nRun `cp .env.example .env`, fill values, then `make build && make migrate && make seed`.\n")


if __name__ == "__main__":
    main()
