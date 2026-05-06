from __future__ import annotations

from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "backend" / "models"
ALEMBIC = ROOT / "backend" / "alembic" / "versions" / "0001_initial.py"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")


MODEL_TEMPLATES: dict[str, str] = {
    "user.py": """
        from __future__ import annotations
        from sqlalchemy import Boolean, String, Text
        from sqlalchemy.orm import Mapped, mapped_column
        from backend.models.base import Base
        from backend.models.mixins import UUIDPrimaryKeyMixin, CreatedUpdatedMixin

        class User(Base, UUIDPrimaryKeyMixin, CreatedUpdatedMixin):
            __tablename__ = "users"
            email: Mapped[str] = mapped_column(String(319), unique=True, nullable=False)
            hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
            role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="user")
            is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    """,
    "domain.py": """
        from __future__ import annotations
        import uuid
        from datetime import datetime
        from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
        from sqlalchemy.dialects.postgresql import UUID
        from sqlalchemy.orm import Mapped, mapped_column
        from backend.models.base import Base
        from backend.models.mixins import UUIDPrimaryKeyMixin, CreatedAtMixin

        class Domain(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
            __tablename__ = "domains"
            name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
            is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
            is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
            suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
            suspended_reason: Mapped[str | None] = mapped_column(Text)
            storage_quota_gb: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
            used_storage_gb: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
            cloudflare_token_encrypted: Mapped[str | None] = mapped_column(Text)
            cloudflare_zone_id: Mapped[str | None] = mapped_column(String(64))
            cloudflare_auto_dns: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
            dns_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
            dns_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
            dkim_private_key_encrypted: Mapped[str | None] = mapped_column(Text)
            dkim_selector: Mapped[str] = mapped_column(String(63), nullable=False, server_default="mail")
            spf_record: Mapped[str | None] = mapped_column(Text)
            dmarc_record: Mapped[str | None] = mapped_column(Text)
            admin_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
            whitelabel_logo_url: Mapped[str | None] = mapped_column(Text)
            whitelabel_primary_color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#6366f1")
            whitelabel_company_name: Mapped[str | None] = mapped_column(String(100))
            retention_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
            ediscovery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    """,
}

SIMPLE_MODELS = [
    ("mailbox.py", "Mailbox", "mailboxes"),
    ("alias.py", "Alias", "aliases"),
    ("session.py", "Session", "sessions"),
    ("audit_log.py", "AuditLog", "audit_logs"),
    ("login_activity.py", "LoginActivity", "login_activity"),
    ("api_key.py", "ApiKey", "api_keys"),
    ("backup_job.py", "BackupJob", "backup_jobs"),
    ("domain_invite.py", "DomainInvite", "domain_invites"),
    ("password_reset_token.py", "PasswordResetToken", "password_reset_tokens"),
    ("totp_secret.py", "TotpSecret", "totp_secrets"),
    ("pgp_key.py", "PgpKey", "pgp_keys"),
    ("email_thread.py", "EmailThread", "email_threads"),
    ("label.py", "Label", "labels"),
    ("email_rule.py", "EmailRule", "email_rules"),
    ("email_template.py", "EmailTemplate", "email_templates"),
    ("read_receipt.py", "ReadReceipt", "read_receipts"),
    ("tracking_pixel.py", "TrackingPixel", "email_tracking_pixels"),
    ("link_click.py", "LinkClick", "email_link_clicks"),
    ("unsubscribe.py", "Unsubscribe", "unsubscribe_tokens"),
    ("webhook.py", "Webhook", "webhooks"),
    ("campaign.py", "Campaign", "campaign_emails"),
    ("autoresponder.py", "Autoresponder", "autoresponders"),
    ("scheduled_email.py", "ScheduledEmail", "scheduled_emails"),
    ("contact.py", "Contact", "contacts"),
    ("calendar_event.py", "CalendarEvent", "calendar_events"),
    ("task.py", "Task", "tasks"),
    ("note.py", "Note", "notes"),
    ("shared_mailbox.py", "SharedMailbox", "shared_mailboxes"),
    ("delegation.py", "Delegation", "mailbox_delegations"),
    ("spam_report.py", "SpamReport", "spam_reports"),
    ("ediscovery_export.py", "EdiscoveryExport", "ediscovery_exports"),
]


def render_simple(class_name: str, table_name: str) -> str:
    return f"""
from __future__ import annotations
from backend.models.base import Base
from backend.models.mixins import UUIDPrimaryKeyMixin, CreatedAtMixin

class {class_name}(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "{table_name}"
"""


MIGRATION = """
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(319), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("suspended_at", sa.DateTime(timezone=True)),
        sa.Column("suspended_reason", sa.Text()),
        sa.Column("storage_quota_gb", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("used_storage_gb", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cloudflare_token_encrypted", sa.Text()),
        sa.Column("cloudflare_zone_id", sa.String(64)),
        sa.Column("cloudflare_auto_dns", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dns_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dns_verified_at", sa.DateTime(timezone=True)),
        sa.Column("dkim_private_key_encrypted", sa.Text()),
        sa.Column("dkim_selector", sa.String(63), nullable=False, server_default="mail"),
        sa.Column("spf_record", sa.Text()),
        sa.Column("dmarc_record", sa.Text()),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("whitelabel_logo_url", sa.Text()),
        sa.Column("whitelabel_primary_color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("whitelabel_company_name", sa.String(100)),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ediscovery_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    table_names = [
        "domain_invites","mailboxes","aliases","sessions","audit_logs","login_activity","password_reset_tokens","totp_secrets","pgp_keys",
        "api_keys","backup_jobs","email_threads","labels","email_rules","email_templates","read_receipts","email_tracking_pixels","email_link_clicks",
        "unsubscribe_tokens","webhooks","campaign_emails","autoresponders","scheduled_emails","contacts","calendar_events","tasks","notes",
        "shared_mailboxes","mailbox_delegations","spam_reports","ediscovery_exports","autoresponder_sent","email_labels","unsubscribe_list","shared_mailbox_members"
    ]
    for name in table_names:
        cols = [sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()"))]
        if name not in {"email_labels","unsubscribe_list","shared_mailbox_members"}:
            cols.append(sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
        op.create_table(name, *cols)

def downgrade() -> None:
    for name in ["shared_mailbox_members","unsubscribe_list","email_labels","autoresponder_sent","ediscovery_exports","spam_reports","mailbox_delegations","shared_mailboxes","notes","tasks","calendar_events","contacts","scheduled_emails","autoresponders","campaign_emails","webhooks","unsubscribe_tokens","email_link_clicks","email_tracking_pixels","read_receipts","email_templates","email_rules","labels","email_threads","backup_jobs","api_keys","pgp_keys","totp_secrets","password_reset_tokens","login_activity","audit_logs","sessions","aliases","mailboxes","domain_invites","domains","users"]:
        op.drop_table(name)
"""


def main() -> None:
    for filename, content in MODEL_TEMPLATES.items():
        write(MODELS / filename, content)
    for filename, cls, table in SIMPLE_MODELS:
        write(MODELS / filename, render_simple(cls, table))
    write(ALEMBIC, MIGRATION)


if __name__ == "__main__":
    main()
