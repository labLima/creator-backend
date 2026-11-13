"""Data-safety tests for the T15 credit ledger alignment (issue #162).

The final modeling declares ``workspace_credit_transactions`` as an append-only
ledger with a dedicated column per correlation target and a cumulative
``balance_after``. The legacy table still carries the generic
``transaction_type``/``reference_type``/``reference_id`` triple plus
``updated_at``/``deleted_at``, and the parity report counts 31 divergences for
this one table (7 missing columns, 5 extra, 6 missing indexes, 2 index names,
5 missing FKs, 1 extra FK, 1 wrong ``ON DELETE`` and 4 unmapped CHECKs).

Each test builds a database from the committed previous schema
(``tests/contracts/schema_prev_ddl.sql``), stamps the historical revision,
upgrades to ``0034_billing_media_micro`` (the head before T15) and only then
writes the legacy rows the new revision has to migrate. The upgrade under test
runs afterwards, exactly like a real database, so a migration that silently
loses rows, forgets the backfill or resurrects a deleted row fails here.

Approved semantics (recorded in #162):

- ``balance_after`` is the cumulative ``SUM(amount)`` per workspace, ordered by
  ``created_at``; it is the ledger balance, not lot availability;
- ``type`` uses the ``credit_transaction_type`` vocabulary, with unknown legacy
  values mapped to ``ADJUSTMENT``;
- unknown ``reference_type`` and dangling references leave the dedicated
  column NULL;
- soft-deleted rows and rows with ``amount = 0`` are dropped by the backfill;
- a cumulative balance below zero aborts the migration.
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
from creator.infrastructure.database.db import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREV_SCHEMA = PROJECT_ROOT / "tests" / "contracts" / "schema_prev_ddl.sql"
PREV_REVISION = "0005_content_text_versions"
# Last revision of the chain before the credit ledger alignment.
LEGACY_REVISION = "0034_billing_media_micro"

TABLE = "workspace_credit_transactions"

# Columns the final modeling requires and the legacy table does not have.
ADDED_COLUMNS = (
    "balance_after",
    "type",
    "order_id",
    "invoice_id",
    "generated_image_id",
    "image_resize_id",
    "created_by",
)
# Columns the final modeling does not have; the contract drops all of them.
DROPPED_COLUMNS = (
    "transaction_type",
    "reference_type",
    "reference_id",
    "updated_at",
    "deleted_at",
)
FINAL_COLUMNS = (
    "id",
    "workspace_id",
    "amount",
    "balance_after",
    "type",
    "order_id",
    "invoice_id",
    "generated_image_id",
    "image_resize_id",
    "created_by",
    "created_at",
)
CREDIT_TRANSACTION_TYPES = (
    "SUBSCRIPTION_CREDIT",
    "TOP_UP",
    "COUPON_CREDIT",
    "GENERATION",
    "EXPIRATION",
    "REFUND",
    "ADJUSTMENT",
)


# --- historical database setup ----------------------------------------------


def _config(database: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database}")
    return config


def _upgrade(database: Path, revision: str) -> None:
    command.upgrade(_config(database), revision)


def _downgrade(database: Path, revision: str) -> None:
    command.downgrade(_config(database), revision)


def _prepare(database: Path) -> None:
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
    engine.dispose()


@pytest.fixture(scope="module")
def legacy_database() -> Iterator[Path]:
    """Schema at ``0034_billing_media_micro``, built once and copied per test."""
    directory = Path(tempfile.mkdtemp(prefix=".creator-pytest-credit-", dir=Path.cwd()))
    try:
        database = directory / "legacy.db"
        _prepare(database)
        _upgrade(database, LEGACY_REVISION)
        yield database
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def database(legacy_database: Path, tmp_path: Path) -> Path:
    """Private copy so each test owns its rows."""
    target = tmp_path / "credit_ledger.db"
    shutil.copy2(legacy_database, target)
    return target


@contextlib.contextmanager
def _connect(database: Path) -> Iterator[sa.Connection]:
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    try:
        with engine.begin() as connection:
            yield connection
    finally:
        engine.dispose()


# --- PRAGMA readers ---------------------------------------------------------


def _columns(connection: sa.Connection, table: str = TABLE) -> dict[str, dict[str, Any]]:
    rows = connection.exec_driver_sql(f'PRAGMA table_info("{table}")').fetchall()
    return {row[1]: {"type": row[2], "notnull": bool(row[3]), "default": row[4]} for row in rows}


def _indexes(connection: sa.Connection, table: str = TABLE) -> dict[str, dict[str, Any]]:
    indexes: dict[str, dict[str, Any]] = {}
    for row in connection.exec_driver_sql(f'PRAGMA index_list("{table}")').fetchall():
        name = row[1]
        columns = [
            info[2]
            for info in connection.exec_driver_sql(f'PRAGMA index_info("{name}")').fetchall()
        ]
        indexes[name] = {"unique": bool(row[2]), "columns": columns}
    return indexes


def _foreign_keys(connection: sa.Connection, table: str = TABLE) -> list[dict[str, Any]]:
    """Group ``PRAGMA foreign_key_list`` by constraint, keeping composite columns."""
    grouped: dict[int, dict[str, Any]] = {}
    rows = connection.exec_driver_sql(f'PRAGMA foreign_key_list("{table}")').fetchall()
    for row in rows:
        entry = grouped.setdefault(
            row[0],
            {"table": row[2], "columns": [], "targets": [], "on_delete": row[6]},
        )
        entry["columns"].append(row[3])
        entry["targets"].append(row[4])
    return list(grouped.values())


def _table_sql(connection: sa.Connection, table: str = TABLE) -> str:
    statement = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = :name", {"name": table}
    ).scalar_one()
    return str(statement)


def _default(value: Any) -> str:
    """SQLite keeps the literal in ``dflt_value``, quotes included."""
    return "" if value is None else str(value).strip().strip("'\"")


def _without_spaces(text: str) -> str:
    """Compare constraint SQL and messages without depending on spacing."""
    return "".join(text.split())


# --- row seeds --------------------------------------------------------------


def _insert_user(connection: sa.Connection, user_id: str) -> None:
    connection.execute(
        sa.text("INSERT INTO users (id, email, display_name) VALUES (:id, :email, :name)"),
        {"id": user_id, "email": f"{user_id}@example.com", "name": "Credit Ledger"},
    )


def _insert_workspace(connection: sa.Connection, workspace_id: str, name: str) -> None:
    connection.execute(
        sa.text("INSERT INTO workspaces (id, name) VALUES (:id, :name)"),
        {"id": workspace_id, "name": name},
    )


def _seed_graph(connection: sa.Connection) -> dict[str, str]:
    """Two workspaces plus the billing graph that makes ``order_id`` resolvable."""
    ids = {
        "user": uuid4().hex,
        "workspace": uuid4().hex,
        "other_workspace": uuid4().hex,
        "account": uuid4().hex,
        "order": uuid4().hex,
    }
    _insert_user(connection, ids["user"])
    _insert_workspace(connection, ids["workspace"], "Credit Ledger A")
    _insert_workspace(connection, ids["other_workspace"], "Credit Ledger B")
    connection.execute(
        sa.text(
            "INSERT INTO billing_accounts (id, user_id, payer_type, name, email) "
            "VALUES (:id, :user, 'INDIVIDUAL', 'Credit', :email)"
        ),
        {"id": ids["account"], "user": ids["user"], "email": f"{ids['account']}@example.com"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
            "amount_cents, status) VALUES (:id, :account, :workspace, 1000, 1000, 'PAID')"
        ),
        {"id": ids["order"], "account": ids["account"], "workspace": ids["workspace"]},
    )
    return ids


def _insert_legacy_transaction(
    connection: sa.Connection,
    *,
    workspace_id: str,
    amount: int,
    transaction_type: str,
    created_at: str,
    transaction_id: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    deleted_at: str | None = None,
) -> str:
    identifier = transaction_id or uuid4().hex
    connection.execute(
        sa.text(
            f"INSERT INTO {TABLE} "
            "(id, workspace_id, amount, transaction_type, reference_type, reference_id, "
            "created_at, deleted_at) "
            "VALUES (:id, :workspace, :amount, :type, :reference_type, :reference_id, "
            ":created_at, :deleted_at)"
        ),
        {
            "id": identifier,
            "workspace": workspace_id,
            "amount": amount,
            "type": transaction_type,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "created_at": created_at,
            "deleted_at": deleted_at,
        },
    )
    return identifier


def _insert_coupon(connection: sa.Connection, *, code: str) -> str:
    """One redeemable coupon, so several redemptions cannot collide on the UNIQUE.

    ``chk_coupons_type_exclusive_fields`` requires ``credits`` for the CREDIT type
    and forbids ``discount_percent``, so the seed has to satisfy it.
    """
    coupon_id = uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO coupons (id, code, type, credits, discount_percent) "
            "VALUES (:id, :code, 'CREDIT', 100, NULL)"
        ),
        {"id": coupon_id, "code": code},
    )
    return coupon_id


def _insert_redemption(
    connection: sa.Connection,
    *,
    user_id: str,
    workspace_id: str,
    order_id: str,
    credit_transaction_id: str,
    code: str,
) -> str:
    """A redemption of the seeded order, linked to one credit transaction.

    ``chk_coupon_redemptions_single_target`` requires exactly one of
    ``order_id``/``subscription_id``, so the order is mandatory.
    """
    coupon_id = _insert_coupon(connection, code=code)
    redemption_id = uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO coupon_redemptions "
            "(id, coupon_id, user_id, workspace_id, order_id, credit_transaction_id, status) "
            "VALUES (:id, :coupon, :user, :workspace, :order, :transaction, 'APPLIED')"
        ),
        {
            "id": redemption_id,
            "coupon": coupon_id,
            "user": user_id,
            "workspace": workspace_id,
            "order": order_id,
            "transaction": credit_transaction_id,
        },
    )
    return redemption_id


def _insert_lot(
    connection: sa.Connection,
    *,
    workspace_id: str,
    grant_transaction_id: str,
    original_amount: int,
    remaining_amount: int,
) -> str:
    lot_id = uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO workspace_credit_lots (id, workspace_id, grant_transaction_id, "
            "original_amount, remaining_amount) "
            "VALUES (:id, :workspace, :grant, :original, :remaining)"
        ),
        {
            "id": lot_id,
            "workspace": workspace_id,
            "grant": grant_transaction_id,
            "original": original_amount,
            "remaining": remaining_amount,
        },
    )
    return lot_id


def _insert_lot_consumption(
    connection: sa.Connection,
    *,
    workspace_id: str,
    lot_id: str,
    transaction_id: str,
    amount: int,
) -> str:
    consumption_id = uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO workspace_credit_lot_consumptions "
            "(id, workspace_id, lot_id, transaction_id, amount) "
            "VALUES (:id, :workspace, :lot, :transaction, :amount)"
        ),
        {
            "id": consumption_id,
            "workspace": workspace_id,
            "lot": lot_id,
            "transaction": transaction_id,
            "amount": amount,
        },
    )
    return consumption_id


def _transaction_reference(connection: sa.Connection, redemption_id: str) -> Any:
    return connection.execute(
        sa.text("SELECT credit_transaction_id FROM coupon_redemptions WHERE id = :id"),
        {"id": redemption_id},
    ).scalar_one()


def _seed_ledger(connection: sa.Connection) -> dict[str, str]:
    """Legacy rows covering every branch the backfill has to decide.

    Workspace A: ``+100`` (order), ``+500`` soft-deleted, ``-30`` (dangling
    generated image), ``0``, ``+50`` coupon. Workspace B: ``+200`` under an
    unknown legacy transaction type.
    """
    ids = _seed_graph(connection)

    _insert_legacy_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=100,
        transaction_type="TOP_UP",
        created_at="2026-01-01 00:00:01",
        reference_type="order",
        reference_id=ids["order"],
    )
    _insert_legacy_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=500,
        transaction_type="TOP_UP",
        created_at="2026-01-01 00:00:02",
        deleted_at="2026-01-02 00:00:00",
    )
    _insert_legacy_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=-30,
        transaction_type="GENERATION",
        created_at="2026-01-01 00:00:03",
        reference_type="generated_image",
        reference_id=uuid4().hex,
    )
    _insert_legacy_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=0,
        transaction_type="ADJUSTMENT",
        created_at="2026-01-01 00:00:04",
    )
    _insert_legacy_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=50,
        transaction_type="COUPON_CREDIT",
        created_at="2026-01-01 00:00:05",
    )
    _insert_legacy_transaction(
        connection,
        workspace_id=ids["other_workspace"],
        amount=200,
        transaction_type="legacy_custom",
        created_at="2026-01-02 00:00:00",
        reference_type="legacy_invoice",
        reference_id=uuid4().hex,
    )
    return ids


def _credit_rows(connection: sa.Connection) -> list[tuple[Any, ...]]:
    """Every surviving ledger row, ordered so the balance sequence is readable."""
    rows = connection.execute(
        sa.text(
            f"SELECT workspace_id, amount, type, balance_after, order_id, invoice_id, "
            f"generated_image_id, image_resize_id, created_by, created_at FROM {TABLE} "
            "ORDER BY created_at, id"
        )
    ).fetchall()
    return [tuple(row) for row in rows]


def _balances_by_workspace(connection: sa.Connection) -> dict[str, list[int]]:
    rows = connection.execute(
        sa.text(f"SELECT workspace_id, balance_after FROM {TABLE} ORDER BY created_at, id")
    ).fetchall()
    balances: dict[str, list[int]] = {}
    for workspace_id, balance in rows:
        balances.setdefault(workspace_id, []).append(balance)
    return balances


# --- 1. schema shape --------------------------------------------------------


def test_upgrade_replaces_the_legacy_columns_with_the_final_ledger_shape(
    database: Path,
) -> None:
    with _connect(database) as connection:
        legacy = _columns(connection)
        assert "transaction_type" in legacy, (
            "the fixture must start at the legacy ledger shape, otherwise the upgrade "
            "under test is not exercised"
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        columns = _columns(connection)

    missing = [name for name in FINAL_COLUMNS if name not in columns]
    assert not missing, (
        "workspace_credit_transactions is missing the final columns "
        f"{missing}; the final modeling declares balance_after, type and the four "
        "correlation columns"
    )
    legacy_left = [name for name in DROPPED_COLUMNS if name in columns]
    assert not legacy_left, (
        f"the legacy columns {legacy_left} must be dropped: an append-only ledger has no "
        "updated_at/deleted_at and correlations use dedicated columns"
    )

    assert columns["amount"]["notnull"] is True, "amount must stay NOT NULL"
    assert columns["balance_after"]["notnull"] is True, (
        "balance_after is NOT NULL in the final modeling"
    )
    assert _default(columns["balance_after"]["default"]) == "0", (
        f"balance_after needs DEFAULT 0, got {columns['balance_after']['default']!r}"
    )
    assert columns["type"]["notnull"] is True, "type is NOT NULL in the final modeling"
    for optional in (
        "order_id",
        "invoice_id",
        "generated_image_id",
        "image_resize_id",
        "created_by",
    ):
        assert columns[optional]["notnull"] is False, f"{optional} must stay nullable"


# --- 2. backfill of type, balance_after and the dedicated references --------


def test_upgrade_backfills_type_balance_and_dedicated_references(database: Path) -> None:
    with _connect(database) as connection:
        ids = _seed_ledger(connection)

    _upgrade(database, "head")

    with _connect(database) as connection:
        rows = _credit_rows(connection)
        balances = _balances_by_workspace(connection)

    assert len(rows) == 4, (
        "the two dropped legacy rows (soft-deleted and amount = 0) must not survive, and "
        f"no surviving row may be lost; got {len(rows)} rows: {rows}"
    )

    by_workspace = {row[0]: row for row in rows if row[0] == ids["workspace"] and row[3] == 100}
    assert len(by_workspace) == 1, (
        f"the first workspace transaction must survive with balance_after 100; got {rows}"
    )
    workspace_row = by_workspace[ids["workspace"]]
    assert workspace_row[2] == "TOP_UP", (
        f"transaction_type TOP_UP must become type TOP_UP, got {workspace_row[2]!r}"
    )
    assert workspace_row[4] == ids["order"], (
        "reference_type='order' with a resolvable id must move to order_id; got "
        f"{workspace_row[4]!r} expected {ids['order']!r}"
    )
    for index, name in ((5, "invoice_id"), (6, "generated_image_id"), (7, "image_resize_id")):
        assert workspace_row[index] is None, (
            f"{name} must stay NULL for a row that never referenced it, got "
            f"{workspace_row[index]!r}"
        )
    assert workspace_row[8] is None, (
        f"created_by has no legacy source and must be NULL, got {workspace_row[8]!r}"
    )

    types = sorted(row[2] for row in rows)
    assert types == ["ADJUSTMENT", "COUPON_CREDIT", "GENERATION", "TOP_UP"], (
        "the legacy vocabulary must map to credit_transaction_type, with the unknown "
        f"'legacy_custom' value becoming ADJUSTMENT; got {types}"
    )

    generated_image_row = next(row for row in rows if row[2] == "GENERATION")
    assert generated_image_row[6] is None, (
        "reference_type='generated_image' with an id no generated_images row declares is a "
        "dangling reference and must leave generated_image_id NULL; got "
        f"{generated_image_row[6]!r}"
    )

    unknown_reference_row = next(row for row in rows if row[2] == "ADJUSTMENT")
    for index, name in (
        (4, "order_id"),
        (5, "invoice_id"),
        (6, "generated_image_id"),
        (7, "image_resize_id"),
    ):
        assert unknown_reference_row[index] is None, (
            f"an unknown reference_type must not guess a dedicated column, got "
            f"{name}={unknown_reference_row[index]!r}"
        )

    assert balances == {
        ids["workspace"]: [100, 70, 120],
        ids["other_workspace"]: [200],
    }, (
        "balance_after is the cumulative SUM(amount) per workspace ordered by created_at, "
        "computed after dropping the deleted and zero-amount rows; got "
        f"{balances}"
    )


def test_upgrade_orders_the_running_balance_by_created_at_not_by_insert_order(
    database: Path,
) -> None:
    """A late insert with an older timestamp must not corrupt the cumulative sum."""
    with _connect(database) as connection:
        ids = _seed_graph(connection)
        # Inserted first but timestamped last, so a rowid-ordered backfill would read
        # the debit before the credit and drive the balance below zero.
        _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=-15,
            transaction_type="GENERATION",
            created_at="2026-01-01 00:00:02",
        )
        _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=40,
            transaction_type="TOP_UP",
            created_at="2026-01-01 00:00:01",
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        balances = _balances_by_workspace(connection)

    assert balances == {ids["workspace"]: [40, 25]}, (
        f"the running balance must follow created_at, not the physical insert order; got {balances}"
    )


def test_upgrade_drops_soft_deleted_and_zero_amount_rows(database: Path) -> None:
    with _connect(database) as connection:
        ids = _seed_ledger(connection)

    _upgrade(database, "head")

    with _connect(database) as connection:
        survivors = connection.execute(sa.text(f"SELECT amount FROM {TABLE}")).scalars().all()
        zero_rows = connection.execute(
            sa.text(f"SELECT COUNT(*) FROM {TABLE} WHERE amount = 0")
        ).scalar_one()

    assert zero_rows == 0, "no ledger row may keep amount = 0 after the backfill"
    assert 500 not in survivors, (
        "the soft-deleted row (+500) must be dropped: an append-only ledger has no "
        f"deleted_at to filter it later; survivors {survivors}"
    )
    assert sorted(survivors) == [-30, 50, 100, 200], (
        f"only the four live, non-zero rows may survive, got {sorted(survivors)}"
    )
    assert ids["workspace"] != ids["other_workspace"], "the two workspaces must be distinct"


# --- 3. indexes, checks and foreign keys ------------------------------------


def test_credit_ledger_indexes_match_the_final_modeling(database: Path) -> None:
    _upgrade(database, "head")

    with _connect(database) as connection:
        indexes = _indexes(connection)

    shapes = {(tuple(index["columns"]), index["unique"]) for index in indexes.values()}

    assert (("workspace_id", "created_at"), False) in shapes, (
        "the ledger needs the (workspace_id, created_at) index the balance query uses; got "
        f"{sorted(shapes)}"
    )
    for column in ("order_id", "invoice_id", "generated_image_id", "image_resize_id"):
        assert ((column, "type"), True) in shapes, (
            f"the final modeling declares a UNIQUE ({column}, type) index so one reference "
            f"cannot produce two transactions of the same type; got {sorted(shapes)}"
        )

    assert "uq_credit_tx_id_workspace" in indexes, (
        "the (id, workspace_id) unique index backs the composite foreign keys of "
        f"workspace_credit_lots and lot consumptions; got {sorted(indexes)}"
    )
    assert indexes["uq_credit_tx_id_workspace"]["unique"] is True
    assert indexes["uq_credit_tx_id_workspace"]["columns"] == ["id", "workspace_id"]

    assert "uq_credit_tx_image_resize" in indexes, (
        f"the dump names the image_resize unique index explicitly; got {sorted(indexes)}"
    )
    assert indexes["uq_credit_tx_image_resize"]["unique"] is True
    assert indexes["uq_credit_tx_image_resize"]["columns"] == ["image_resize_id", "type"]

    created_by = indexes.get("idx_m8_workspace_credit_transactions_created_by")
    assert created_by is not None, (
        f"the dump names the partial created_by index explicitly; got {sorted(indexes)}"
    )
    assert created_by["columns"] == ["created_by"]
    assert created_by["unique"] is False


def test_credit_ledger_checks_match_the_final_modeling(database: Path) -> None:
    _upgrade(database, "head")

    with _connect(database) as connection:
        ddl = _table_sql(connection)

    for constraint in (
        "chk_credit_tx_single_reference",
        "chk_credit_tx_balance_nonnegative",
        "chk_credit_tx_amount_by_type",
        # The dump declares the amount-nonzero rule inline, so the name is ours to
        # choose; `chk_credit_tx_amount_nonzero` is the expected one.
        "chk_credit_tx_amount_nonzero",
    ):
        assert constraint in ddl, (
            f"the final modeling declares {constraint} and the rebuilt table must keep it; "
            f"table SQL: {ddl}"
        )

    normalized_ddl = _without_spaces(ddl.lower())
    assert "amount<>0" in normalized_ddl or "amount!=0" in normalized_ddl, (
        "the dump declares `amount int NOT NULL CHECK (amount <> 0)`; the rebuilt table "
        f"must carry that rule, not only the by-type sign rule; table SQL: {ddl}"
    )

    assert "credit_transaction_type" in ddl, (
        f"type must be constrained by the credit_transaction_type vocabulary; table SQL: {ddl}"
    )
    for value in CREDIT_TRANSACTION_TYPES:
        assert value in ddl, (
            f"the credit_transaction_type vocabulary must declare {value}; table SQL: {ddl}"
        )


def test_credit_ledger_foreign_keys_match_the_final_modeling(database: Path) -> None:
    _upgrade(database, "head")

    with _connect(database) as connection:
        foreign_keys = _foreign_keys(connection)

    by_target = {(fk["table"], tuple(fk["columns"])): fk for fk in foreign_keys}

    assert ("orders", ("order_id", "workspace_id")) in by_target, (
        "order_id must be validated by the composite (order_id, workspace_id) foreign key "
        f"so a transaction cannot cross workspaces; got {sorted(by_target)}"
    )
    order_key = by_target[("orders", ("order_id", "workspace_id"))]
    assert order_key["targets"] == ["id", "workspace_id"], order_key
    assert order_key["on_delete"] == "RESTRICT", order_key

    for target, column in (
        ("invoices", "invoice_id"),
        ("generated_images", "generated_image_id"),
        ("image_resizes", "image_resize_id"),
    ):
        key = by_target.get((target, (column,)))
        assert key is not None, f"{column} must reference {target}(id); got {sorted(by_target)}"
        assert key["targets"] == ["id"], key
        assert key["on_delete"] == "RESTRICT", key

    created_by = by_target.get(("users", ("created_by",)))
    assert created_by is not None, f"created_by must reference users(id); got {sorted(by_target)}"
    assert created_by["on_delete"] == "SET NULL", created_by

    workspace = by_target.get(("workspaces", ("workspace_id",)))
    assert workspace is not None, f"workspace_id must reference workspaces(id); got {by_target}"
    assert workspace["on_delete"] == "RESTRICT", (
        f"the final modeling deletes workspaces with RESTRICT here; got {workspace['on_delete']!r}"
    )


# --- 4. constraints behave like the final modeling --------------------------


@pytest.fixture()
def fresh_engine() -> Iterator[sa.Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def _insert_transaction(
    connection: sa.Connection,
    *,
    amount: int,
    transaction_type: str,
    balance_after: int = 0,
    order_id: str | None = None,
    invoice_id: str | None = None,
    generated_image_id: str | None = None,
) -> None:
    connection.execute(
        sa.text(
            f"INSERT INTO {TABLE} (id, workspace_id, amount, balance_after, type, order_id, "
            "invoice_id, generated_image_id) VALUES (:id, :workspace, :amount, :balance, "
            ":type, :order_id, :invoice_id, :generated_image_id)"
        ),
        {
            "id": uuid4().hex,
            "workspace": uuid4().hex,
            "amount": amount,
            "balance": balance_after,
            "type": transaction_type,
            "order_id": order_id,
            "invoice_id": invoice_id,
            "generated_image_id": generated_image_id,
        },
    )


@pytest.mark.parametrize(
    ("amount", "transaction_type"),
    [
        (100, "SUBSCRIPTION_CREDIT"),
        (100, "TOP_UP"),
        (100, "COUPON_CREDIT"),
        (100, "REFUND"),
        (-30, "GENERATION"),
        (-30, "EXPIRATION"),
        (1, "ADJUSTMENT"),
        (-1, "ADJUSTMENT"),
    ],
)
def test_credit_ledger_type_and_amount_pairs_are_accepted(
    fresh_engine: sa.Engine, amount: int, transaction_type: str
) -> None:
    """The vocabulary is the dump's, and ADJUSTMENT accepts either sign.

    Zero is not in the accepted list on purpose: the dump declares the inline
    ``CHECK (amount <> 0)`` beside ``chk_credit_tx_amount_by_type``, and the
    ``ADJUSTMENT`` branch of the by-type rule is the one that would otherwise let
    a no-op transaction through.
    """
    with fresh_engine.begin() as connection:
        _insert_transaction(connection, amount=amount, transaction_type=transaction_type)

    with fresh_engine.connect() as connection:
        stored = connection.execute(sa.text(f"SELECT type, amount FROM {TABLE}")).one()
    assert tuple(stored) == (transaction_type, amount)


@pytest.mark.parametrize(
    ("amount", "transaction_type"),
    [(-10, "TOP_UP"), (10, "GENERATION"), (-10, "COUPON_CREDIT")],
)
def test_credit_ledger_rejects_amounts_with_the_wrong_sign(
    fresh_engine: sa.Engine, amount: int, transaction_type: str
) -> None:
    with pytest.raises(sa.exc.IntegrityError) as error:
        with fresh_engine.begin() as connection:
            _insert_transaction(connection, amount=amount, transaction_type=transaction_type)
    assert "chk_credit_tx_amount_by_type" in str(error.value)


def test_credit_ledger_rejects_a_zero_amount(fresh_engine: sa.Engine) -> None:
    """`amount <> 0` is a rule of its own in the dump, not a branch of the by-type rule.

    The final modeling declares ``amount int NOT NULL CHECK (amount <> 0)`` beside
    ``chk_credit_tx_amount_by_type``, and ``ADJUSTMENT`` accepts either sign, so the
    zero case is only covered by that separate rule. A no-op ledger entry would
    otherwise slip through and make ``balance_after`` ambiguous.

    The dump's inline CHECK is unnamed, so any constraint name is acceptable as
    long as the database rejects the row and the evidence names the amount rule.
    """
    with pytest.raises(sa.exc.IntegrityError) as error:
        with fresh_engine.begin() as connection:
            _insert_transaction(connection, amount=0, transaction_type="ADJUSTMENT")

    message = str(error.value)
    normalized = _without_spaces(message.lower())
    assert "check constraint failed" in message.lower(), message

    names_amount_rule = "amount_nonzero" in normalized or "amount<>0" in normalized
    assert names_amount_rule or "amount!=0" in normalized, (
        "a zero-amount ledger row must be rejected by an amount-nonzero CHECK; expected "
        "the constraint name chk_credit_tx_amount_nonzero or its SQL (amount <> 0), got "
        f"{message!r}"
    )
    assert "amount_by_type" not in normalized, (
        "the by-type rule accepts ADJUSTMENT with any amount, so this rejection cannot "
        f"come from it; got {message!r}"
    )


def test_credit_ledger_rejects_an_unknown_type(fresh_engine: sa.Engine) -> None:
    """An out-of-vocabulary type is rejected, whichever CHECK SQLite reports first.

    SQLite reports only the first violated CHECK. An unknown type is not in any
    allowed list of ``chk_credit_tx_amount_by_type`` and is not ``ADJUSTMENT``, so
    that constraint may legitimately be the one named; the vocabulary rule is
    asserted structurally by the DDL/model tests instead of racing the message.
    """
    with pytest.raises(sa.exc.IntegrityError) as error:
        with fresh_engine.begin() as connection:
            _insert_transaction(connection, amount=10, transaction_type="legacy_custom")

    message = str(error.value).lower()
    assert "credit_transaction_type" in message or "chk_credit_tx_amount_by_type" in message, (
        "an unknown credit transaction type must be rejected by the vocabulary CHECK or "
        f"by the amount-by-type CHECK, got {error.value!r}"
    )


def test_credit_ledger_rejects_a_negative_balance(fresh_engine: sa.Engine) -> None:
    with pytest.raises(sa.exc.IntegrityError) as error:
        with fresh_engine.begin() as connection:
            _insert_transaction(
                connection, amount=-10, transaction_type="GENERATION", balance_after=-1
            )
    assert "chk_credit_tx_balance_nonnegative" in str(error.value)


def test_credit_ledger_rejects_more_than_one_reference(fresh_engine: sa.Engine) -> None:
    with pytest.raises(sa.exc.IntegrityError) as error:
        with fresh_engine.begin() as connection:
            _insert_transaction(
                connection,
                amount=10,
                transaction_type="TOP_UP",
                order_id=uuid4().hex,
                invoice_id=uuid4().hex,
            )
    assert "chk_credit_tx_single_reference" in str(error.value)


# --- 5. migration failure mode ----------------------------------------------


def test_negative_balance_aborts_with_value_error_naming_workspace_and_balance(
    database: Path,
) -> None:
    """A wallet cannot go below zero: the backfill must fail loudly, not write -10.

    The migration has to raise its own ``ValueError`` that names the offending
    workspace and the balance it computed. Letting the rebuilt table's
    ``chk_credit_tx_balance_nonnegative`` fail instead is useless to an operator:
    SQLite reports a constraint name, not which workspace or which row.
    """
    with _connect(database) as connection:
        ids = _seed_graph(connection)
        _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=100,
            transaction_type="TOP_UP",
            created_at="2026-01-01 00:00:01",
        )
        _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=-130,
            transaction_type="GENERATION",
            created_at="2026-01-01 00:00:02",
        )

    with pytest.raises(ValueError) as error:
        _upgrade(database, "head")

    message = str(error.value)
    assert ids["workspace"] in message, (
        f"the abort must name the offending workspace {ids['workspace']!r}; got {message!r}"
    )
    assert "-30" in message, (
        f"the abort must name the negative balance it computed (-30); got {message!r}"
    )
    assert "balance" in message.lower(), (
        f"the abort must say the credit balance is the problem; got {message!r}"
    )


def test_canonical_upgrade_leaves_no_dangling_foreign_keys(database: Path) -> None:
    """Every dedicated reference the backfill writes must resolve."""
    with _connect(database) as connection:
        _seed_ledger(connection)

    _upgrade(database, "head")

    with _connect(database) as connection:
        targets = {fk["table"] for fk in _foreign_keys(connection)}
        assert "orders" in targets and "users" in targets, (
            "this guard is only meaningful once the upgrade creates the ledger foreign "
            f"keys; got {sorted(targets)}"
        )
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()

    assert violations == [], (
        "the upgraded database has dangling foreign keys (table, rowid, parent, fkid): "
        f"{violations}"
    )


# --- 6. depended-on rows the backfill drops ---------------------------------
#
# Dropping a legacy row is a data change the children of the ledger do not see:
# `migrations/env.py` disables `PRAGMA foreign_keys`, so a coupon redemption, a
# credit lot or a lot consumption keeps pointing at an id the upgraded ledger no
# longer has. The rebuild must handle each dependent explicitly instead of
# leaving an orphan that only `PRAGMA foreign_key_check` can find.


def test_upgrade_nulls_coupon_redemption_for_a_dropped_transaction(database: Path) -> None:
    """A dropped parent must null the child link, matching ``ON DELETE SET NULL``.

    ``coupon_redemptions.credit_transaction_id`` is declared ``ON DELETE SET NULL``,
    so a redemption whose transaction the backfill drops (soft-deleted or
    ``amount = 0``) must read as NULL afterwards; a resolvable link must survive.
    """
    with _connect(database) as connection:
        ids = _seed_graph(connection)
        kept = _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=100,
            transaction_type="TOP_UP",
            created_at="2026-01-01 00:00:01",
        )
        zero_amount = _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=0,
            transaction_type="ADJUSTMENT",
            created_at="2026-01-01 00:00:02",
        )
        soft_deleted = _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=50,
            transaction_type="TOP_UP",
            created_at="2026-01-01 00:00:03",
            deleted_at="2026-01-02 00:00:00",
        )
        zero_redemption = _insert_redemption(
            connection,
            user_id=ids["user"],
            workspace_id=ids["workspace"],
            order_id=ids["order"],
            credit_transaction_id=zero_amount,
            code=f"ZERO{uuid4().hex[:8].upper()}",
        )
        soft_redemption = _insert_redemption(
            connection,
            user_id=ids["user"],
            workspace_id=ids["workspace"],
            order_id=ids["order"],
            credit_transaction_id=soft_deleted,
            code=f"SOFT{uuid4().hex[:8].upper()}",
        )
        kept_redemption = _insert_redemption(
            connection,
            user_id=ids["user"],
            workspace_id=ids["workspace"],
            order_id=ids["order"],
            credit_transaction_id=kept,
            code=f"KEPT{uuid4().hex[:8].upper()}",
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        zero_value = _transaction_reference(connection, zero_redemption)
        soft_value = _transaction_reference(connection, soft_redemption)
        kept_value = _transaction_reference(connection, kept_redemption)
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()

    assert zero_value is None, (
        "coupon_redemptions.credit_transaction_id pointed at an amount=0 transaction the "
        f"backfill dropped; the FK is ON DELETE SET NULL, so it must be NULL, got {zero_value!r}"
    )
    assert soft_value is None, (
        "coupon_redemptions.credit_transaction_id pointed at a soft-deleted transaction "
        f"the backfill dropped; it must be NULL, got {soft_value!r}"
    )
    assert kept_value == kept, (
        "neutralising the dropped parents must not touch a resolvable redemption; got "
        f"{kept_value!r} expected {kept!r}"
    )
    assert violations == [], (
        "PRAGMA foreign_key_check still reports dangling rows (table, rowid, parent, fkid): "
        f"{violations}"
    )


def test_upgrade_aborts_when_a_dropped_transaction_is_a_lot_grant(database: Path) -> None:
    """A Credit Lot cannot lose its grant transaction: abort before the rebuild.

    ``workspace_credit_lots.grant_transaction_id`` is ``NOT NULL`` and
    ``ON DELETE RESTRICT``, so the backfill cannot null it. Dropping the grant
    leaves a lot whose original amount has no origin, which is worse than a failed
    migration; the abort has to name the lot or the transaction.
    """
    with _connect(database) as connection:
        ids = _seed_graph(connection)
        dropped = _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=0,
            transaction_type="ADJUSTMENT",
            created_at="2026-01-01 00:00:01",
        )
        lot_id = _insert_lot(
            connection,
            workspace_id=ids["workspace"],
            grant_transaction_id=dropped,
            original_amount=100,
            remaining_amount=100,
        )

    with pytest.raises((ValueError, RuntimeError)) as error:
        _upgrade(database, "head")

    message = str(error.value)
    normalized = message.lower()
    assert dropped in message or lot_id in message, (
        "the abort must name the dropped grant transaction or the lot that depends on "
        f"it; got {message!r}"
    )
    assert "lot" in normalized or "grant" in normalized, (
        f"the abort must say a Credit Lot is the problem; got {message!r}"
    )


def test_upgrade_aborts_when_a_dropped_transaction_is_a_lot_consumption(
    database: Path,
) -> None:
    """A consumption cannot lose the transaction it accounts for; abort clearly."""
    with _connect(database) as connection:
        ids = _seed_graph(connection)
        grant = _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=100,
            transaction_type="TOP_UP",
            created_at="2026-01-01 00:00:01",
        )
        dropped = _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=0,
            transaction_type="ADJUSTMENT",
            created_at="2026-01-01 00:00:02",
        )
        lot_id = _insert_lot(
            connection,
            workspace_id=ids["workspace"],
            grant_transaction_id=grant,
            original_amount=100,
            remaining_amount=90,
        )
        consumption_id = _insert_lot_consumption(
            connection,
            workspace_id=ids["workspace"],
            lot_id=lot_id,
            transaction_id=dropped,
            amount=10,
        )

    with pytest.raises((ValueError, RuntimeError)) as error:
        _upgrade(database, "head")

    message = str(error.value)
    normalized = message.lower()
    assert dropped in message or consumption_id in message, (
        "the abort must name the dropped transaction or the consumption that depends on "
        f"it; got {message!r}"
    )
    assert "consumption" in normalized or "lot" in normalized, (
        f"the abort must say a lot consumption is the problem; got {message!r}"
    )


def test_migrated_foreign_key_names_match_the_model(database: Path) -> None:
    """SQLite cannot add a named constraint later, so the rebuild must name them.

    The final metadata declares ``fk_credit_tx_order``, ``fk_credit_tx_workspace``,
    ``fk_credit_tx_invoice``, ``fk_credit_tx_generated_image``,
    ``fk_credit_tx_image_resize`` and ``fk_credit_tx_created_by``. An inline
    unnamed foreign key produces the same behaviour on SQLite but cannot be
    introspected by name, and a later revision that needs to drop or rebuild one
    has nothing to address.
    """
    _upgrade(database, "head")

    with _connect(database) as connection:
        ddl = _table_sql(connection)

    missing = [
        name
        for name in (
            "fk_credit_tx_order",
            "fk_credit_tx_workspace",
            "fk_credit_tx_invoice",
            "fk_credit_tx_generated_image",
            "fk_credit_tx_image_resize",
            "fk_credit_tx_created_by",
        )
        if name not in ddl
    ]

    assert not missing, (
        f"the rebuilt table does not declare the named foreign keys {missing}; table SQL: {ddl}"
    )


def test_type_aliases_map_to_the_final_vocabulary(database: Path) -> None:
    """The legacy generic column accepted aliases; the backfill must translate them.

    A ``CREDIT``/``GRANT``/``TOPUP``/``PURCHASE`` movement is a top-up, a
    ``DEBIT``/``SPEND`` is a generation charge and ``ADJUST`` is an adjustment.
    Dropping the row or collapsing every alias into ``ADJUSTMENT`` would lose the
    business meaning the ledger is queried for.
    """
    aliases = (
        ("CREDIT", "TOP_UP", 10),
        ("GRANT", "TOP_UP", 10),
        ("TOPUP", "TOP_UP", 10),
        ("PURCHASE", "TOP_UP", 10),
        ("DEBIT", "GENERATION", -5),
        ("SPEND", "GENERATION", -5),
        ("ADJUST", "ADJUSTMENT", 1),
    )
    expected: dict[str, str] = {}
    with _connect(database) as connection:
        ids = _seed_graph(connection)
        for index, (legacy, _final, amount) in enumerate(aliases, start=1):
            expected[legacy] = _insert_legacy_transaction(
                connection,
                workspace_id=ids["workspace"],
                amount=amount,
                transaction_type=legacy,
                created_at=f"2026-01-01 00:00:{index:02d}",
            )

    _upgrade(database, "head")

    with _connect(database) as connection:
        rows = connection.execute(
            sa.text(f"SELECT id, type FROM {TABLE} WHERE workspace_id = :workspace"),
            {"workspace": ids["workspace"]},
        ).fetchall()

    actual = {row[0]: row[1] for row in rows}
    problems = [
        f"{legacy}: expected {final}, got {actual.get(expected[legacy])!r}"
        for legacy, final, _amount in aliases
        if actual.get(expected[legacy]) != final
    ]
    assert not problems, "the legacy type aliases are not mapped:\n" + "\n".join(problems)


def test_duplicate_legacy_order_type_aborts_with_a_clear_error(database: Path) -> None:
    """Two legacy rows cannot become the same ``(order_id, type)`` entry.

    The final modeling declares ``UNIQUE (order_id, type)`` so a single order
    cannot add two top-ups. Two legacy rows with ``reference_type='order'`` and
    ``transaction_type='TOP_UP'`` therefore collide during the copy. The migration
    must abort with a ``ValueError`` naming the duplicate instead of letting SQLite
    fail late with an opaque ``UNIQUE constraint failed`` from the rebuild table.
    Silently dropping one of the movements is not acceptable: the ledger is
    append-only and the amounts are business data.
    """
    with _connect(database) as connection:
        ids = _seed_graph(connection)
        _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=60,
            transaction_type="TOP_UP",
            created_at="2026-01-01 00:00:01",
            reference_type="order",
            reference_id=ids["order"],
        )
        _insert_legacy_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=40,
            transaction_type="TOP_UP",
            created_at="2026-01-01 00:00:02",
            reference_type="order",
            reference_id=ids["order"],
        )

    with pytest.raises((ValueError, RuntimeError)) as error:
        _upgrade(database, "head")

    message = str(error.value)
    normalized = message.lower()
    assert ids["order"] in message or "duplicate" in normalized or "order" in normalized, (
        "the abort must name the duplicated order (or the duplicate pair) so an operator "
        f"can fix the legacy rows; got {message!r}"
    )
    assert "unique constraint failed" not in normalized, (
        "the migration must detect the duplicate itself instead of failing late inside "
        f"the rebuild INSERT; got {message!r}"
    )


# --- 7. downgrade -----------------------------------------------------------


def test_downgrade_restores_the_legacy_shape_without_resurrecting_dropped_rows(
    database: Path,
) -> None:
    """Issue #162 asks for a functional downgrade; deleted rows stay deleted.

    The reversal is shape-based, not value-based: ``transaction_type`` comes back
    from ``type`` and the dedicated references collapse into the generic pair, so
    the original ``legacy_custom`` value is not recoverable and is documented as a
    lossy step. Rows the backfill dropped are not restored.
    """
    with _connect(database) as connection:
        ids = _seed_ledger(connection)

    _upgrade(database, "head")

    with _connect(database) as connection:
        assert "type" in _columns(connection), (
            "the downgrade test assumes the upgrade applied the final ledger shape"
        )

    _downgrade(database, LEGACY_REVISION)

    with _connect(database) as connection:
        columns = _columns(connection)
        legacy_left = [name for name in ADDED_COLUMNS if name in columns]
        assert not legacy_left, (
            f"the downgrade must drop the final-only columns {legacy_left}; got {sorted(columns)}"
        )
        for name in ("transaction_type", "updated_at", "deleted_at"):
            assert name in columns, f"the downgrade must restore {name}; got {sorted(columns)}"
        assert columns["transaction_type"]["notnull"] is True, (
            "the restored transaction_type must be NOT NULL, so the downgrade has to "
            "remap type back"
        )

        rows = connection.execute(
            sa.text(
                f"SELECT workspace_id, amount, transaction_type FROM {TABLE} "
                "ORDER BY created_at, id"
            )
        ).fetchall()

    assert len(rows) == 4, (
        "the downgrade must keep the four surviving rows and must not resurrect the "
        f"deleted or zero-amount ones; got {[tuple(row) for row in rows]}"
    )
    amounts = sorted(row[1] for row in rows)
    assert amounts == [-30, 50, 100, 200], f"the downgrade must not rewrite amounts; got {amounts}"
    assert all(row[2] for row in rows), (
        f"every restored row needs a non-null transaction_type; got {[tuple(row) for row in rows]}"
    )
    restored_types = sorted(row[2] for row in rows)
    assert restored_types == ["ADJUSTMENT", "COUPON_CREDIT", "GENERATION", "TOP_UP"], (
        "the downgrade maps type back to the legacy vocabulary; the unknown legacy value "
        f"cannot be recovered and reads as ADJUSTMENT; got {restored_types}"
    )
    assert ids["workspace"] in {row[0] for row in rows}


# --- 8. metadata ------------------------------------------------------------


def test_metadata_declares_the_final_credit_ledger_shape() -> None:
    table = Base.metadata.tables[TABLE]

    missing = [name for name in FINAL_COLUMNS if name not in table.c]
    assert not missing, f"the model is missing the final ledger columns {missing}"
    legacy_left = [name for name in DROPPED_COLUMNS if name in table.c]
    assert not legacy_left, f"the model still declares the legacy columns {legacy_left}"

    assert table.c.balance_after.nullable is False
    assert str(table.c.balance_after.server_default.arg).strip().strip("'\"") == "0"

    transaction_type = table.c.type.type
    assert isinstance(transaction_type, sa.Enum), (
        f"type must render as the portable enum, got {transaction_type!r}"
    )
    assert transaction_type.name == "credit_transaction_type"
    assert tuple(transaction_type.enums) == CREDIT_TRANSACTION_TYPES
    assert transaction_type.create_constraint is True, (
        "the vocabulary CHECK must be generated by the enum column "
        "(enum_column(..., create_constraint=True)); a hand-written CheckConstraint "
        "with the enum name is not a declared exception under the T26 policy, so the "
        "parity gate cannot tell the vocabulary guarantee apart from real debt"
    )


def test_metadata_credit_ledger_checks_follow_the_final_modeling() -> None:
    """The model must carry the dump's amount-nonzero rule as its own constraint."""
    table = Base.metadata.tables[TABLE]
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, sa.CheckConstraint)
    }

    assert "chk_credit_tx_amount_nonzero" in checks, (
        "the dump declares `amount int NOT NULL CHECK (amount <> 0)`; the model needs a "
        f"constraint for it, got {sorted(name for name in checks if name)}"
    )
    normalized = _without_spaces(checks["chk_credit_tx_amount_nonzero"].lower())
    assert "amount<>0" in normalized or "amount!=0" in normalized, (
        "chk_credit_tx_amount_nonzero must compare amount against zero; got "
        f"{checks['chk_credit_tx_amount_nonzero']!r}"
    )

    for name in (
        "chk_credit_tx_single_reference",
        "chk_credit_tx_balance_nonnegative",
        "chk_credit_tx_amount_by_type",
        "credit_transaction_type",
    ):
        assert name in checks, f"the model is missing the {name} constraint; got {sorted(checks)}"


def test_metadata_credit_ledger_indexes_cover_the_final_modeling() -> None:
    table = Base.metadata.tables[TABLE]
    indexes = {index.name: index for index in table.indexes}

    shapes = {
        (tuple(column.name for column in index.columns), bool(index.unique))
        for index in table.indexes
    }
    assert (("workspace_id", "created_at"), False) in shapes, sorted(shapes)
    for column in ("order_id", "invoice_id", "generated_image_id", "image_resize_id"):
        assert ((column, "type"), True) in shapes, sorted(shapes)

    for name in (
        "uq_credit_tx_id_workspace",
        "uq_credit_tx_image_resize",
        "idx_m8_workspace_credit_transactions_created_by",
    ):
        assert name in indexes, (
            f"the model must keep the dump index name {name}; got {sorted(indexes)}"
        )


def test_metadata_credit_ledger_foreign_keys_follow_the_final_modeling() -> None:
    """Each FK is asserted with its local columns, target and ``ON DELETE``.

    The model declares the constraints through ``ForeignKeyConstraint``, so the
    enumeration reads ``table.foreign_key_constraints`` and its elements: a
    single-column ``ForeignKey`` (``table.foreign_keys``) cannot describe the
    composite ``(order_id, workspace_id)`` key.
    """
    table = Base.metadata.tables[TABLE]

    keys: dict[tuple[str, ...], tuple[str, tuple[str, ...], str | None]] = {}
    for constraint in table.foreign_key_constraints:
        columns = tuple(element.parent.name for element in constraint.elements)
        targets = {element.column.table.name for element in constraint.elements}
        assert len(targets) == 1, (
            f"the foreign key on {columns} points at several tables: {sorted(targets)}"
        )
        target_columns = tuple(element.column.name for element in constraint.elements)
        keys[columns] = (targets.pop(), target_columns, constraint.ondelete)

    expected = {
        ("order_id", "workspace_id"): ("orders", ("id", "workspace_id"), "RESTRICT"),
        ("invoice_id",): ("invoices", ("id",), "RESTRICT"),
        ("generated_image_id",): ("generated_images", ("id",), "RESTRICT"),
        ("image_resize_id",): ("image_resizes", ("id",), "RESTRICT"),
        ("created_by",): ("users", ("id",), "SET NULL"),
        ("workspace_id",): ("workspaces", ("id",), "RESTRICT"),
    }

    problems = [
        f"{columns}: expected {targets}{target_columns} ON DELETE {on_delete}, "
        f"got {keys.get(columns)}"
        for columns, (targets, target_columns, on_delete) in expected.items()
        if keys.get(columns) != (targets, target_columns, on_delete)
    ]

    assert not problems, (
        "the credit ledger foreign keys do not follow the final modeling:\n" + "\n".join(problems)
    )
    assert set(keys) == set(expected), f"unexpected credit ledger foreign keys: {sorted(keys)}"
