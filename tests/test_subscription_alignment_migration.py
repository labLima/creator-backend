"""Data-safety test for the B3 subscription migration (0022)."""

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


def test_subscription_and_history_are_mapped(tmp_path: Path) -> None:
    database = tmp_path / "subscriptions.db"
    _prepare(database)
    config = _config(database)
    command.upgrade(config, "0021_plan_alignment")

    plan, subscription, history = uuid4(), uuid4(), uuid4()
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO plans (id, name, type, provider, price_cents, currency, "
                "credits_per_month, status) VALUES (:id, 'Pro', 'PRO', 'PAGARME', "
                "9900, 'BRL', 10, 'ACTIVE')"
            ),
            {"id": plan.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO subscriptions "
                "(id, billing_account_id, workspace_id, plan_id, status, "
                "provider_subscription_id, provider_code, payment_method, interval, "
                "installments) VALUES (:id, :account, :workspace, :plan, 'active', "
                "'sub_1', 'code_1', 'credit_card', 'month', 2)"
            ),
            {
                "id": subscription.hex,
                "account": uuid4().hex,
                "workspace": uuid4().hex,
                "plan": plan.hex,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO subscription_history "
                "(id, subscription_id, change_type, previous_plan_id, plan_id, "
                "previous_status, status, reason) "
                "VALUES (:id, :subscription, 'upgrade', :plan, :plan, 'active', "
                "'trialing', 'CUSTOMER_REQUEST')"
            ),
            {"id": history.hex, "subscription": subscription.hex, "plan": plan.hex},
        )
    engine.dispose()

    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        row = connection.execute(
            sa.text(
                "SELECT external_id, status, contracted_price_cents, payment_method, "
                "billing_interval, installments FROM subscriptions WHERE id = :id"
            ),
            {"id": subscription.hex},
        ).one()
        assert tuple(row) == ("sub_1", "ACTIVE", 9900, "CREDIT_CARD", "MONTH", 2)
        history_row = connection.execute(
            sa.text(
                "SELECT change_type, old_plan_id, new_plan_id, old_status, new_status, "
                "reason_text FROM subscription_history WHERE id = :id"
            ),
            {"id": history.hex},
        ).one()
        assert tuple(history_row) == (
            "UPGRADE",
            plan.hex,
            plan.hex,
            "ACTIVE",
            "TRIALING",
            "CUSTOMER_REQUEST",
        )
    engine.dispose()
