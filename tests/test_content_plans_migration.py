"""Prove migration 0012 actually runs and survives a downgrade (T9).

The slice tests use ``create_all``; this one builds the 0005 schema, seeds a
legacy ``planning`` row and upgrades through the migrations, so the DDL executed
is the one in ``migrations/versions/0012_content_plans.py``.
"""

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


def _prepare(path: Path) -> None:
    statements = [
        statement.strip()
        for statement in PREV_SCHEMA.read_text(encoding="utf-8").split("\n\n")
        if statement.strip()
    ]
    engine = sa.create_engine(f"sqlite+pysqlite:///{path}")
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
    engine.dispose()


def test_migration_creates_the_planning_tables_and_keeps_the_legacy_one(
    tmp_path: Path,
) -> None:
    database = tmp_path / "plans.db"
    _prepare(database)

    # A legacy planning row must survive the expand step.
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO planning (id, brand_id, campaign_id, persona_id, created_by) "
                "VALUES (:id, :brand, :campaign, :persona, :user)"
            ),
            {
                "id": uuid4().hex,
                "brand": uuid4().hex,
                "campaign": uuid4().hex,
                "persona": uuid4().hex,
                "user": uuid4().hex,
            },
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
        assert {"content_plans", "content_plan_items", "content_plan_special_dates"} <= created
        legacy = connection.execute(sa.text("SELECT COUNT(*) FROM planning")).scalar_one()
        assert legacy == 1
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []

    command.downgrade(config, "0011_brand_business_details")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.connect() as connection:
        remaining = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        legacy = connection.execute(sa.text("SELECT COUNT(*) FROM planning")).scalar_one()
    engine.dispose()
    assert not {"content_plans", "content_plan_items", "content_plan_special_dates"} & remaining
    assert legacy == 1
