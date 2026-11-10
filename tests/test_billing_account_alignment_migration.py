"""Data-safety test for the B1 billing migration (0020)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREV_SCHEMA = PROJECT_ROOT / "tests" / "contracts" / "schema_prev_ddl.sql"


def _upgrade(path: Path, revision: str) -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    command.upgrade(config, revision)


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


def test_billing_rows_are_mapped_to_the_final_columns(tmp_path: Path) -> None:
    database = tmp_path / "billing.db"
    _prepare(database)
    _upgrade(database, "0019_legacy_contract")

    account, address, method = uuid4(), uuid4(), uuid4()
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO billing_accounts "
                "(id, user_id, payer_type, name, email, document, document_type, "
                "company_name, provider, provider_customer_id, provider_customer_code) "
                "VALUES (:id, :user, 'COMPANY', 'Acme', 'acme@example.com', "
                "'12345678000199', 'cnpj', 'Acme', 'PAGARME', 'cus_1', 'code_1')"
            ),
            {"id": account.hex, "user": uuid4().hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO billing_addresses "
                "(id, billing_account_id, street, number, complement, neighborhood, "
                "zip_code, city, state) "
                "VALUES (:id, :account, 'Rua A', '10', 'Sala 1', 'Centro', "
                "'50000000', 'Recife', 'PE')"
            ),
            {"id": address.hex, "account": account.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO billing_payment_methods "
                "(id, billing_account_id, provider_card_id, holder_name, card_brand, "
                "card_last_four, exp_month, exp_year, card_type, card_status) "
                "VALUES (:id, :account, 'card_1', 'Ana', 'visa', '4242', 12, 2030, "
                "'credit', 'active')"
            ),
            {"id": method.hex, "account": account.hex},
        )
    engine.dispose()

    _upgrade(database, "head")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        row = connection.execute(
            sa.text(
                "SELECT document, document_hash, external_id, external_code "
                "FROM billing_accounts WHERE id = :id"
            ),
            {"id": account.hex},
        ).one()
        assert bytes(row[0]) == b"12345678000199"
        assert row[1] == hashlib.sha256(b"12345678000199").hexdigest()
        assert (row[2], row[3]) == ("cus_1", "code_1")
        address_row = connection.execute(
            sa.text(
                "SELECT line_1, line_2, district, status FROM billing_addresses WHERE id = :id"
            ),
            {"id": address.hex},
        ).one()
        assert tuple(address_row) == ("Rua A", "Sala 1", "Centro", "ACTIVE")
        method_row = connection.execute(
            sa.text(
                "SELECT external_id, brand, type, status FROM billing_payment_methods "
                "WHERE id = :id"
            ),
            {"id": method.hex},
        ).one()
        assert tuple(method_row) == ("card_1", "VISA", "CREDIT", "ACTIVE")
    engine.dispose()
