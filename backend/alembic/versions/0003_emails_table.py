"""Add emails table for inbox/sent DB persistence.

Revision ID: 0003_emails_table
Revises: 0002_mailbox_display_name
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_emails_table"
down_revision = "0002_mailbox_display_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("emails"):
        return

    op.create_table(
        "emails",
        sa.Column("mailbox_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folder", sa.String(length=50), nullable=False, server_default="inbox"),
        sa.Column("from_address", sa.String(length=319), nullable=True),
        sa.Column("to_addresses", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("cc_addresses", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("bcc_addresses", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("flags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_attachments", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["mailbox_id"], ["mailboxes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emails_mailbox_folder_created", "emails", ["mailbox_id", "folder", "created_at"])
    op.create_index("ix_emails_message_id", "emails", ["message_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("emails"):
        return
    op.drop_index("ix_emails_message_id", table_name="emails")
    op.drop_index("ix_emails_mailbox_folder_created", table_name="emails")
    op.drop_table("emails")
