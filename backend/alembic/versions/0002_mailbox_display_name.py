"""Add mailboxes.display_name for mailbox owner display name.

Revision ID: 0002_mailbox_display_name
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_mailbox_display_name"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("mailboxes")}
    if "display_name" not in cols:
        op.add_column("mailboxes", sa.Column("display_name", sa.String(200), nullable=True))

def downgrade() -> None:
    op.drop_column("mailboxes", "display_name")
