"""Prove migration 0014 runs and keeps the legacy image table (T11)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
PREV_SCHEMA = CONTRACTS / "schema_prev_ddl.sql"
PREV_REVISION = "0005_content_text_versions"


def _config(path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    return config


def test_media_tables_come_from_the_migration(tmp_path: Path) -> None:
    database = tmp_path / "media.db"
    statements = [
        statement.strip()
        for statement in PREV_SCHEMA.read_text(encoding="utf-8").split("\n\n")
        if statement.strip()
    ]
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
        connection.exec_driver_sql(
            "CREATE TABLE alembic_version ("
            "version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        connection.exec_driver_sql(
            "INSERT INTO alembic_version (version_num) VALUES (?)", (PREV_REVISION,)
        )
        connection.execute(
            sa.text(
                "INSERT INTO generated_image "
                "(id, design_structure_id, workspace_id, image_status, resolution) "
                "VALUES (:id, :d, :w, 'pending', '1024x1024')"
            ),
            {"id": uuid4().hex, "d": uuid4().hex, "w": uuid4().hex},
        )
    engine.dispose()

    config = _config(database)
    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.connect() as connection:
        created = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"generated_images", "image_resizes"} <= created
        legacy = connection.execute(sa.text("SELECT COUNT(*) FROM generated_image")).scalar_one()
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert legacy == 1
    assert diff == []

    command.downgrade(config, "0013_posts_captions_designs")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.connect() as connection:
        remaining = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        legacy = connection.execute(sa.text("SELECT COUNT(*) FROM generated_image")).scalar_one()
    engine.dispose()
    assert not {"generated_images", "image_resizes"} & remaining
    assert legacy == 1
