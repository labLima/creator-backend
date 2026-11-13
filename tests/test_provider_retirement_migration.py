"""T16 (issue #164): the provider cache tables are retired by ADR-031.

`provider_customers` and `provider_subscriptions` are the only two tables the
metadata carries without a target in ``Creator_DB_final.sql``. ADR-031 retires
them: the final modeling keeps ``provider_webhook_events``,
``provider_idempotency_keys`` and ``provider_disputes`` (the provider-facing
fact tables) but has no table for a provider-side customer or subscription
cache, and the modern code paths read the provider identifier from
``billing_accounts.external_id``/``external_code`` and
``subscriptions.external_id``/``external_code``.

These tests build a database from the committed previous schema
(``tests/contracts/schema_prev_ddl.sql``), stamp the historical revision, upgrade
to ``0036_storage_objects`` -- the head before T16 -- and seed one provider
customer and one provider subscription so the data loss of the retirement is
observable instead of assumed. Only then does the revision under test run,
exactly like a real database.

The retirement is a *contract* step (ADR-030, decision 3): the downgrade recreates
the previous shape empty. Data comes back from a backup, never from the
downgrade, and this module asserts that the recreations are empty so the
documented data loss cannot silently turn into a "restored" one.
"""

from __future__ import annotations

import contextlib
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from creator.infrastructure.database import metadata as _models  # noqa: F401  (registers tables)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREV_SCHEMA = PROJECT_ROOT / "tests" / "contracts" / "schema_prev_ddl.sql"
PREV_REVISION = "0005_content_text_versions"
# Head of the chain before T16; the revision under test must sit directly on it.
PRE_T16_REVISION = "0036_storage_objects"

CUSTOMERS = "provider_customers"
SUBSCRIPTIONS = "provider_subscriptions"
RETIRED_TABLES = (CUSTOMERS, SUBSCRIPTIONS)

# Shape of both tables at `0036_storage_objects`, read from the migrated schema.
# The downgrade has to recreate exactly this: same columns, in the same order,
# with the same nullability, defaults and primary key, and the same foreign key.
# Types are compared upper-cased because SQLite preserves the declared spelling
# but not its case.
CUSTOMERS_COLUMNS = [
    ("billing_account_id", "CHAR(32)", 1, None, 0),
    ("provider", "VARCHAR(20)", 1, None, 0),
    ("provider_customer_id", "VARCHAR(64)", 1, None, 0),
    ("provider_code", "VARCHAR(52)", 0, None, 0),
    ("metadata", "JSON", 1, "'{}'", 0),
    ("id", "CHAR(32)", 1, None, 1),
    ("created_at", "DATETIME", 1, "CURRENT_TIMESTAMP", 0),
    ("updated_at", "DATETIME", 1, "CURRENT_TIMESTAMP", 0),
    ("deleted_at", "DATETIME", 0, None, 0),
]
SUBSCRIPTIONS_COLUMNS = [
    ("subscription_id", "CHAR(32)", 1, None, 0),
    ("provider", "VARCHAR(20)", 1, None, 0),
    ("provider_subscription_id", "VARCHAR(64)", 1, None, 0),
    ("provider_status", "VARCHAR(20)", 0, None, 0),
    ("payload", "JSON", 1, "'{}'", 0),
    ("id", "CHAR(32)", 1, None, 1),
    ("created_at", "DATETIME", 1, "CURRENT_TIMESTAMP", 0),
    ("updated_at", "DATETIME", 1, "CURRENT_TIMESTAMP", 0),
    ("deleted_at", "DATETIME", 0, None, 0),
]
PREVIOUS_COLUMNS = {CUSTOMERS: CUSTOMERS_COLUMNS, SUBSCRIPTIONS: SUBSCRIPTIONS_COLUMNS}
PREVIOUS_FOREIGN_KEYS = {
    CUSTOMERS: [("billing_accounts", ["billing_account_id"], ["id"], "NO ACTION")],
    SUBSCRIPTIONS: [("subscriptions", ["subscription_id"], ["id"], "NO ACTION")],
}


# --- historical database setup ----------------------------------------------


def _config(database: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database.as_posix()}")
    return config


def _upgrade(database: Path, revision: str) -> None:
    command.upgrade(_config(database), revision)


def _downgrade(database: Path, revision: str) -> None:
    command.downgrade(_config(database), revision)


def _prepare(database: Path) -> None:
    """Create the committed previous schema and stamp it at its revision."""
    statements = [
        statement.strip()
        for statement in PREV_SCHEMA.read_text(encoding="utf-8").split("\n\n")
        if statement.strip()
    ]
    engine = sa.create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
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


@pytest.fixture(scope="module")
def pre_t16_database() -> Iterator[Path]:
    """Schema at ``0036_storage_objects``, built once and copied per test.

    Upgrading 31 revisions per test would dominate the suite; the chain is
    deterministic, so a private copy per test is enough to isolate the rows.
    """
    directory = Path(tempfile.mkdtemp(prefix=".creator-pytest-t16-", dir=Path.cwd()))
    try:
        database = directory / "pre_t16.db"
        _prepare(database)
        _upgrade(database, PRE_T16_REVISION)
        yield database
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def database(pre_t16_database: Path, tmp_path: Path) -> Path:
    """Private copy so each test owns its rows."""
    target = tmp_path / "provider_retirement.db"
    shutil.copy2(pre_t16_database, target)
    return target


@contextlib.contextmanager
def _connect(database: Path) -> Iterator[sa.Connection]:
    engine = sa.create_engine(f"sqlite+pysqlite:///{database.as_posix()}")
    try:
        with engine.begin() as connection:
            yield connection
    finally:
        engine.dispose()


# --- PRAGMA readers ---------------------------------------------------------


def _table_names(connection: sa.Connection) -> set[str]:
    rows = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _columns(connection: sa.Connection, table: str) -> list[tuple[Any, ...]]:
    """Columns as `(name, type, notnull, default, pk)`, case-normalized type."""
    return [
        (row[1], str(row[2]).upper(), row[3], row[4], row[5])
        for row in connection.exec_driver_sql(f'PRAGMA table_info("{table}")').fetchall()
    ]


def _foreign_keys(connection: sa.Connection, table: str) -> list[tuple[Any, ...]]:
    """Group `PRAGMA foreign_key_list` by constraint, keeping composite columns."""
    grouped: dict[int, dict[str, Any]] = {}
    for row in connection.exec_driver_sql(f'PRAGMA foreign_key_list("{table}")').fetchall():
        entry = grouped.setdefault(
            row[0], {"table": row[2], "columns": [], "targets": [], "on_delete": row[6]}
        )
        entry["columns"].append(row[3])
        entry["targets"].append(row[4])
    return [
        (entry["table"], entry["columns"], entry["targets"], entry["on_delete"])
        for entry in grouped.values()
    ]


def _named_indexes(connection: sa.Connection, table: str) -> dict[str, list[str]]:
    """Explicitly named indexes, excluding SQLite's `sqlite_autoindex_*` ones."""
    indexes: dict[str, list[str]] = {}
    for row in connection.exec_driver_sql(f'PRAGMA index_list("{table}")').fetchall():
        name = str(row[1])
        if name.startswith("sqlite_autoindex_"):
            continue
        indexes[name] = [
            str(info[2])
            for info in connection.exec_driver_sql(f'PRAGMA index_info("{name}")').fetchall()
        ]
    return indexes


def _revision(connection: sa.Connection) -> str:
    return str(connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one())


def _count(connection: sa.Connection, table: str) -> int:
    return int(connection.execute(sa.text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one())


# --- row seeds --------------------------------------------------------------


def _seed_provider_rows(connection: sa.Connection) -> dict[str, str]:
    """One provider customer and one provider subscription, with real parents."""
    ids = {
        "user": uuid4().hex,
        "workspace": uuid4().hex,
        "account": uuid4().hex,
        "plan": uuid4().hex,
        "subscription": uuid4().hex,
        "customer": uuid4().hex,
        "provider_subscription": uuid4().hex,
    }
    connection.execute(
        sa.text("INSERT INTO users (id, email, display_name) VALUES (:id, :email, :name)"),
        {"id": ids["user"], "email": f"{ids['user']}@example.com", "name": "T16 Retirement"},
    )
    connection.execute(
        sa.text("INSERT INTO workspaces (id, name) VALUES (:id, :name)"),
        {"id": ids["workspace"], "name": "T16 Workspace"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO billing_accounts (id, user_id, payer_type, name, email) "
            "VALUES (:id, :user, 'INDIVIDUAL', 'T16', :email)"
        ),
        {"id": ids["account"], "user": ids["user"], "email": f"{ids['account']}@example.com"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO plans (id, name, type, price_cents, credits_per_month) "
            "VALUES (:id, 'T16 Plan', 'BASIC', 1000, 10)"
        ),
        {"id": ids["plan"]},
    )
    connection.execute(
        sa.text(
            "INSERT INTO subscriptions (id, billing_account_id, workspace_id, plan_id, "
            "contracted_price_cents, status) "
            "VALUES (:id, :account, :workspace, :plan, 1000, 'ACTIVE')"
        ),
        {
            "id": ids["subscription"],
            "account": ids["account"],
            "workspace": ids["workspace"],
            "plan": ids["plan"],
        },
    )
    connection.execute(
        sa.text(
            "INSERT INTO provider_customers (id, billing_account_id, provider, "
            "provider_customer_id, provider_code) "
            "VALUES (:id, :account, 'PAGARME', 'cus_retired', 'retired')"
        ),
        {"id": ids["customer"], "account": ids["account"]},
    )
    connection.execute(
        sa.text(
            "INSERT INTO provider_subscriptions (id, subscription_id, provider, "
            "provider_subscription_id, provider_status) "
            "VALUES (:id, :subscription, 'PAGARME', 'sub_retired', 'ACTIVE')"
        ),
        {"id": ids["provider_subscription"], "subscription": ids["subscription"]},
    )
    return ids


# --- 1. the upgrade retires both tables -------------------------------------


def test_previous_head_really_carries_both_provider_tables(database: Path) -> None:
    """The fixture must start where T16 starts, not where the metadata is today.

    Without this guard a failure of the retirement assertions could be explained
    by a fixture that never created the tables in the first place.
    """
    with _connect(database) as connection:
        tables = _table_names(connection)
        assert _revision(connection) == PRE_T16_REVISION, (
            f"the fixture must be stamped at the pre-T16 head, got {_revision(connection)!r}"
        )
        for table in RETIRED_TABLES:
            assert table in tables, (
                f"{table} is absent from {PRE_T16_REVISION}; this test cannot observe the "
                f"retirement. Tables: {sorted(tables)}"
            )
            assert _columns(connection, table) == PREVIOUS_COLUMNS[table], (
                f"{table} does not have the shape T16 removes; the downgrade expectations "
                "of this module are stale"
            )


def test_upgrade_to_head_drops_the_provider_customer_and_subscription_tables(
    database: Path,
) -> None:
    """ADR-031 removes both tables: the final modeling has no target for them."""
    with _connect(database) as connection:
        ids = _seed_provider_rows(connection)
        before = _table_names(connection)
        assert _count(connection, CUSTOMERS) == 1, "the seeded provider customer is missing"
        assert _count(connection, SUBSCRIPTIONS) == 1, "the seeded provider subscription is missing"

    _upgrade(database, "head")

    with _connect(database) as connection:
        after = _table_names(connection)

        still_there = sorted(set(RETIRED_TABLES) & after)
        assert not still_there, (
            f"{still_there} survived the upgrade; ADR-031 retires both provider cache "
            f"tables because the final modeling has no target for them. Flagged rows: "
            f"customer={ids['customer']}, subscription={ids['provider_subscription']}"
        )
        assert after == before - set(RETIRED_TABLES), (
            "the retirement must drop exactly the two provider cache tables and nothing "
            f"else; dropped: {sorted(before - after)}, added: {sorted(after - before)}"
        )
        assert _revision(connection) != PRE_T16_REVISION, (
            "the database is still stamped at the pre-T16 head, so no retirement revision "
            "ran and this test would pass vacuously"
        )


def test_upgrade_leaves_the_database_reference_clean(database: Path) -> None:
    """Dropping a table must not orphan the rows that pointed at it.

    No other table declares a foreign key to the two provider caches, so the
    expectation is an empty ``PRAGMA foreign_key_check``: a surviving reference
    would mean the retirement left a half-dropped graph behind.
    """
    with _connect(database) as connection:
        _seed_provider_rows(connection)

    _upgrade(database, "head")

    with _connect(database) as connection:
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        assert violations == [], (
            "the upgraded database has dangling foreign keys (table, rowid, parent, fkid): "
            f"{violations}"
        )


# --- 2. the downgrade recreates the previous shape, empty -------------------


def test_downgrade_recreates_both_tables_with_the_previous_columns(database: Path) -> None:
    with _connect(database) as connection:
        _seed_provider_rows(connection)

    _upgrade(database, "head")

    with _connect(database) as connection:
        assert not set(RETIRED_TABLES) & _table_names(connection), (
            "the downgrade test assumes the upgrade removed the provider cache tables"
        )

    _downgrade(database, PRE_T16_REVISION)

    with _connect(database) as connection:
        assert _revision(connection) == PRE_T16_REVISION, (
            f"the downgrade must return the database to {PRE_T16_REVISION}, got "
            f"{_revision(connection)!r}"
        )
        tables = _table_names(connection)
        for table in RETIRED_TABLES:
            assert table in tables, (
                f"{table} was not recreated by the downgrade; tables: {sorted(tables)}"
            )
            assert _columns(connection, table) == PREVIOUS_COLUMNS[table], (
                f"the recreated {table} does not match the shape T16 removed; expected "
                f"{PREVIOUS_COLUMNS[table]}, got {_columns(connection, table)}"
            )


def test_downgrade_restores_the_previous_foreign_keys_and_primary_key(database: Path) -> None:
    _upgrade(database, "head")

    with _connect(database) as connection:
        assert not set(RETIRED_TABLES) & _table_names(connection), (
            "the downgrade test assumes the upgrade removed the provider cache tables"
        )

    _downgrade(database, PRE_T16_REVISION)

    with _connect(database) as connection:
        for table in RETIRED_TABLES:
            assert _foreign_keys(connection, table) == PREVIOUS_FOREIGN_KEYS[table], (
                f"the recreated {table} does not declare the previous foreign key; expected "
                f"{PREVIOUS_FOREIGN_KEYS[table]}, got {_foreign_keys(connection, table)}"
            )
            primary_key = [column for column in _columns(connection, table) if column[4]]
            assert [column[0] for column in primary_key] == ["id"], (
                f"the recreated {table} must keep `id` as its primary key, got "
                f"{[column[0] for column in primary_key]}"
            )
            assert _named_indexes(connection, table) == {}, (
                f"the recreated {table} invented indexes the retired table did not have: "
                f"{_named_indexes(connection, table)}"
            )


def test_downgrade_does_not_restore_the_retired_rows(database: Path) -> None:
    """Data loss is documented, not hidden: the downgrade is structure-only."""
    with _connect(database) as connection:
        _seed_provider_rows(connection)
        customer_rows = _count(connection, CUSTOMERS)
    assert customer_rows == 1, "the seeded provider customer must exist before the upgrade"

    _upgrade(database, "head")
    with _connect(database) as connection:
        assert not set(RETIRED_TABLES) & _table_names(connection), (
            "the downgrade test assumes the upgrade removed the provider cache tables"
        )
    _downgrade(database, PRE_T16_REVISION)

    with _connect(database) as connection:
        for table in RETIRED_TABLES:
            assert _count(connection, table) == 0, (
                f"{table} has rows after the round trip; the retirement downgrade is "
                "structure-only, so the dropped rows must not come back"
            )
