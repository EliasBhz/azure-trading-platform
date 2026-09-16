import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from trading_bot.persistence.database import normalise_dsn
from trading_bot.persistence.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """Read the DSN from the environment, never from alembic.ini.

    The file is committed; the credential is not. In Azure the value is injected
    from Key Vault through the container's managed identity.
    """
    dsn = os.environ.get("BOT_DATABASE_URL")
    if not dsn:
        raise RuntimeError("BOT_DATABASE_URL is not set")
    return normalise_dsn(dsn)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

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
