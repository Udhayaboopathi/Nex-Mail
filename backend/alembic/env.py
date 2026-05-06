"""
Alembic env.py — synchronous migrations via psycopg2.

The application uses asyncpg at runtime, but Alembic's migration runner
is synchronous.  We swap the driver suffix before handing the URL to
SQLAlchemy's synchronous engine_from_config so migrations work without
any async scaffolding.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.config import settings

# Import all models so Alembic's autogenerate sees the full schema.
from backend.models.base import Base  # noqa: F401
from backend import models  # noqa: F401  (registers all mapped classes)

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

# Replace asyncpg with psycopg2 for the sync migration engine.
_sync_url = (
    settings.database_url
    .replace("+asyncpg", "+psycopg2")
    .replace("postgresql+psycopg2", "postgresql+psycopg2")  # idempotent
)
# If the URL has no driver suffix at all, keep it as-is (defaults to psycopg2).
if "+asyncpg" not in settings.database_url and "postgresql://" in settings.database_url:
    _sync_url = settings.database_url  # plain postgresql:// → psycopg2

config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
