"""Add allow_custom_dkim_signing to domains.

Revision ID: 0006_allow_custom_dkim_signing
Revises: 0005_domain_bimi_vmc_url
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_allow_custom_dkim_signing"
down_revision = "0005_domain_bimi_vmc_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("domains"):
        return
    cols = {c["name"] for c in inspector.get_columns("domains")}
    if "allow_custom_dkim_signing" not in cols:
        op.add_column(
            "domains",
            sa.Column("allow_custom_dkim_signing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("domains"):
        return
    cols = {c["name"] for c in inspector.get_columns("domains")}
    if "allow_custom_dkim_signing" in cols:
        op.drop_column("domains", "allow_custom_dkim_signing")
