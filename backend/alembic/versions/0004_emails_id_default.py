"""Ensure emails.id has gen_random_uuid() default.

Revision ID: 0004_emails_id_default
Revises: 0003_emails_table
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_emails_id_default"
down_revision = "0003_emails_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("emails"):
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("ALTER TABLE emails ALTER COLUMN id SET DEFAULT gen_random_uuid()")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("emails"):
        return
    op.execute("ALTER TABLE emails ALTER COLUMN id DROP DEFAULT")
