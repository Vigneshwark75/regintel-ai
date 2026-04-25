import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from regintel_infrastructure.db.base import Base, create_engine
from regintel_infrastructure.db.models import (  # noqa: F401 -- registers tables on Base.metadata
    ActionItemModel,
    ChunkModel,
    ComplianceQueryModel,
    DocumentModel,
    RegulationVersionModel,
)
from regintel_shared.asyncio_compat import ensure_windows_selector_event_loop
from regintel_shared.config import get_settings

ensure_windows_selector_event_loop()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_settings().postgres_dsn
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine: AsyncEngine = create_engine(get_settings().postgres_dsn)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
