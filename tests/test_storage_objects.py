"""Storage objects of the final modeling, ported to SQLite (T20, issue #163).

The final modeling keeps business rules in the database, not only in tables: the
dump declares **70** storage objects — 11 functions and 58 triggers plus the
``charges_with_last_transaction`` view. ADR-030 decision 11 requires each one to be
classified object by object: ported as a SQLite trigger, moved to the application
with an equivalent test, or explicitly out of scope with a written justification
and risk. The credit ledger, the credit lot, the coupon snapshot and the
append-only subscription history are the invariants that may not depend on
discipline alone.

Every test here builds a real database from ``tests/contracts/schema_prev_ddl.sql``,
stamps ``0005_content_text_versions``, upgrades to the head that precedes T20
(``0035_credit_ledger_alignment``) and then to ``head``. The guards are therefore
asserted on the schema a migration actually produces, never on
``Base.metadata.create_all()``, which cannot express triggers or a view.

Expected repository seams. The two derived credit measures of ADR-019 are exposed
by ``creator/credit/ports.py`` and ``creator/credit/repository.py`` with these
signatures::

    WorkspaceCreditTransactionRepository.workspace_balance(workspace_id: UUID) -> int
    WorkspaceCreditTransactionRepository.lot_available(workspace_id: UUID, lot_id: UUID) -> int

``workspace_balance`` sums ``remaining_amount`` over non-expired lots, and
``lot_available`` returns ``0`` for an expired lot and for a lot that belongs to
another Workspace — a Credit Lot is tenant scoped, so an identifier alone must
never be enough. ``CreditLedgerQueries`` below is the reference implementation the
port must match.

The ``charges_with_last_transaction`` view is exposed by the charge capability::

    SqlAlchemyChargeRepository.get_with_last_transaction_for_user(
        *, user_id: UUID, charge_id: UUID
    ) -> <record with last_transaction_id and last_transaction_status>

It returns the latest transaction by ``(created_at, id)``, ``None``/``None`` when
the charge has no transaction, and ``None`` for a charge of another tenant.
"""

from __future__ import annotations

import contextlib
import re
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from creator.billing_account.models import BillingAccount
from creator.charge.models import Charge, ChargeTransaction
from creator.charge.repository import SqlAlchemyChargeRepository
from creator.coupon.models import Coupon
from creator.coupon.repository import SqlAlchemyCouponRedemptionRepository
from creator.coupon.schemas import CouponRedemptionCreateRequest
from creator.infrastructure.database.db import create_database_engine
from creator.infrastructure.database.final_schema import (  # type: ignore[import-untyped]
    parse_final,
)
from creator.order.models import Order
from creator.user.models import User
from creator.workspace.models import Workspace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREV_SCHEMA = PROJECT_ROOT / "tests" / "contracts" / "schema_prev_ddl.sql"
FINAL_DUMP = PROJECT_ROOT / "docs" / "migration" / "Creator_DB_final.sql"
STORAGE_MATRIX = PROJECT_ROOT / "docs" / "migration" / "storage-objects-matrix.md"

PREV_REVISION = "0005_content_text_versions"
# Last revision of the chain before T20 introduces the storage objects.
PRE_T20_REVISION = "0035_credit_ledger_alignment"

# SQLite trigger name -> table the trigger must be attached to.
REQUIRED_TRIGGERS: Final[tuple[tuple[str, str], ...]] = (
    ("trg_credit_tx_immutable_update", "workspace_credit_transactions"),
    ("trg_credit_tx_immutable_delete", "workspace_credit_transactions"),
    ("trg_credit_consumption_immutable_update", "workspace_credit_lot_consumptions"),
    ("trg_credit_consumption_immutable_delete", "workspace_credit_lot_consumptions"),
    ("trg_subscription_history_append_only_update", "subscription_history"),
    ("trg_subscription_history_append_only_delete", "subscription_history"),
    ("trg_credit_lot_no_delete", "workspace_credit_lots"),
    ("trg_credit_lot_guard_update", "workspace_credit_lots"),
    ("trg_coupon_redemption_once_snapshot", "coupon_redemptions"),
)
REQUIRED_VIEW = "charges_with_last_transaction"

# Substrings that make a guard message actionable: it has to name the object that
# refused the write, so an operator can tell an immutability guard from an
# unrelated CHECK or foreign key.
LEDGER_NEEDLES: Final[tuple[str, ...]] = (
    "workspace_credit_transactions",
    "credit_tx",
    "ledger",
)
CONSUMPTION_NEEDLES: Final[tuple[str, ...]] = (
    "workspace_credit_lot_consumptions",
    "lot_consumption",
    "consumption",
    "consumo",
)
HISTORY_NEEDLES: Final[tuple[str, ...]] = (
    "subscription_history",
    "append-only",
    "append only",
)
LOT_NEEDLES: Final[tuple[str, ...]] = ("workspace_credit_lots", "lote", "credit lot")
COUPON_NEEDLES: Final[tuple[str, ...]] = (
    "once_per_workspace",
    "coupon_redemptions",
    "cupom",
)

# ADR-019 / ADR-030: these invariants must be enforced by a ported guard, never
# silently downgraded to "out of scope". The value is the set of accepted codes.
MUST_BE_ENFORCED: Final[dict[str, tuple[str, ...]]] = {
    "trg_m1_tx_immutable": ("a", "b"),
    "trg_m1_consumption_immutable": ("a", "b"),
    "trg_m1_lot_guard": ("a", "b"),
    "trg_m1_credit_lot_validate": ("a",),
    "trg_subscription_history_append_only": ("a", "b"),
    "trg_coupon_redemptions_set_once": ("a", "b"),
    # ADR-030 asks for an equivalent query with a test, so a repository query counts.
    "charges_with_last_transaction": ("a", "b", "c"),
}

# Classification codes of the inventory, with the wording each one must carry.
CLASSIFICATION_LABELS: Final[dict[str, tuple[str, ...]]] = {
    "a": ("trigger",),
    "b": ("guard", "guarda"),
    "c": ("query", "consulta", "repository", "reposit"),
    "d": ("out of scope", "out-of-scope", "fora de escopo"),
}
# Column aliases of the inventory table: the report may be written in English or
# in Portuguese, but it must carry these five columns.
MATRIX_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "object": frozenset({"objeto", "object", "nome", "name"}),
    "classification": frozenset({"classificacao", "classificação", "classification", "classe"}),
    "reason": frozenset({"motivo", "reason", "justificativa"}),
    "test": frozenset({"teste", "test", "evidencia", "evidência"}),
    "risk": frozenset({"risco", "risk"}),
}


# --- historical database setup ----------------------------------------------


def _config(database: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database}")
    return config


def _upgrade(database: Path, revision: str) -> None:
    command.upgrade(_config(database), revision)


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


def _temporary_directory(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix, dir=Path.cwd()))


@pytest.fixture(scope="module")
def pre_t20_database() -> Iterator[Path]:
    """Schema at ``0035_credit_ledger_alignment``, built once."""
    directory = _temporary_directory(".creator-pytest-storage-prev-")
    try:
        database = directory / "pre_t20.db"
        _prepare(database)
        _upgrade(database, PRE_T20_REVISION)
        yield database
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture(scope="module")
def head_database(pre_t20_database: Path) -> Iterator[Path]:
    """Schema at ``head``, i.e. after the T20 migration ran on top of the previous head."""
    directory = _temporary_directory(".creator-pytest-storage-head-")
    try:
        database = directory / "head.db"
        shutil.copy2(pre_t20_database, database)
        _upgrade(database, "head")
        yield database
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def database(head_database: Path, tmp_path: Path) -> Path:
    """Private copy so each test owns its rows."""
    target = tmp_path / "storage_objects.db"
    shutil.copy2(head_database, target)
    return target


@contextlib.contextmanager
def _connect(database: Path) -> Iterator[sqlite3.Connection]:
    """Raw driver connection: the guards are asserted below the ORM on purpose."""
    connection = sqlite3.connect(database, isolation_level=None)
    try:
        yield connection
    finally:
        connection.close()


# --- schema introspection ---------------------------------------------------


def _storage_objects(connection: sqlite3.Connection) -> dict[tuple[str, str], str]:
    rows = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master WHERE type IN ('trigger', 'view')"
    ).fetchall()
    return {(row[0], row[1]): row[2] for row in rows}


def _reject(
    connection: sqlite3.Connection, statement: str, parameters: tuple[object, ...] = ()
) -> str:
    """Run a write that must be refused, and return the driver message."""
    with pytest.raises(sqlite3.IntegrityError) as error:
        connection.execute(statement, parameters)
    return str(error.value)


def _mentions(message: str, needles: tuple[str, ...]) -> bool:
    normalized = message.lower()
    return any(needle.lower() in normalized for needle in needles)


# --- row seeds --------------------------------------------------------------


def _seed_billing_graph(connection: sqlite3.Connection) -> dict[str, str]:
    """One user, two workspaces and the billing graph the guards reference."""
    ids = {
        "user": uuid4().hex,
        "workspace": uuid4().hex,
        "other_workspace": uuid4().hex,
        "account": uuid4().hex,
        "order": uuid4().hex,
        "plan": uuid4().hex,
        "subscription": uuid4().hex,
    }
    connection.execute(
        "INSERT INTO users (id, display_name) VALUES (?, ?)",
        (ids["user"], "Storage Objects"),
    )
    connection.execute(
        "INSERT INTO workspaces (id, name) VALUES (?, ?)", (ids["workspace"], "Storage A")
    )
    connection.execute(
        "INSERT INTO workspaces (id, name) VALUES (?, ?)",
        (ids["other_workspace"], "Storage B"),
    )
    connection.execute(
        "INSERT INTO billing_accounts (id, user_id, payer_type, name, email) "
        "VALUES (?, ?, 'INDIVIDUAL', 'Storage', ?)",
        (ids["account"], ids["user"], f"{ids['account']}@example.com"),
    )
    connection.execute(
        "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
        "amount_cents, status) VALUES (?, ?, ?, 1000, 1000, 'PAID')",
        (ids["order"], ids["account"], ids["workspace"]),
    )
    connection.execute(
        "INSERT INTO plans (id, name, type, price_cents, credits_per_month) "
        "VALUES (?, 'Pro', 'PRO', 9900, 100)",
        (ids["plan"],),
    )
    connection.execute(
        "INSERT INTO subscriptions (id, billing_account_id, workspace_id, plan_id, "
        "contracted_price_cents, status) VALUES (?, ?, ?, ?, 9900, 'ACTIVE')",
        (ids["subscription"], ids["account"], ids["workspace"], ids["plan"]),
    )
    return ids


def _insert_transaction(
    connection: sqlite3.Connection,
    *,
    workspace_id: str,
    amount: int,
    balance_after: int,
    transaction_type: str,
) -> str:
    """A ledger row whose ``balance_after`` matches the running sum.

    Seeding a consistent balance means a ported insert-validation guard, if the
    coder chooses to port one, cannot be what fails these tests.
    """
    transaction_id = uuid4().hex
    connection.execute(
        "INSERT INTO workspace_credit_transactions "
        "(id, workspace_id, amount, balance_after, type) VALUES (?, ?, ?, ?, ?)",
        (transaction_id, workspace_id, amount, balance_after, transaction_type),
    )
    return transaction_id


def _insert_lot(
    connection: sqlite3.Connection,
    *,
    workspace_id: str,
    grant_transaction_id: str,
    original_amount: int,
    remaining_amount: int,
    expires_at: str | None = None,
) -> str:
    lot_id = uuid4().hex
    connection.execute(
        "INSERT INTO workspace_credit_lots (id, workspace_id, grant_transaction_id, "
        "original_amount, remaining_amount, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            lot_id,
            workspace_id,
            grant_transaction_id,
            original_amount,
            remaining_amount,
            expires_at,
        ),
    )
    return lot_id


def _insert_consumption(
    connection: sqlite3.Connection,
    *,
    workspace_id: str,
    lot_id: str,
    transaction_id: str,
    amount: int,
) -> str:
    consumption_id = uuid4().hex
    connection.execute(
        "INSERT INTO workspace_credit_lot_consumptions "
        "(id, workspace_id, lot_id, transaction_id, amount) VALUES (?, ?, ?, ?, ?)",
        (consumption_id, workspace_id, lot_id, transaction_id, amount),
    )
    return consumption_id


def _seed_credit_ledger(connection: sqlite3.Connection, ids: dict[str, str]) -> dict[str, str]:
    """A grant lot, a debit and one consumption allocation."""
    grant = _insert_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=100,
        balance_after=100,
        transaction_type="TOP_UP",
    )
    debit = _insert_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=-30,
        balance_after=70,
        transaction_type="GENERATION",
    )
    lot = _insert_lot(
        connection,
        workspace_id=ids["workspace"],
        grant_transaction_id=grant,
        original_amount=100,
        remaining_amount=100,
    )
    consumption = _insert_consumption(
        connection,
        workspace_id=ids["workspace"],
        lot_id=lot,
        transaction_id=debit,
        amount=30,
    )
    return {"grant": grant, "debit": debit, "lot": lot, "consumption": consumption}


def _insert_coupon(connection: sqlite3.Connection, *, once_per_workspace: int) -> str:
    """A credit coupon; the type CHECK forbids ``discount_percent`` beside ``credits``."""
    coupon_id = uuid4().hex
    connection.execute(
        "INSERT INTO coupons (id, code, type, credits, once_per_workspace) "
        "VALUES (?, ?, 'CREDIT', 100, ?)",
        (coupon_id, f"C{uuid4().hex[:10].upper()}", once_per_workspace),
    )
    return coupon_id


def _insert_redemption(
    connection: sqlite3.Connection,
    *,
    coupon_id: str,
    user_id: str,
    workspace_id: str,
    order_id: str,
    once_per_workspace: int,
) -> str:
    """A redemption of ``order_id``; the single-target CHECK needs exactly one target."""
    redemption_id = uuid4().hex
    connection.execute(
        "INSERT INTO coupon_redemptions "
        "(id, coupon_id, user_id, workspace_id, order_id, once_per_workspace) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            redemption_id,
            coupon_id,
            user_id,
            workspace_id,
            order_id,
            once_per_workspace,
        ),
    )
    return redemption_id


def _insert_charge(
    connection: sqlite3.Connection, *, billing_account_id: str, status: str = "PAID"
) -> str:
    charge_id = uuid4().hex
    connection.execute(
        "INSERT INTO charges (id, billing_account_id, payment_method, amount_cents, status) "
        "VALUES (?, ?, 'CREDIT_CARD', 1000, ?)",
        (charge_id, billing_account_id, status),
    )
    return charge_id


def _insert_charge_transaction(
    connection: sqlite3.Connection,
    *,
    charge_id: str,
    transaction_id: str,
    external_id: str,
    status: str,
    created_at: str,
) -> None:
    connection.execute(
        "INSERT INTO charge_transactions (id, charge_id, external_id, status, amount_cents, "
        "created_at) VALUES (?, ?, ?, ?, 1000, ?)",
        (transaction_id, charge_id, external_id, status, created_at),
    )


# --- 1. the objects the migration must create -------------------------------


def test_upgrade_creates_every_required_trigger_and_the_charge_view(database: Path) -> None:
    """The guards have to exist in the migrated schema, attached to the right table.

    A trigger on the wrong table, or a missing view, is indistinguishable from "no
    guard at all" for the invariants below, so both the name and ``tbl_name`` are
    asserted here.
    """
    with _connect(database) as connection:
        objects = _storage_objects(connection)

    missing = [
        f"{name} ON {table}"
        for name, table in REQUIRED_TRIGGERS
        if ("trigger", name) not in objects
    ]
    assert not missing, (
        "the T20 migration must create these SQLite triggers: "
        f"{missing}; sqlite_master has {sorted(objects)}"
    )

    wrong_table = [
        f"{name} is ON {objects[('trigger', name)]}, expected {table}"
        for name, table in REQUIRED_TRIGGERS
        if objects[("trigger", name)] != table
    ]
    assert not wrong_table, "triggers attached to the wrong table: " + "; ".join(wrong_table)

    assert ("view", REQUIRED_VIEW) in objects, (
        f"the final modeling declares the view {REQUIRED_VIEW!r} over charges and "
        f"charge_transactions; sqlite_master has {sorted(objects)}"
    )


def test_previous_head_has_none_of_the_ported_guards(pre_t20_database: Path) -> None:
    """The fixtures only prove something if T20 is what introduces the objects."""
    with _connect(pre_t20_database) as connection:
        objects = _storage_objects(connection)

    present = [
        name
        for name, _table in REQUIRED_TRIGGERS
        if ("trigger", name) in objects or ("view", name) in objects
    ]
    assert not present, (
        f"the previous head {PRE_T20_REVISION} already declares {present}; the upgrade test "
        "would not be exercising the T20 migration"
    )
    assert ("view", REQUIRED_VIEW) not in objects, (
        f"{REQUIRED_VIEW} must be created by T20, not before"
    )


# --- 2. credit ledger immutability ------------------------------------------


def test_credit_transaction_update_is_rejected(database: Path) -> None:
    """ADR-019: a correction is a new movement, never an UPDATE."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)
        message = _reject(
            connection,
            "UPDATE workspace_credit_transactions SET amount = amount + 1 WHERE id = ?",
            (ledger["grant"],),
        )
        stored = connection.execute(
            "SELECT amount FROM workspace_credit_transactions WHERE id = ?",
            (ledger["grant"],),
        ).fetchone()

    assert _mentions(message, LEDGER_NEEDLES), (
        "an UPDATE on the append-only Credit Transaction ledger must be refused by a guard "
        f"that names it; got {message!r}"
    )
    assert tuple(stored) == (100,), f"the rejected UPDATE must not change the row; got {stored}"


def test_credit_transaction_delete_is_rejected(database: Path) -> None:
    """Deleting a ledger row erases history that ``balance_after`` depends on."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)
        message = _reject(
            connection,
            "DELETE FROM workspace_credit_transactions WHERE id = ?",
            (ledger["grant"],),
        )
        survivors = connection.execute(
            "SELECT COUNT(*) FROM workspace_credit_transactions WHERE id = ?",
            (ledger["grant"],),
        ).fetchone()[0]

    assert _mentions(message, LEDGER_NEEDLES), (
        "a DELETE on the append-only Credit Transaction ledger must be refused by a guard "
        f"that names it; got {message!r}"
    )
    assert survivors == 1, "the rejected DELETE must leave the ledger row in place"


def test_credit_lot_consumption_update_is_rejected(database: Path) -> None:
    """An allocation ties a debit to a lot; rewriting it breaks the audit trail."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)
        message = _reject(
            connection,
            "UPDATE workspace_credit_lot_consumptions SET amount = amount + 1 WHERE id = ?",
            (ledger["consumption"],),
        )
        stored = connection.execute(
            "SELECT amount FROM workspace_credit_lot_consumptions WHERE id = ?",
            (ledger["consumption"],),
        ).fetchone()

    assert _mentions(message, CONSUMPTION_NEEDLES), (
        "an UPDATE on the immutable lot consumption must be refused by a guard that names "
        f"it; got {message!r}"
    )
    assert tuple(stored) == (30,), f"the rejected UPDATE must not change the row; got {stored}"


def test_credit_lot_consumption_delete_is_rejected(database: Path) -> None:
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)
        message = _reject(
            connection,
            "DELETE FROM workspace_credit_lot_consumptions WHERE id = ?",
            (ledger["consumption"],),
        )
        survivors = connection.execute(
            "SELECT COUNT(*) FROM workspace_credit_lot_consumptions WHERE id = ?",
            (ledger["consumption"],),
        ).fetchone()[0]

    assert _mentions(message, CONSUMPTION_NEEDLES), (
        "a DELETE on the immutable lot consumption must be refused by a guard that names "
        f"it; got {message!r}"
    )
    assert survivors == 1, "the rejected DELETE must leave the consumption row in place"


# --- 3. subscription history is append-only ---------------------------------


def test_subscription_history_update_is_rejected(database: Path) -> None:
    """ADR-019/ADR-030: a plan or status change is a new event, never a rewrite."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        history_id = uuid4().hex
        connection.execute(
            "INSERT INTO subscription_history (id, subscription_id, change_type, reason_text) "
            "VALUES (?, ?, 'CREATE', 'initial')",
            (history_id, ids["subscription"]),
        )
        message = _reject(
            connection,
            "UPDATE subscription_history SET reason_text = 'rewritten' WHERE id = ?",
            (history_id,),
        )
        stored = connection.execute(
            "SELECT reason_text FROM subscription_history WHERE id = ?", (history_id,)
        ).fetchone()

    assert _mentions(message, HISTORY_NEEDLES), (
        "an UPDATE on the append-only subscription history must be refused by a guard that "
        f"names it; got {message!r}"
    )
    assert tuple(stored) == ("initial",), f"the rejected UPDATE must not change the row; {stored}"


def test_subscription_history_delete_is_rejected(database: Path) -> None:
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        history_id = uuid4().hex
        connection.execute(
            "INSERT INTO subscription_history (id, subscription_id, change_type) "
            "VALUES (?, ?, 'CREATE')",
            (history_id, ids["subscription"]),
        )
        message = _reject(
            connection,
            "DELETE FROM subscription_history WHERE id = ?",
            (history_id,),
        )
        survivors = connection.execute(
            "SELECT COUNT(*) FROM subscription_history WHERE id = ?", (history_id,)
        ).fetchone()[0]

    assert _mentions(message, HISTORY_NEEDLES), (
        "a DELETE on the append-only subscription history must be refused by a guard that "
        f"names it; got {message!r}"
    )
    assert survivors == 1, "the rejected DELETE must leave the history row in place"


# --- 4. the credit lot is mutable only in remaining_amount ------------------


def test_credit_lot_delete_is_rejected(database: Path) -> None:
    """A lot is the persisted availability of a grant; deleting it loses the balance."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)
        message = _reject(
            connection,
            "DELETE FROM workspace_credit_lots WHERE id = ?",
            (ledger["lot"],),
        )
        survivors = connection.execute(
            "SELECT COUNT(*) FROM workspace_credit_lots WHERE id = ?", (ledger["lot"],)
        ).fetchone()[0]

    assert _mentions(message, LOT_NEEDLES), (
        f"deleting a Credit Lot must be refused by a guard that names it; got {message!r}"
    )
    assert survivors == 1, "the rejected DELETE must leave the lot in place"


@pytest.mark.parametrize(
    ("column", "value"),
    [
        # 120 keeps `remaining_amount <= original_amount` satisfied, so only a guard
        # can reject it: a CHECK failure would be a different, weaker rule.
        ("original_amount", 120),
        ("grant_transaction_id", None),
    ],
)
def test_credit_lot_identity_columns_are_immutable(
    database: Path, column: str, value: object
) -> None:
    """Only ``remaining_amount``/``updated_at`` may change after the grant."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)
        replacement = uuid4().hex if value is None else value
        message = _reject(
            connection,
            f"UPDATE workspace_credit_lots SET {column} = ? WHERE id = ?",
            (replacement, ledger["lot"]),
        )
        stored = connection.execute(
            f"SELECT {column} FROM workspace_credit_lots WHERE id = ?", (ledger["lot"],)
        ).fetchone()

    assert _mentions(message, LOT_NEEDLES), (
        f"changing workspace_credit_lots.{column} must be refused by the lot guard; got {message!r}"
    )
    assert stored[0] != replacement, (
        f"the rejected UPDATE must not change {column}; got {stored[0]!r}"
    )


def test_credit_lot_workspace_is_immutable(database: Path) -> None:
    """Moving a lot across workspaces would move available credit between tenants."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)
        message = _reject(
            connection,
            "UPDATE workspace_credit_lots SET workspace_id = ? WHERE id = ?",
            (ids["other_workspace"], ledger["lot"]),
        )
        stored = connection.execute(
            "SELECT workspace_id FROM workspace_credit_lots WHERE id = ?", (ledger["lot"],)
        ).fetchone()

    assert _mentions(message, LOT_NEEDLES), (
        "changing workspace_credit_lots.workspace_id must be refused by the lot guard; "
        f"got {message!r}"
    )
    assert stored[0] == ids["workspace"], (
        f"the rejected UPDATE must not move the lot; got {stored[0]!r}"
    )


def test_credit_lot_remaining_amount_can_only_decrease(database: Path) -> None:
    """A consumption reduces the lot; nothing may put credit back into it."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger = _seed_credit_ledger(connection, ids)

        connection.execute(
            "UPDATE workspace_credit_lots SET remaining_amount = 90 WHERE id = ?",
            (ledger["lot"],),
        )
        decreased = connection.execute(
            "SELECT remaining_amount FROM workspace_credit_lots WHERE id = ?",
            (ledger["lot"],),
        ).fetchone()[0]
        assert decreased == 90, (
            "a decrease of remaining_amount is how consumption works and must be allowed; "
            f"got {decreased!r}"
        )

        message = _reject(
            connection,
            "UPDATE workspace_credit_lots SET remaining_amount = 100 WHERE id = ?",
            (ledger["lot"],),
        )
        restored = connection.execute(
            "SELECT remaining_amount FROM workspace_credit_lots WHERE id = ?",
            (ledger["lot"],),
        ).fetchone()[0]

    assert _mentions(message, LOT_NEEDLES), (
        "raising remaining_amount would mint credit out of nothing and must be refused by "
        f"the lot guard; got {message!r}"
    )
    assert restored == 90, f"the rejected UPDATE must not restore the lot; got {restored!r}"


# --- 5. the coupon snapshot -----------------------------------------------


def test_coupon_redemption_snapshot_must_match_the_coupon(database: Path) -> None:
    """The redemption stores the coupon's ``once_per_workspace`` as it was redeemed.

    SQLite cannot assign to ``NEW`` inside a trigger the way the PostgreSQL
    function does, so the port has to refuse a value that disagrees with the
    coupon instead of silently rewriting the row.
    """
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        once_coupon = _insert_coupon(connection, once_per_workspace=1)
        repeatable_coupon = _insert_coupon(connection, once_per_workspace=1)

        message = _reject(
            connection,
            "INSERT INTO coupon_redemptions "
            "(id, coupon_id, user_id, workspace_id, order_id, once_per_workspace) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                uuid4().hex,
                once_coupon,
                ids["user"],
                ids["workspace"],
                ids["order"],
                0,
            ),
        )

        redemption = _insert_redemption(
            connection,
            coupon_id=repeatable_coupon,
            user_id=ids["user"],
            workspace_id=ids["workspace"],
            order_id=ids["order"],
            once_per_workspace=1,
        )
        stored = connection.execute(
            "SELECT once_per_workspace FROM coupon_redemptions WHERE id = ?", (redemption,)
        ).fetchone()[0]

    assert _mentions(message, COUPON_NEEDLES), (
        "a redemption whose once_per_workspace disagrees with the coupon must be refused by "
        f"a snapshot guard that names the column or the table; got {message!r}"
    )
    assert bool(stored) is True, (
        "a matching snapshot must be accepted and stored as redeemed; "
        f"got once_per_workspace={stored!r}"
    )


# --- 6. the view ---------------------------------------------------------


def test_view_returns_the_last_transaction_of_each_charge(database: Path) -> None:
    """``charges_with_last_transaction`` mirrors the dump's LATERAL join.

    A charge with no transaction reads as NULL/NULL; a charge with two reads the
    latest by ``(created_at, id)``, even though the older one was inserted last.
    """
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        without = _insert_charge(connection, billing_account_id=ids["account"])
        with_two = _insert_charge(connection, billing_account_id=ids["account"])
        _insert_charge_transaction(
            connection,
            charge_id=with_two,
            transaction_id=uuid4().hex,
            external_id="ext-newest",
            status="PAID",
            created_at="2026-01-02 00:00:05",
        )
        _insert_charge_transaction(
            connection,
            charge_id=with_two,
            transaction_id=uuid4().hex,
            external_id="ext-oldest",
            status="CAPTURED",
            created_at="2026-01-02 00:00:01",
        )

        rows = connection.execute(
            f"SELECT id, last_transaction_id, last_transaction_status FROM {REQUIRED_VIEW}"
        ).fetchall()

    by_charge = {row[0]: (row[1], row[2]) for row in rows}

    assert by_charge.get(without) == (None, None), (
        "a charge without any charge_transaction must read as NULL, not be filtered out or "
        f"borrow another charge's transaction; got {by_charge.get(without)!r}"
    )
    assert by_charge.get(with_two) == ("ext-newest", "PAID"), (
        "the view must return the latest transaction by (created_at, id), not the physical "
        f"insert order; got {by_charge.get(with_two)!r}"
    )


def test_view_tie_breaks_on_the_transaction_id(database: Path) -> None:
    """The dump orders by ``created_at DESC, id DESC``, so ``id`` decides a tie."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        charge = _insert_charge(connection, billing_account_id=ids["account"])
        low_id, high_id = sorted((uuid4().hex, uuid4().hex))
        # The lower id is inserted last: a rowid-ordered or insertion-ordered view
        # would pick it and pass a weaker assertion.
        _insert_charge_transaction(
            connection,
            charge_id=charge,
            transaction_id=high_id,
            external_id="ext-high",
            status="PAID",
            created_at="2026-01-03 00:00:00",
        )
        _insert_charge_transaction(
            connection,
            charge_id=charge,
            transaction_id=low_id,
            external_id="ext-low",
            status="CAPTURED",
            created_at="2026-01-03 00:00:00",
        )

        row = connection.execute(
            f"SELECT last_transaction_id, last_transaction_status FROM {REQUIRED_VIEW} "
            "WHERE id = ?",
            (charge,),
        ).fetchone()

    assert tuple(row) == ("ext-high", "PAID"), (
        "transactions sharing created_at must be ordered by id DESC, as the dump's "
        f"ORDER BY declares; got {tuple(row)!r}"
    )


# --- 7. the derived credit measures --------------------------------------


class CreditLedgerQueries:
    """Reference implementation of the two derived credit measures of ADR-019.

    This is the seam the credit repository port exposes as ``workspace_balance``
    and ``lot_available(workspace_id, lot_id)``; the semantics below are the
    contract those methods have to match, including treating an expired lot as
    zero availability even though the ledger still records the grant, and
    treating a lot of another Workspace as unavailable.
    """

    def __init__(self, connection: sqlite3.Connection, *, now: str) -> None:
        self.connection = connection
        self.now = now

    def workspace_balance(self, workspace_id: str) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(SUM(remaining_amount), 0) FROM workspace_credit_lots "
            "WHERE workspace_id = ? AND (expires_at IS NULL OR expires_at > ?)",
            (workspace_id, self.now),
        ).fetchone()
        return int(row[0])

    def lot_available(self, workspace_id: str, lot_id: str) -> int:
        row = self.connection.execute(
            "SELECT CASE WHEN expires_at IS NOT NULL AND expires_at <= ? THEN 0 "
            "ELSE remaining_amount END FROM workspace_credit_lots "
            "WHERE id = ? AND workspace_id = ?",
            (self.now, lot_id, workspace_id),
        ).fetchone()
        return int(row[0]) if row is not None else 0


NOW = "2026-06-01 00:00:00"
EXPIRED_AT = "2020-01-01 00:00:00"


def _seed_two_lots(connection: sqlite3.Connection, ids: dict[str, str]) -> dict[str, str]:
    """One active and one expired lot, plus a consumption on the active one."""
    first = _insert_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=100,
        balance_after=100,
        transaction_type="TOP_UP",
    )
    second = _insert_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=100,
        balance_after=200,
        transaction_type="TOP_UP",
    )
    active = _insert_lot(
        connection,
        workspace_id=ids["workspace"],
        grant_transaction_id=first,
        original_amount=100,
        remaining_amount=100,
    )
    expired = _insert_lot(
        connection,
        workspace_id=ids["workspace"],
        grant_transaction_id=second,
        original_amount=100,
        remaining_amount=100,
        expires_at=EXPIRED_AT,
    )
    # 100 -> 30 through the only mutation the lot guard allows.
    connection.execute(
        "UPDATE workspace_credit_lots SET remaining_amount = 30 WHERE id = ?", (active,)
    )
    return {"active": active, "expired": expired}


def test_workspace_balance_ignores_expired_lots(database: Path) -> None:
    """Available credit is ``SUM(remaining_amount)`` of non-expired lots only."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        lots = _seed_two_lots(connection, ids)
        queries = CreditLedgerQueries(connection, now=NOW)

        balance = queries.workspace_balance(ids["workspace"])
        unmetered = connection.execute(
            "SELECT SUM(remaining_amount) FROM workspace_credit_lots WHERE workspace_id = ?",
            (ids["workspace"],),
        ).fetchone()[0]

    assert unmetered == 130, (
        "the fixture must distinguish both measures (30 available against 130 persisted); "
        f"got {unmetered!r}"
    )
    assert balance == 30, (
        "workspace credit availability must ignore the expired lot (100 remaining) and use "
        f"the reduced active lot; got {balance!r}"
    )
    assert lots["active"] != lots["expired"], "the two lots must be distinct"


def test_lot_available_returns_zero_for_an_expired_lot(database: Path) -> None:
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        lots = _seed_two_lots(connection, ids)
        queries = CreditLedgerQueries(connection, now=NOW)

        available = queries.lot_available(ids["workspace"], lots["active"])
        expired = queries.lot_available(ids["workspace"], lots["expired"])
        foreign = queries.lot_available(ids["other_workspace"], lots["active"])

    assert available == 30, f"an active lot reports its remaining_amount (30); got {available!r}"
    assert expired == 0, (
        "an expired lot must report zero availability, even though the ledger still records "
        f"its grant and the row keeps remaining_amount = 100; got {expired!r}"
    )
    assert foreign == 0, (
        "a Credit Lot is tenant scoped: an identifier alone must not read another Workspace's "
        f"availability; got {foreign!r}"
    )


# --- 8. the inventory of the 70 storage objects --------------------------


def _dump_objects() -> tuple[tuple[str, str], ...]:
    objects: tuple[tuple[str, str], ...] = parse_final(
        FINAL_DUMP.read_text(encoding="utf-8")
    ).storage_objects
    return objects


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(cell and set(cell) <= {"-", ":", " "} for cell in cells)


def _markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Every pipe table in the document, as ``(header, rows)``."""
    tables: list[tuple[list[str], list[list[str]]]] = []
    header: list[str] | None = None
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if _is_separator(cells):
                continue
            if header is None:
                header = [cell.lower().strip("`*_ ") for cell in cells]
            else:
                rows.append(cells)
            continue
        if header is not None:
            tables.append((header, rows))
            header = None
            rows = []
    if header is not None:
        tables.append((header, rows))
    return tables


def _column_index(header: list[str], aliases: frozenset[str]) -> int | None:
    for index, name in enumerate(header):
        if any(alias in name for alias in aliases):
            return index
    return None


def _load_matrix() -> list[dict[str, str]]:
    """Parse the inventory into ``{object, classification, reason, test, risk}`` rows.

    Every table that declares all five columns is read, so the inventory may be a
    single table or one table per family without losing a row.
    """
    if not STORAGE_MATRIX.is_file():
        pytest.fail(
            f"{STORAGE_MATRIX} is missing: ADR-030 decision 11 requires a versioned inventory "
            "with one row per storage object of the final modeling and a classification for "
            "each one"
        )

    text = STORAGE_MATRIX.read_text(encoding="utf-8")
    parsed: list[dict[str, str]] = []
    for header, rows in _markdown_tables(text):
        positions = {
            name: _column_index(header, aliases) for name, aliases in MATRIX_COLUMNS.items()
        }
        if any(position is None for position in positions.values()):
            continue
        for cells in rows:
            row = {
                name: (cells[position].strip() if position < len(cells) else "")
                for name, position in positions.items()
                if position is not None
            }
            row["object"] = row["object"].strip("`*_ ")
            parsed.append(row)

    if not parsed:
        pytest.fail(
            f"{STORAGE_MATRIX} has no inventory table with the five columns "
            f"{sorted(MATRIX_COLUMNS)} (Portuguese or English aliases); each object needs its "
            "name, a classification, and a reason, test and risk"
        )
    return parsed


def _classification(cell: str) -> str:
    """Return the ``(a)``..``(d)`` code of a classification cell, or ``""``."""
    match = re.match(r"^\(([a-d])\)\s*(.*)$", cell.strip(), re.IGNORECASE)
    if match is None:
        return ""
    code = match.group(1).lower()
    label = match.group(2).lower()
    if not any(token in label for token in CLASSIFICATION_LABELS[code]):
        return ""
    return code


def test_storage_objects_matrix_lists_every_dump_object_once() -> None:
    """One row per object: the inventory is the evidence `grep -c` counts."""
    expected = {name for _kind, name in _dump_objects()}
    assert len(expected) == 70, (
        "the final modeling declares 70 functions/triggers/views (ADR-030); the dump now has "
        f"{len(expected)}, so the T20 inventory and ADR-030 need a decision"
    )

    rows = _load_matrix()
    names = [row["object"] for row in rows]

    duplicates = sorted({name for name in names if names.count(name) > 1})
    missing = sorted(expected - set(names))
    extra = sorted(set(names) - expected)

    assert not duplicates, f"the inventory repeats these objects: {duplicates}"
    assert not missing, (
        f"these dump objects have no row in the inventory, so they are unclassified: {missing}"
    )
    assert not extra, (
        "the inventory names objects the dump does not declare (or spells them differently): "
        f"{extra}"
    )
    assert len(rows) == len(expected), (
        f"the inventory must have exactly one row per dump object ({len(expected)}); "
        f"got {len(rows)}"
    )


def test_storage_objects_matrix_classifies_and_justifies_every_object() -> None:
    """No object may be left without ``(a)``..``(d)``, a reason, a test and a risk."""
    problems: list[str] = []
    for row in _load_matrix():
        name = row["object"]
        code = _classification(row["classification"])
        if not code:
            problems.append(
                f"{name}: classification {row['classification']!r} is not one of "
                "(a) trigger SQLite, (b) application guard, (c) repository/query, "
                "(d) out of scope"
            )
        for column in ("reason", "test", "risk"):
            value = row[column].strip()
            if not value or value in {"-", "—", "n/a", "N/A"}:
                problems.append(f"{name}: {column} is empty")

    assert not problems, "the inventory has unclassified or unjustified objects:\n" + "\n".join(
        problems
    )


def test_storage_objects_matrix_does_not_downgrade_the_ledger_invariants() -> None:
    """ADR-030: the ledger, the lot, the coupon and the history may not be (d)."""
    rows = {row["object"]: row for row in _load_matrix()}
    problems = [
        f"{object_name}: classified {rows[object_name]['classification']!r}, expected one of "
        f"{sorted(accepted)}"
        for object_name, accepted in MUST_BE_ENFORCED.items()
        if object_name in rows
        and _classification(rows[object_name]["classification"]) not in accepted
    ]
    assert not problems, (
        "these invariants must be carried by a ported guard or an equivalent query; "
        "declaring them out of scope is forbidden:\n" + "\n".join(problems)
    )


# --- 9. INSERT OR REPLACE must not bypass the guards -------------------------
#
# SQLite fires the BEFORE DELETE trigger of an ``INSERT OR REPLACE`` only when
# ``recursive_triggers`` is ON. With the default (off) the conflicting row is
# removed to make room for the new one *without* invoking the guard, so every
# append-only table can be rewritten through the very constraint that protects it.
# ``sqlite3`` leaves the pragma off and ``creator.infrastructure.database.db`` did
# not set it either, which makes the guards bypassable from the application engine
# even though the trigger bodies are correct.

REPLACE_NEEDLES: Final[dict[str, tuple[str, ...]]] = {
    "workspace_credit_transactions": LEDGER_NEEDLES,
    "workspace_credit_lot_consumptions": CONSUMPTION_NEEDLES,
    "subscription_history": HISTORY_NEEDLES,
    "workspace_credit_lots": LOT_NEEDLES,
}


def _replace_attempt(
    table: str, ids: dict[str, str], ledger: dict[str, str], history_id: str
) -> tuple[str, tuple[object, ...]]:
    """An ``INSERT OR REPLACE`` that collides with the row seeded for ``table``.

    The ledger case targets ``ledger["spare"]``, a TOP_UP row no Credit Lot and no
    allocation points at. Replacing a *referenced* grant would fail on the
    ``ON DELETE RESTRICT`` foreign key instead of on the immutability guard, and the
    test would pass for the wrong reason.
    """
    if table == "workspace_credit_transactions":
        return (
            "INSERT OR REPLACE INTO workspace_credit_transactions "
            "(id, workspace_id, amount, balance_after, type) VALUES (?, ?, 100, 100, 'TOP_UP')",
            (ledger["spare"], ids["workspace"]),
        )
    if table == "workspace_credit_lot_consumptions":
        return (
            "INSERT OR REPLACE INTO workspace_credit_lot_consumptions "
            "(id, workspace_id, lot_id, transaction_id, amount) VALUES (?, ?, ?, ?, 30)",
            (ledger["consumption"], ids["workspace"], ledger["lot"], ledger["debit"]),
        )
    if table == "subscription_history":
        return (
            "INSERT OR REPLACE INTO subscription_history "
            "(id, subscription_id, change_type) VALUES (?, ?, 'CREATE')",
            (history_id, ids["subscription"]),
        )
    if table == "workspace_credit_lots":
        return (
            "INSERT OR REPLACE INTO workspace_credit_lots "
            "(id, workspace_id, grant_transaction_id, original_amount, remaining_amount) "
            "VALUES (?, ?, ?, 50, 50)",
            (ledger["spare_lot"], ids["workspace"], ledger["spare_lot_grant"]),
        )
    raise AssertionError(f"no INSERT OR REPLACE fixture for {table}")


def _insert_spare_grant(connection: sqlite3.Connection, ids: dict[str, str]) -> str:
    """A TOP_UP row nothing else references, so only a guard can refuse a REPLACE.

    Replacing a grant that a Credit Lot points at would fail on ``ON DELETE
    RESTRICT``, which is a different (weaker) rule than the immutability guard.
    """
    return _insert_transaction(
        connection,
        workspace_id=ids["workspace"],
        amount=50,
        balance_after=150,
        transaction_type="TOP_UP",
    )


def _seed_replace_targets(
    connection: sqlite3.Connection, ids: dict[str, str]
) -> tuple[dict[str, str], str]:
    """The credit graph plus the rows an `INSERT OR REPLACE` will collide with.

    Every target is childless on purpose: a row that another table references would
    be refused by ``ON DELETE RESTRICT`` before any guard is reached, and the test
    would pass without proving anything.
    """
    ledger = _seed_credit_ledger(connection, ids)
    ledger["spare"] = _insert_spare_grant(connection, ids)
    # A second grant that owns exactly one child (the lot below), so the lot itself is
    # childless and the ledger row stays childless: each REPLACE target is isolated.
    lot_grant = _insert_spare_grant(connection, ids)
    ledger["spare_lot_grant"] = lot_grant
    ledger["spare_lot"] = _insert_lot(
        connection,
        workspace_id=ids["workspace"],
        grant_transaction_id=lot_grant,
        original_amount=50,
        remaining_amount=50,
    )
    history_id = uuid4().hex
    connection.execute(
        "INSERT INTO subscription_history (id, subscription_id, change_type) "
        "VALUES (?, ?, 'CREATE')",
        (history_id, ids["subscription"]),
    )
    return ledger, history_id


@pytest.mark.parametrize("table", sorted(REPLACE_NEEDLES))
def test_insert_or_replace_cannot_replace_an_immutable_row(database: Path, table: str) -> None:
    """The DELETE guard must fire for the implicit delete of a REPLACE."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger, history_id = _seed_replace_targets(connection, ids)

        statement, parameters = _replace_attempt(table, ids, ledger, history_id)
        row_id = str(parameters[0])

        connection.execute("PRAGMA recursive_triggers=ON")
        assert connection.execute("PRAGMA recursive_triggers").fetchone()[0] == 1, (
            "the fixture could not enable recursive_triggers, so the REPLACE bypass is not "
            "being exercised"
        )

        message = _reject(connection, statement, parameters)
        survivors = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE id = ?", (row_id,)
        ).fetchone()[0]

    assert _mentions(message, REPLACE_NEEDLES[table]), (
        f"INSERT OR REPLACE on {table} must be refused by the immutability guard that names "
        f"it; got {message!r}"
    )
    assert survivors == 1, (
        f"INSERT OR REPLACE deleted the {table} row instead of being refused; an append-only "
        "row must survive a REPLACE"
    )


@pytest.mark.parametrize("table", sorted(REPLACE_NEEDLES))
def test_app_engine_refuses_insert_or_replace_on_immutable_tables(
    database: Path, table: str
) -> None:
    """The bypass must be closed for the engine the application really uses.

    Two implementations are acceptable and this test accepts either: a ``BEFORE
    INSERT`` guard that refuses an identifier the table already holds, or
    ``PRAGMA recursive_triggers=ON`` (in ``creator.infrastructure.database.db``) so
    the existing ``BEFORE DELETE`` guard fires for the implicit delete. What may not
    happen is the REPLACE succeeding: with the pragma off and no insert guard, SQLite
    removes the immutable row and writes the replacement without running any guard.
    """
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        ledger, history_id = _seed_replace_targets(connection, ids)
        statement, parameters = _replace_attempt(table, ids, ledger, history_id)
        row_id = str(parameters[0])

    engine = create_database_engine(f"sqlite+pysqlite:///{database}")
    try:
        with engine.connect() as connection:
            pragma = int(connection.exec_driver_sql("PRAGMA recursive_triggers").scalar_one() or 0)
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql(statement, parameters)
        except sa.exc.IntegrityError as error:
            message = str(error)
        else:
            pytest.fail(
                "the application engine rewrote an immutable row with INSERT OR REPLACE "
                f"(PRAGMA recursive_triggers={pragma} and no BEFORE INSERT guard refused it): "
                f"SQLite deleted the {table} row and inserted the replacement, so the guard "
                "was bypassed. Either enable recursive_triggers in "
                "creator.infrastructure.database.db or add a BEFORE INSERT guard that refuses "
                f"an identifier the table already holds. Table under test: {table}"
            )
    finally:
        engine.dispose()

    with _connect(database) as connection:
        survivors = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE id = ?", (row_id,)
        ).fetchone()[0]

    assert "foreign key" not in message.lower(), (
        "the fixture hit the ON DELETE RESTRICT of a referenced grant instead of the "
        f"immutability guard, so this test would not prove the bypass: {message}"
    )
    assert _mentions(message, REPLACE_NEEDLES[table]), (
        f"INSERT OR REPLACE on {table} through the application engine must be refused by a "
        f"guard that names it; got {message!r}"
    )
    assert survivors == 1, (
        f"INSERT OR REPLACE through the application engine deleted the {table} row instead of "
        "being refused; an append-only row must survive a REPLACE"
    )


# --- 10. a Credit Lot is born from an integral positive grant ---------------
#
# The dump keeps ``m1_validate_credit_lot``: the grant transaction must exist in
# the same Workspace, be positive, and match ``original_amount``; a fresh lot has
# ``remaining_amount = original_amount``. Nothing enforced that in SQLite, so a
# lot could be created with no grant at all, or with amounts that do not match the
# transaction it claims to come from.

GRANT_NONE: Final[str] = "none"
GRANT_BASE: Final[str] = "base"
GRANT_DEBIT: Final[str] = "debit"


@pytest.mark.parametrize(
    ("case", "grant", "original_amount", "remaining_amount", "needles"),
    [
        ("a lot without a grant transaction", GRANT_NONE, 100, 100, ()),
        ("a lot from a non-positive grant", GRANT_DEBIT, 30, 30, LOT_NEEDLES),
        ("original_amount that differs from the grant", GRANT_BASE, 70, 70, LOT_NEEDLES),
        ("remaining_amount that differs from the original", GRANT_BASE, 100, 60, LOT_NEEDLES),
    ],
)
def test_credit_lot_insert_requires_an_integral_positive_grant(
    database: Path,
    case: str,
    grant: str,
    original_amount: int,
    remaining_amount: int,
    needles: tuple[str, ...],
) -> None:
    """``m1_validate_credit_lot``: no lot may outlive the grant it claims."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        base_grant = _insert_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=100,
            balance_after=100,
            transaction_type="TOP_UP",
        )
        debit = _insert_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=-30,
            balance_after=70,
            transaction_type="GENERATION",
        )
        grant_transaction_id = {GRANT_NONE: None, GRANT_BASE: base_grant, GRANT_DEBIT: debit}[grant]

        message = _reject(
            connection,
            "INSERT INTO workspace_credit_lots (id, workspace_id, grant_transaction_id, "
            "original_amount, remaining_amount) VALUES (?, ?, ?, ?, ?)",
            (
                uuid4().hex,
                ids["workspace"],
                grant_transaction_id,
                original_amount,
                remaining_amount,
            ),
        )
        stored = connection.execute("SELECT COUNT(*) FROM workspace_credit_lots").fetchone()[0]

    assert stored == 0, f"{case} must not be persisted; the table has {stored} row(s)"
    if needles:
        assert _mentions(message, needles), (
            f"{case} must be refused by a ported lot guard that names the lot or its grant, "
            f"not by an unrelated constraint; got {message!r}"
        )


def test_credit_lot_insert_accepts_the_integral_grant(database: Path) -> None:
    """The guard must not reject the legitimate shape of a grant."""
    with _connect(database) as connection:
        ids = _seed_billing_graph(connection)
        grant = _insert_transaction(
            connection,
            workspace_id=ids["workspace"],
            amount=100,
            balance_after=100,
            transaction_type="TOP_UP",
        )
        lot = _insert_lot(
            connection,
            workspace_id=ids["workspace"],
            grant_transaction_id=grant,
            original_amount=100,
            remaining_amount=100,
        )
        stored = connection.execute(
            "SELECT original_amount, remaining_amount FROM workspace_credit_lots WHERE id = ?",
            (lot,),
        ).fetchone()

    assert tuple(stored) == (100, 100), (
        f"a lot that matches its grant must be accepted unchanged; got {tuple(stored)!r}"
    )


# --- 11. the coupon snapshot comes from the coupon, never from the client ---
#
# ``coupon_redemptions_set_once`` copies ``coupons.once_per_workspace`` into the
# redemption. SQLite cannot assign ``NEW`` inside a trigger, so the port refuses a
# row whose snapshot disagrees instead of rewriting it -- which means the writer
# has to derive the value. ``CouponRedemptionCreateRequest`` has no such field, so
# the derivation belongs to ``SqlAlchemyCouponRedemptionRepository.add``.


@contextlib.contextmanager
def _session(database: Path) -> Iterator[Session]:
    """ORM session on a migrated database copy."""
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    try:
        with Session(engine, expire_on_commit=False) as session:
            yield session
    finally:
        engine.dispose()


def _seed_coupon_graph(session: Session, *, once_per_workspace: bool) -> dict[str, UUID]:
    """User, workspace, billing account, order and one CREDIT coupon."""
    user = User(id=uuid4(), display_name="Coupon Snapshot")
    workspace = Workspace(id=uuid4(), name="Coupon Snapshot WS")
    session.add_all([user, workspace])
    session.flush()

    account = BillingAccount(
        id=uuid4(),
        user_id=user.id,
        payer_type="INDIVIDUAL",
        name="Coupon Snapshot",
        email=f"{uuid4()}@example.com",
    )
    session.add(account)
    session.flush()

    order = Order(
        id=uuid4(),
        billing_account_id=account.id,
        workspace_id=workspace.id,
        subtotal_cents=1000,
        amount_cents=1000,
        status="PAID",
    )
    coupon = Coupon(
        id=uuid4(),
        code=f"C{uuid4().hex[:10].upper()}",
        type="CREDIT",
        credits=100,
        once_per_workspace=once_per_workspace,
    )
    session.add_all([order, coupon])
    session.flush()

    return {
        "user": user.id,
        "workspace": workspace.id,
        "account": account.id,
        "order": order.id,
        "coupon": coupon.id,
    }


def test_coupon_redemption_derives_once_per_workspace_from_the_coupon(database: Path) -> None:
    """A once-per-workspace coupon must store ``true`` without the client sending it."""
    with _session(database) as session:
        ids = _seed_coupon_graph(session, once_per_workspace=True)
        repository = SqlAlchemyCouponRedemptionRepository(session)
        try:
            record = repository.add(
                fields={
                    "coupon_id": ids["coupon"],
                    "billing_account_id": ids["account"],
                    "order_id": ids["order"],
                    "credits_applied": 100,
                }
            )
        except sa.exc.IntegrityError as error:
            session.rollback()
            pytest.fail(
                "SqlAlchemyCouponRedemptionRepository.add must copy "
                "coupons.once_per_workspace into the redemption before the INSERT: the client "
                "payload (CouponRedemptionCreateRequest) has no such field, so the row falls "
                "back to DEFAULT false and the snapshot trigger refuses it. Expected "
                "`once_per_workspace=1` for this coupon. Driver said: "
                f"{error.orig}"
            )

        stored = session.execute(
            sa.text("SELECT once_per_workspace FROM coupon_redemptions WHERE id = :id"),
            {"id": record.id.hex},
        ).scalar_one()

    assert record.status == "APPLIED", f"the redemption must be applied, got {record.status!r}"
    assert bool(stored) is True, (
        "the redemption of a once-per-workspace coupon must store once_per_workspace = true; "
        f"got {stored!r}"
    )


def test_coupon_redemption_stores_false_for_a_repeatable_coupon(database: Path) -> None:
    """The derivation must not hard-code ``true``: a repeatable coupon stays repeatable."""
    with _session(database) as session:
        ids = _seed_coupon_graph(session, once_per_workspace=False)
        repository = SqlAlchemyCouponRedemptionRepository(session)
        record = repository.add(
            fields={
                "coupon_id": ids["coupon"],
                "billing_account_id": ids["account"],
                "order_id": ids["order"],
                "credits_applied": 100,
            }
        )
        stored = session.execute(
            sa.text("SELECT once_per_workspace FROM coupon_redemptions WHERE id = :id"),
            {"id": record.id.hex},
        ).scalar_one()

    assert bool(stored) is False, (
        f"a repeatable coupon must store once_per_workspace = false; got {stored!r}"
    )


def test_coupon_redemption_payload_cannot_supply_once_per_workspace() -> None:
    """The snapshot is server-derived; accepting it from the client would defeat it."""
    fields = set(CouponRedemptionCreateRequest.model_fields)
    assert "once_per_workspace" not in fields, (
        "CouponRedemptionCreateRequest must not accept once_per_workspace: the value is a "
        f"snapshot of the coupon, derived by the repository; got {sorted(fields)}"
    )


# --- 12. updated_at is the application-side replacement for 50 triggers ----
#
# ``set_updated_at`` and the 49 ``trg_updated_at_*`` triggers of the dump are not
# ported: every mutable model declares ``onupdate=func.now()``, and the rule is
# carried by the ORM. That is an ``(b) application guard`` with an equivalent
# test, not an object that may be declared ``(d) out of scope``.


def test_orm_onupdate_advances_updated_at(database: Path) -> None:
    """A representative mutable model must bump ``updated_at`` on UPDATE."""
    with _session(database) as session:
        coupon = Coupon(
            id=uuid4(),
            code=f"T{uuid4().hex[:10].upper()}",
            type="CREDIT",
            credits=10,
            once_per_workspace=False,
        )
        session.add(coupon)
        session.flush()
        session.execute(
            sa.text("UPDATE coupons SET updated_at = '2020-01-01 00:00:00' WHERE id = :id"),
            {"id": coupon.id.hex},
        )
        session.expire_all()

        stale_row = session.get(Coupon, coupon.id)
        assert stale_row is not None, "the seeded coupon disappeared"
        stale = stale_row.updated_at
        assert stale.year == 2020, f"the fixture must start from a stale updated_at, got {stale!r}"

        stale_row.internal_note = "touched through the ORM"
        session.flush()
        session.expire_all()

        fresh_row = session.get(Coupon, coupon.id)
        assert fresh_row is not None, "the updated coupon disappeared"

    assert fresh_row.updated_at > stale, (
        "the ORM onupdate is the application-side replacement for set_updated_at and the 49 "
        f"trg_updated_at_* triggers; updated_at did not advance: {stale!r} -> "
        f"{fresh_row.updated_at!r}"
    )


def test_storage_objects_matrix_classifies_updated_at_as_an_application_guard() -> None:
    """The 50 ``updated_at`` objects must be ``(b)``, never ``(d)``."""
    family = sorted(
        name
        for kind, name in _dump_objects()
        if name == "set_updated_at" or (kind == "TRIGGER" and name.startswith("trg_updated_at_"))
    )
    assert len(family) == 50, (
        f"the dump declares set_updated_at plus 49 trg_updated_at_* triggers; got {len(family)}: "
        f"{family}"
    )

    rows = {row["object"]: row for row in _load_matrix()}
    missing = [name for name in family if name not in rows]
    assert not missing, f"the inventory does not classify the updated_at family: {missing}"

    problems = [
        f"{name}: classified {rows[name]['classification']!r}, expected (b) application guard "
        "(the metadata onupdate carries the rule and tests/test_storage_objects.py proves it)"
        for name in family
        if _classification(rows[name]["classification"]) != "b"
    ]
    assert not problems, "the updated_at family is not classified as an application guard:\n" + (
        "\n".join(problems)
    )


# --- 13. the view behind a charge repository seam -------------------------


CHARGE_VIEW_METHOD: Final[str] = "get_with_last_transaction_for_user"
_UNSET: Final[object] = object()


def _record_field(record: object, name: str) -> object:
    if isinstance(record, Mapping):
        return record.get(name, _UNSET)
    return getattr(record, name, _UNSET)


def _seed_charge_view_graph(session: Session) -> dict[str, UUID]:
    """Two charges: one with two transactions, one with none."""
    user = User(id=uuid4(), display_name="Charge View")
    session.add(user)
    session.flush()
    account = BillingAccount(
        id=uuid4(),
        user_id=user.id,
        payer_type="INDIVIDUAL",
        name="Charge View",
        email=f"{uuid4()}@example.com",
    )
    session.add(account)
    session.flush()

    with_two = Charge(
        id=uuid4(),
        billing_account_id=account.id,
        payment_method="CREDIT_CARD",
        amount_cents=1000,
        currency="BRL",
        status="PAID",
    )
    without = Charge(
        id=uuid4(),
        billing_account_id=account.id,
        payment_method="CREDIT_CARD",
        amount_cents=2000,
        currency="BRL",
        status="PENDING",
    )
    session.add_all([with_two, without])
    session.flush()

    # Inserted out of chronological order on purpose: the view must order by
    # (created_at, id), not by the physical row.
    session.add_all(
        [
            ChargeTransaction(
                id=uuid4(),
                charge_id=with_two.id,
                provider="PAGARME",
                status="PAID",
                amount_cents=1000,
                external_id="ext-newest",
                created_at=datetime(2026, 1, 2, 0, 0, 5, tzinfo=UTC),
            ),
            ChargeTransaction(
                id=uuid4(),
                charge_id=with_two.id,
                provider="PAGARME",
                status="CAPTURED",
                amount_cents=1000,
                external_id="ext-oldest",
                created_at=datetime(2026, 1, 2, 0, 0, 1, tzinfo=UTC),
            ),
        ]
    )
    session.flush()

    return {
        "user": user.id,
        "account": account.id,
        "with_two": with_two.id,
        "without": without.id,
    }


def test_charge_repository_reads_the_last_transaction_view(database: Path) -> None:
    """``charges_with_last_transaction`` must be reachable through the port.

    Expected seam::

        SqlAlchemyChargeRepository.get_with_last_transaction_for_user(
            *, user_id: UUID, charge_id: UUID
        ) -> <record exposing last_transaction_id and last_transaction_status>

    ``None`` for a charge of another tenant, and ``None``/``None`` fields for a
    charge without transactions, mirroring ``get_for_user`` and the view.
    """
    with _session(database) as session:
        repository = SqlAlchemyChargeRepository(session)
        method = getattr(repository, CHARGE_VIEW_METHOD, None)
        if method is None:
            pytest.fail(
                "the T20 view has no repository seam: expected "
                "SqlAlchemyChargeRepository.get_with_last_transaction_for_user("
                "*, user_id: UUID, charge_id: UUID) reading "
                "charges_with_last_transaction and returning last_transaction_id / "
                f"last_transaction_status; {type(repository).__name__} has no "
                f"{CHARGE_VIEW_METHOD}. The view is ported and tested, but no caller can read it."
            )

        ids = _seed_charge_view_graph(session)
        with_two = method(user_id=ids["user"], charge_id=ids["with_two"])
        without = method(user_id=ids["user"], charge_id=ids["without"])
        foreign = method(user_id=uuid4(), charge_id=ids["with_two"])

    assert with_two is not None, "the seeded charge must be readable by its owner"
    assert _record_field(with_two, "last_transaction_id") == "ext-newest", (
        "the seam must read the latest transaction by (created_at, id), not the physical "
        f"insert order; got {with_two!r}"
    )
    assert _record_field(with_two, "last_transaction_status") == "PAID", (
        f"the seam must expose last_transaction_status; got {with_two!r}"
    )
    assert without is not None, "a charge without transactions must still be readable"
    assert _record_field(without, "last_transaction_id") is None, (
        f"a charge without a transaction must read NULL, not borrow another one; got {without!r}"
    )
    assert _record_field(without, "last_transaction_status") is None, (
        f"a charge without a transaction must read NULL status; got {without!r}"
    )
    assert foreign is None, (
        "the seam must be tenant scoped, like get_for_user: a charge of another user must not "
        f"be readable; got {foreign!r}"
    )
