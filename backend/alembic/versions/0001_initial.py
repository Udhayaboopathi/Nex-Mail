"""Initial schema — creates all tables via SQLAlchemy metadata.

Revision: 0001_initial
"""
from alembic import op

# Import Base and all mapped models so metadata is fully populated before
# create_all is called.  The noqa comments silence "imported but unused" warnings.
from backend.models.base import Base  # noqa: F401
from backend import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure the pgcrypto extension exists (used for gen_random_uuid() fallback).
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # op.get_bind() returns the live synchronous Connection provided by env.py.
    # Passing it positionally to create_all() satisfies SQLAlchemy 2.0's
    # requirement that bind is a Connection or Engine (not a keyword-only arg).
    conn = op.get_bind()
    Base.metadata.create_all(conn)


def downgrade() -> None:
    conn = op.get_bind()
    Base.metadata.drop_all(conn)
