"""Data-safety test for the B2 plan migration (0021)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREV_SCHEMA = PROJECT_ROOT / "tests" / "contracts" / "schema_prev_ddl.sql"


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
            "INSERT INTO alembic_version (version_num) VALUES (?)", ("0005_content_text_versions",)
        )
    engine.dispose()


def test_plan_rows_keep_code_and_description_in_metadata(tmp_path: Path) -> None:
    database = tmp_path / "plans.db"
    _prepare(database)
    config = _config(database)
    command.upgrade(config, "0020_billing_account_alignment")

    plan, item = uuid4(), uuid4()
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO plans (id, code, type, name, description, metadata, is_active) "
                "VALUES (:id, 'pro', 'PRO', 'Pro', 'Pro plan', '{}', 1)"
            ),
            {"id": plan.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO plan_items "
                "(id, plan_id, gateway_id, name, quantity, price_cents, status) "
                "VALUES (:id, :plan, 'gw_1', 'Item', 1, 990, 'ACTIVE')"
            ),
            {"id": item.hex, "plan": plan.hex},
        )
    engine.dispose()

    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT metadata, status FROM plans WHERE id = :id"), {"id": plan.hex}
        ).one()
        metadata = row[0]
        if isinstance(metadata, str):
            import json

            metadata = json.loads(metadata)
        assert metadata["code"] == "pro"
        assert metadata["description"] == "Pro plan"
        assert row[1] == "ACTIVE"
        item_row = connection.execute(
            sa.text("SELECT external_id, status, price_cents FROM plan_items WHERE id = :id"),
            {"id": item.hex},
        ).one()
        assert tuple(item_row) == ("gw_1", "ACTIVE", 990)
    engine.dispose()

    command.downgrade(config, "0020_billing_account_alignment")
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT code, description, is_active FROM plans WHERE id = :id"),
            {"id": plan.hex},
        ).one()
        assert tuple(row) == ("pro", "Pro plan", 1)
    engine.dispose()
