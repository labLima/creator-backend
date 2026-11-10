"""Contract test for the T13 drop of the four legacy redesign tables."""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREV_SCHEMA = PROJECT_ROOT / "tests" / "contracts" / "schema_prev_ddl.sql"
LEGACY = ("planning", "post_structure", "design_structure", "generated_image")


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
            "INSERT INTO alembic_version (version_num) VALUES (?)", ("0005_content_text_versions",)
        )
    engine.dispose()


def _config(path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    return config


def test_contract_drops_legacy_tables_and_downgrade_recreates_them_empty(
    tmp_path: Path,
) -> None:
    database = tmp_path / "contract.db"
    _prepare(database)
    config = _config(database)

    command.upgrade(config, "head")
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in LEGACY:
            assert table not in tables
    engine.dispose()

    command.downgrade(config, "0018_campaign_persona_alignment")
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in LEGACY:
            assert table in tables
            assert connection.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one() == 0
    engine.dispose()
