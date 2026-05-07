"""Add bimi_vmc_url to domains.

Revision ID: 0005_domain_bimi_vmc_url
Revises: 0004_emails_id_default
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_domain_bimi_vmc_url"
down_revision = "0004_emails_id_default"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("domains"):
        return
    cols = {c["name"] for c in inspector.get_columns("domains")}
    if "bimi_vmc_url" not in cols:
        op.add_column("domains", sa.Column("bimi_vmc_url", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("domains"):
        return
    cols = {c["name"] for c in inspector.get_columns("domains")}
    if "bimi_vmc_url" in cols:
        op.drop_column("domains", "bimi_vmc_url")
