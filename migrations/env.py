from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from creator.config import get_settings
from creator.infrastructure.database import metadata as models  # noqa: F401
from creator.infrastructure.database.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DEFAULT_ALEMBIC_DATABASE_URL = "sqlite+pysqlite:///./.local/db/creator.db"
configured_database_url = config.get_main_option("sqlalchemy.url")
if not configured_database_url or configured_database_url == DEFAULT_ALEMBIC_DATABASE_URL:
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Migrations rebuild tables (SQLite cannot ALTER constraints). With
        # foreign keys ON, DROP TABLE runs an implicit DELETE and cascades into
        # child rows; the rebuild would silently lose campaign/invite data.
        # Enforcement is restored on every application connection by
        # create_database_engine().
        if connection.dialect.name == "sqlite":
            # Run on the DBAPI connection: an ORM-level execute would open a
            # transaction and the PRAGMA would be a no-op inside it.
            driver_connection = connection.connection.driver_connection
            driver_connection.execute("PRAGMA foreign_keys=OFF")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
