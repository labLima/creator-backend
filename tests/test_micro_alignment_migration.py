"""Data-safety and schema tests for the T27 micro-divergences (issue #170).

The final modeling declares nine small divergences that the previous revisions left
behind. They are the nine items the parity gap still reports for these five tables:

- ``provider_webhook_events.updated_at`` is missing (``column_missing``);
- ``orders.discount_cents`` is nullable and has no default (``nullability`` and
  ``default_missing``);
- ``provider_idempotency_keys.provider`` lacks the ``'PAGARME'`` server default
  (``default_missing``);
- ``provider_webhook_events.status`` lacks the ``'RECEIVED'`` server default
  (``default_missing``);
- ``image_resizes`` keeps the old index names (``index_name`` twice);
- ``coupon_redemptions`` keeps a simple ``workspace_id -> workspaces`` foreign key
  (``fk_extra``) and does not link ``credit_transaction_id`` to
  ``workspace_credit_transactions`` (``fk_missing``).

Each test builds a database from the committed previous schema
(``tests/contracts/schema_prev_ddl.sql``), stamps the historical revision, upgrades to
``0032_coupon_redemption`` and only then writes the rows the new revision has to
normalise. The upgrade under test runs afterwards, exactly like a real database, so a
migration that silently loses rows or forgets the backfill fails here.

The security section is separate from the parity arithmetic: the new
``coupon_redemptions.credit_transaction_id`` foreign key is created while Alembic runs
with ``PRAGMA foreign_keys=OFF``, so a pre-existing dangling reference is accepted by
SQLite and never surfaces again on insert or update. ``PRAGMA foreign_key_check`` is
used to prove the upgraded database is reference-clean, and a seeded dangling value
must be neutralised by the migration.
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
# Last revision of the chain before the T27 alignment: the schema under test starts here.
LEGACY_REVISION = "0032_coupon_redemption"


# --- historical database setup ----------------------------------------------


def _upgrade(database: Path, revision: str) -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database}")
    command.upgrade(config, revision)


def _downgrade(database: Path, revision: str) -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{database}")
    command.downgrade(config, revision)


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
    """Schema at ``0032_coupon_redemption``, built once and copied per test."""
    directory = Path(tempfile.mkdtemp(prefix=".creator-pytest-micro-", dir=Path.cwd()))
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
    target = tmp_path / "micro_alignment.db"
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


def _columns(connection: sa.Connection, table: str) -> dict[str, dict[str, Any]]:
    rows = connection.exec_driver_sql(f'PRAGMA table_info("{table}")').fetchall()
    return {row[1]: {"type": row[2], "notnull": bool(row[3]), "default": row[4]} for row in rows}


def _indexes(connection: sa.Connection, table: str) -> dict[str, dict[str, Any]]:
    indexes: dict[str, dict[str, Any]] = {}
    for row in connection.exec_driver_sql(f'PRAGMA index_list("{table}")').fetchall():
        name = row[1]
        columns = [
            info[2]
            for info in connection.exec_driver_sql(f'PRAGMA index_info("{name}")').fetchall()
        ]
        indexes[name] = {"unique": bool(row[2]), "columns": columns}
    return indexes


def _foreign_keys(connection: sa.Connection, table: str) -> list[dict[str, Any]]:
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


def _default(value: Any) -> str:
    """SQLite keeps the literal in ``dflt_value``, quotes included."""
    return "" if value is None else str(value).strip().strip("'\"")


def _stamp(value: Any) -> str:
    """Compare timestamps at second precision: the stored text may keep microseconds."""
    return "" if value is None else str(value)[:19]


def _server_default(column: sa.Column[Any]) -> str:
    default = column.server_default
    assert default is not None, f"{column.table.name}.{column.name} has no server default"
    return str(default.arg).strip().strip("'\"")


# --- row seeds --------------------------------------------------------------


def _seed_orders(connection: sa.Connection) -> dict[str, str]:
    """Minimal user/workspace/billing_account plus one order with a NULL discount."""
    ids = {
        "user": uuid4().hex,
        "workspace": uuid4().hex,
        "account": uuid4().hex,
        "order": uuid4().hex,
        "discounted_order": uuid4().hex,
    }
    connection.execute(
        sa.text("INSERT INTO users (id, email, display_name) VALUES (:id, :email, :name)"),
        {"id": ids["user"], "email": f"{ids['user']}@example.com", "name": "Micro Alignment"},
    )
    connection.execute(
        sa.text("INSERT INTO workspaces (id, name) VALUES (:id, :name)"),
        {"id": ids["workspace"], "name": "Micro Workspace"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO billing_accounts (id, user_id, payer_type, name, email) "
            "VALUES (:id, :user, 'INDIVIDUAL', 'Micro', :email)"
        ),
        {"id": ids["account"], "user": ids["user"], "email": f"{ids['account']}@example.com"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
            "discount_cents, amount_cents, status) "
            "VALUES (:id, :account, :workspace, 1000, NULL, 1000, 'PAID')"
        ),
        {"id": ids["order"], "account": ids["account"], "workspace": ids["workspace"]},
    )
    connection.execute(
        sa.text(
            "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
            "discount_cents, amount_cents, status) "
            "VALUES (:id, :account, :workspace, 1000, 250, 750, 'PAID')"
        ),
        {"id": ids["discounted_order"], "account": ids["account"], "workspace": ids["workspace"]},
    )
    return ids


def _insert_order(
    connection: sa.Connection,
    ids: dict[str, str],
    *,
    subtotal_cents: int,
    amount_cents: int,
    discount_cents: int | None,
) -> str:
    """One order of the seeded billing graph, so several backfill branches coexist."""
    order_id = uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
            "discount_cents, amount_cents, status) "
            "VALUES (:id, :account, :workspace, :subtotal, :discount, :amount, 'PAID')"
        ),
        {
            "id": order_id,
            "account": ids["account"],
            "workspace": ids["workspace"],
            "subtotal": subtotal_cents,
            "discount": discount_cents,
            "amount": amount_cents,
        },
    )
    return order_id


def _order_amounts(connection: sa.Connection, order_id: str) -> tuple[Any, ...]:
    """No coercion: a leftover NULL discount must show up in the assertion message."""
    row = connection.execute(
        sa.text("SELECT subtotal_cents, discount_cents, amount_cents FROM orders WHERE id = :id"),
        {"id": order_id},
    ).one()
    return tuple(row)


def _insert_redemption(
    connection: sa.Connection,
    ids: dict[str, str],
    *,
    coupon_code: str,
    credit_transaction_id: str | None,
) -> str:
    """A redemption of the seeded order, optionally pointing at a credit transaction."""
    coupon_id, redemption_id = uuid4().hex, uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO coupons (id, code, type, discount_percent) "
            "VALUES (:id, :code, 'DISCOUNT', 10)"
        ),
        {"id": coupon_id, "code": coupon_code},
    )
    connection.execute(
        sa.text(
            "INSERT INTO coupon_redemptions "
            "(id, coupon_id, user_id, workspace_id, order_id, credit_transaction_id) "
            "VALUES (:id, :coupon, :user, :workspace, :order, :transaction)"
        ),
        {
            "id": redemption_id,
            "coupon": coupon_id,
            "user": ids["user"],
            "workspace": ids["workspace"],
            "order": ids["order"],
            "transaction": credit_transaction_id,
        },
    )
    return redemption_id


def _insert_webhook_event(
    connection: sa.Connection,
    *,
    external_id: str,
    received_at: str,
    processed_at: str | None,
) -> str:
    event_id = uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO provider_webhook_events "
            "(id, provider, external_id, dedupe_key, event_type, payload, status, "
            "received_at, processed_at) "
            "VALUES (:id, 'PAGARME', :external_id, :dedupe_key, 'order.paid', '{}', "
            "'PROCESSED', :received_at, :processed_at)"
        ),
        {
            "id": event_id,
            "external_id": external_id,
            "dedupe_key": f"dedupe_{external_id}",
            "received_at": received_at,
            "processed_at": processed_at,
        },
    )
    return event_id


# --- 1. provider_webhook_events.updated_at ----------------------------------


def test_provider_webhook_events_gains_updated_at_backfilled_from_processed_at(
    database: Path,
) -> None:
    processed = "2026-01-02 03:04:05"
    received = "2026-01-01 00:00:00"
    pending_received = "2026-01-05 06:07:08"
    with _connect(database) as connection:
        _insert_webhook_event(
            connection, external_id="evt_processed", received_at=received, processed_at=processed
        )
        _insert_webhook_event(
            connection,
            external_id="evt_unprocessed",
            received_at=pending_received,
            processed_at=None,
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        columns = _columns(connection, "provider_webhook_events")
        assert "updated_at" in columns, (
            "provider_webhook_events.updated_at is missing; the final modeling declares it NOT NULL"
        )
        assert columns["updated_at"]["notnull"] is True, (
            "provider_webhook_events.updated_at must be NOT NULL"
        )
        assert columns["updated_at"]["default"] is not None, (
            "provider_webhook_events.updated_at needs a server default, like every other "
            "table's updated_at"
        )

        backfilled = connection.execute(
            sa.text("SELECT updated_at FROM provider_webhook_events WHERE external_id = :key"),
            {"key": "evt_processed"},
        ).scalar_one()
        assert _stamp(backfilled) == processed, (
            "the backfill must prefer processed_at for an already processed event; "
            f"got {backfilled!r}"
        )

        pending = connection.execute(
            sa.text("SELECT updated_at FROM provider_webhook_events WHERE external_id = :key"),
            {"key": "evt_unprocessed"},
        ).scalar_one()
        assert _stamp(pending) == pending_received, (
            "an event without processed_at must fall back to received_at, not to the "
            f"migration clock; got {pending!r} expected {pending_received!r}"
        )

    # A row inserted after the upgrade must get the server default.
    with _connect(database) as connection:
        fresh = _insert_webhook_event(
            connection,
            external_id="evt_fresh",
            received_at="2026-02-01 00:00:00",
            processed_at=None,
        )
        updated_at = connection.execute(
            sa.text("SELECT updated_at FROM provider_webhook_events WHERE id = :id"),
            {"id": fresh},
        ).scalar_one()
        assert _stamp(updated_at), "the server default must fill updated_at on insert"

        # Rebuilding the table for a new NOT NULL column must not drop the other indexes.
        indexes = _indexes(connection, "provider_webhook_events")
        for name in (
            "uq_provider_webhook_events_provider_external_id",
            "ix_provider_webhook_events_event_type",
            "ix_provider_webhook_events_resource_id",
            "ix_provider_webhook_events_status_received_at",
        ):
            assert name in indexes, (
                f"{name} disappeared while rebuilding provider_webhook_events; got "
                f"{sorted(indexes)}"
            )


# --- 2. orders.discount_cents ----------------------------------------------


def test_orders_discount_cents_is_not_null_defaults_to_zero_and_keeps_amounts(
    database: Path,
) -> None:
    with _connect(database) as connection:
        ids = _seed_orders(connection)

    _upgrade(database, "head")

    with _connect(database) as connection:
        columns = _columns(connection, "orders")
        assert columns["discount_cents"]["notnull"] is True, (
            "orders.discount_cents must be NOT NULL: the final modeling declares "
            "`bigint NOT NULL DEFAULT 0`"
        )
        assert _default(columns["discount_cents"]["default"]) == "0", (
            f"orders.discount_cents needs DEFAULT 0, got {columns['discount_cents']['default']!r}"
        )

        backfilled = connection.execute(
            sa.text(
                "SELECT subtotal_cents, discount_cents, amount_cents FROM orders WHERE id = :id"
            ),
            {"id": ids["order"]},
        ).one()
        assert tuple(backfilled) == (1000, 0, 1000), (
            "the NULL discount must become 0 and the amount must stay consistent with "
            f"`amount_cents = subtotal_cents - discount_cents`; got {tuple(backfilled)}"
        )

        untouched = connection.execute(
            sa.text(
                "SELECT subtotal_cents, discount_cents, amount_cents FROM orders WHERE id = :id"
            ),
            {"id": ids["discounted_order"]},
        ).one()
        assert tuple(untouched) == (1000, 250, 750), (
            f"an existing discount must survive the rebuild; got {tuple(untouched)}"
        )

    with _connect(database) as connection:
        order_id = uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
                "amount_cents, status) VALUES (:id, :account, :workspace, 500, 500, 'PAID')"
            ),
            {"id": order_id, "account": ids["account"], "workspace": ids["workspace"]},
        )
        inserted = connection.execute(
            sa.text("SELECT discount_cents FROM orders WHERE id = :id"), {"id": order_id}
        ).scalar_one()
        assert inserted == 0, f"a new order must default discount_cents to 0, got {inserted!r}"

    with _connect(database) as connection:
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                sa.text(
                    "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
                    "discount_cents, amount_cents, status) "
                    "VALUES (:id, :account, :workspace, 500, NULL, 500, 'PAID')"
                ),
                {"id": uuid4().hex, "account": ids["account"], "workspace": ids["workspace"]},
            )

    # Rebuilding the table must not drop `chk_orders_amount_consistency`.
    with _connect(database) as connection:
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                sa.text(
                    "INSERT INTO orders (id, billing_account_id, workspace_id, subtotal_cents, "
                    "discount_cents, amount_cents, status) "
                    "VALUES (:id, :account, :workspace, 1000, 100, 1000, 'PAID')"
                ),
                {"id": uuid4().hex, "account": ids["account"], "workspace": ids["workspace"]},
            )


def test_orders_discount_backfill_normalises_inconsistent_amounts(database: Path) -> None:
    """The NULL-discount backfill has two branches beside the canonical row.

    A legacy row may carry ``discount_cents IS NULL`` with an amount that does not
    match the subtotal, because the ``amount_cents = subtotal_cents - discount_cents``
    CHECK is unknown (not false) while the discount is NULL. Both branches must land
    on a row the invariant accepts:

    - ``amount_cents`` below the subtotal -> the difference becomes the discount;
    - ``amount_cents`` above the subtotal  -> the discount is 0 and the amount is
      clamped to the subtotal.
    """
    with _connect(database) as connection:
        # The control rows keep the canonical case and the consistent case in the same
        # INSERT ... SELECT, so a per-row CASE cannot regress unseen.
        ids = _seed_orders(connection)
        below = _insert_order(
            connection, ids, subtotal_cents=1000, amount_cents=800, discount_cents=None
        )
        above = _insert_order(
            connection, ids, subtotal_cents=1000, amount_cents=1200, discount_cents=None
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        below_amounts = _order_amounts(connection, below)
        assert below_amounts == (1000, 200, 800), (
            "a NULL discount under a 1000 subtotal paid as 800 must become 200, keeping "
            f"the recorded amount; got {below_amounts}"
        )

        above_amounts = _order_amounts(connection, above)
        assert above_amounts == (1000, 0, 1000), (
            "a NULL discount whose amount exceeds the subtotal must clamp to discount 0 "
            f"and amount = subtotal, never a negative discount; got {above_amounts}"
        )

        assert _order_amounts(connection, ids["order"]) == (1000, 0, 1000), (
            "the canonical NULL-discount row must keep its zero-discount result"
        )
        assert _order_amounts(connection, ids["discounted_order"]) == (1000, 250, 750), (
            "a consistent existing discount must not be rewritten by the new branches"
        )


# --- 3. provider_idempotency_keys.provider default --------------------------


def test_provider_idempotency_keys_provider_defaults_to_pagarme(database: Path) -> None:
    _upgrade(database, "head")

    with _connect(database) as connection:
        columns = _columns(connection, "provider_idempotency_keys")
        assert _default(columns["provider"]["default"]).upper() == "PAGARME", (
            "provider_idempotency_keys.provider needs DEFAULT 'PAGARME'; got "
            f"{columns['provider']['default']!r}"
        )

    with _connect(database) as connection:
        key_id = uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO provider_idempotency_keys (id, idempotency_key, status) "
                "VALUES (:id, :key, 'STARTED')"
            ),
            {"id": key_id, "key": f"idem_{key_id}"},
        )
        provider = connection.execute(
            sa.text("SELECT provider FROM provider_idempotency_keys WHERE id = :id"),
            {"id": key_id},
        ).scalar_one()
        assert provider == "PAGARME", f"the server default must fill provider, got {provider!r}"


def test_provider_idempotency_keys_rebuild_preserves_existing_rows(database: Path) -> None:
    """The default is added by rebuilding the table, so the copy must be lossless.

    The seeded key proves the rebuild does not fall back to the new ``'PAGARME'``
    default over a real provider, keeps every column value, and recreates the unique
    index that protects idempotency (verified functionally, not only by ``PRAGMA``).
    """
    key_id = uuid4().hex
    idempotency_key = "idem_rebuild_existing"
    expires_at = "2027-01-01 00:00:00"
    with _connect(database) as connection:
        connection.execute(
            sa.text(
                "INSERT INTO provider_idempotency_keys "
                "(id, provider, idempotency_key, status, expires_at) "
                "VALUES (:id, 'STRIPE', :key, 'COMPLETED', :expires_at)"
            ),
            {"id": key_id, "key": idempotency_key, "expires_at": expires_at},
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        row = connection.execute(
            sa.text(
                "SELECT provider, idempotency_key, status, expires_at "
                "FROM provider_idempotency_keys WHERE id = :id"
            ),
            {"id": key_id},
        ).one()
        assert row[0] == "STRIPE", (
            "the rebuild must keep the recorded provider instead of applying the new "
            f"'PAGARME' default; got {row[0]!r}"
        )
        assert row[1] == idempotency_key, f"idempotency_key was rewritten: {row[1]!r}"
        assert row[2] == "COMPLETED", f"status was rewritten by the copy: {row[2]!r}"
        assert _stamp(row[3]) == expires_at, (
            f"expires_at was rewritten by the copy: {row[3]!r} expected {expires_at!r}"
        )

        indexes = _indexes(connection, "provider_idempotency_keys")
        unique = indexes.get("uq_provider_idempotency_keys_provider_key")
        assert unique is not None, (
            "the rebuild must recreate uq_provider_idempotency_keys_provider_key; got "
            f"{sorted(indexes)}"
        )
        assert unique["unique"] is True, unique
        assert unique["columns"] == ["provider", "idempotency_key"], unique
        assert "ix_provider_idempotency_keys_expires_at" in indexes, sorted(indexes)

    # A recreated index must still reject a duplicate idempotency key.
    with _connect(database) as connection:
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                sa.text(
                    "INSERT INTO provider_idempotency_keys "
                    "(id, provider, idempotency_key, status) "
                    "VALUES (:id, 'STRIPE', :key, 'STARTED')"
                ),
                {"id": uuid4().hex, "key": idempotency_key},
            )


# --- 4. provider_webhook_events.status default ------------------------------


def test_provider_webhook_events_status_defaults_to_received(database: Path) -> None:
    _upgrade(database, "head")

    with _connect(database) as connection:
        columns = _columns(connection, "provider_webhook_events")
        assert _default(columns["status"]["default"]).upper() == "RECEIVED", (
            "provider_webhook_events.status needs DEFAULT 'RECEIVED'; got "
            f"{columns['status']['default']!r}"
        )

    with _connect(database) as connection:
        event_id = uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO provider_webhook_events "
                "(id, external_id, dedupe_key, event_type, payload) "
                "VALUES (:id, :external_id, :dedupe_key, 'order.paid', '{}')"
            ),
            {"id": event_id, "external_id": "evt_default", "dedupe_key": "dedupe_default"},
        )
        status = connection.execute(
            sa.text("SELECT status FROM provider_webhook_events WHERE id = :id"), {"id": event_id}
        ).scalar_one()
        assert status == "RECEIVED", f"the server default must fill status, got {status!r}"


# --- 5. image_resizes index names -------------------------------------------


def test_image_resizes_indexes_use_the_final_modeling_names(database: Path) -> None:
    _upgrade(database, "head")

    with _connect(database) as connection:
        indexes = _indexes(connection, "image_resizes")

    assert "idx_image_resizes_source_image" in indexes, (
        "image_resizes must expose the dump index name `idx_image_resizes_source_image`; "
        f"got {sorted(indexes)}"
    )
    assert indexes["idx_image_resizes_source_image"]["columns"] == ["source_image_id"]
    assert indexes["idx_image_resizes_source_image"]["unique"] is False

    assert "uq_image_resizes_storage" in indexes, (
        "image_resizes must expose the dump index name `uq_image_resizes_storage`; "
        f"got {sorted(indexes)}"
    )
    assert indexes["uq_image_resizes_storage"]["unique"] is True
    assert indexes["uq_image_resizes_storage"]["columns"] == ["storage_bucket", "storage_key"]

    assert "ix_image_resizes_source_image_id" not in indexes, (
        "the previous index name must be gone, otherwise the rename never happened"
    )
    assert "uq_image_resizes_storage_bucket_storage_key" not in indexes, (
        "the previous unique index name must be gone, otherwise the rename never happened"
    )
    assert "idx_image_resizes_created_by" in indexes, (
        "renaming the two indexes must not drop the unrelated partial index"
    )


# --- 6. coupon_redemptions foreign keys -------------------------------------


def test_coupon_redemptions_links_credit_transactions_instead_of_workspaces(
    database: Path,
) -> None:
    with _connect(database) as connection:
        ids = _seed_orders(connection)
        coupon_id, transaction_id, redemption_id = uuid4().hex, uuid4().hex, uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO coupons (id, code, type, discount_percent) "
                "VALUES (:id, :code, 'DISCOUNT', 10)"
            ),
            {"id": coupon_id, "code": "MICRO10"},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workspace_credit_transactions "
                "(id, workspace_id, amount, transaction_type) "
                "VALUES (:id, :workspace, 10, 'COUPON_CREDIT')"
            ),
            {"id": transaction_id, "workspace": ids["workspace"]},
        )
        connection.execute(
            sa.text(
                "INSERT INTO coupon_redemptions "
                "(id, coupon_id, user_id, workspace_id, order_id, credit_transaction_id) "
                "VALUES (:id, :coupon, :user, :workspace, :order, :transaction)"
            ),
            {
                "id": redemption_id,
                "coupon": coupon_id,
                "user": ids["user"],
                "workspace": ids["workspace"],
                "order": ids["order"],
                "transaction": transaction_id,
            },
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        foreign_keys = _foreign_keys(connection, "coupon_redemptions")

    credit = [fk for fk in foreign_keys if fk["table"] == "workspace_credit_transactions"]
    assert len(credit) == 1, (
        "coupon_redemptions needs exactly one foreign key to workspace_credit_transactions; "
        f"got {credit}"
    )
    assert credit[0]["columns"] == ["credit_transaction_id"], credit[0]
    assert credit[0]["targets"] == ["id"], credit[0]
    assert credit[0]["on_delete"] == "SET NULL", credit[0]

    assert not [fk for fk in foreign_keys if fk["table"] == "workspaces"], (
        "the simple `workspace_id -> workspaces` foreign key must be dropped; the workspace "
        "is already validated by the composite FKs to orders/subscriptions"
    )

    targets = {fk["table"] for fk in foreign_keys}
    assert {"coupons", "users", "invoices", "orders", "subscriptions"} <= targets, (
        f"the rebuild must keep the remaining foreign keys, got {sorted(targets)}"
    )

    with _connect(database) as connection:
        row = connection.execute(
            sa.text(
                "SELECT workspace_id, credit_transaction_id FROM coupon_redemptions WHERE id = :id"
            ),
            {"id": redemption_id},
        ).one()
        assert tuple(row) == (ids["workspace"], transaction_id), (
            "the table rebuild must preserve existing redemptions; got "
            f"{tuple(row)} expected {(ids['workspace'], transaction_id)}"
        )


# --- 7. security: the new ledger foreign key must not be created over bad data --


def test_coupon_redemptions_dangling_credit_transaction_never_survives_the_upgrade(
    database: Path,
) -> None:
    """A ``credit_transaction_id`` the ledger does not know is untrusted data.

    ``migrations/env.py`` turns ``PRAGMA foreign_keys`` off for the rebuild, so SQLite
    accepts a pre-existing dangling reference when the constraint is created and every
    later ``INSERT``/``UPDATE`` leaves it invisible. The migration therefore has to
    neutralise the value itself, matching the ``ON DELETE SET NULL`` shape: a dangling
    link must read as NULL, while a resolvable link must be preserved untouched.
    """
    dangling = uuid4().hex  # never inserted into workspace_credit_transactions
    with _connect(database) as connection:
        ids = _seed_orders(connection)
        transaction_id = uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO workspace_credit_transactions "
                "(id, workspace_id, amount, transaction_type) "
                "VALUES (:id, :workspace, 10, 'COUPON_CREDIT')"
            ),
            {"id": transaction_id, "workspace": ids["workspace"]},
        )
        valid_redemption = _insert_redemption(
            connection, ids, coupon_code="MICROVALID", credit_transaction_id=transaction_id
        )
        dangling_redemption = _insert_redemption(
            connection, ids, coupon_code="MICRODANGLE", credit_transaction_id=dangling
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        dangling_value = connection.execute(
            sa.text("SELECT credit_transaction_id FROM coupon_redemptions WHERE id = :id"),
            {"id": dangling_redemption},
        ).scalar_one()
        valid_value = connection.execute(
            sa.text("SELECT credit_transaction_id FROM coupon_redemptions WHERE id = :id"),
            {"id": valid_redemption},
        ).scalar_one()
        violations = connection.exec_driver_sql(
            'PRAGMA foreign_key_check("coupon_redemptions")'
        ).fetchall()

    assert dangling_value is None, (
        "coupon_redemptions.credit_transaction_id pointed at a transaction that does not "
        "exist and the upgrade kept it; the new FK must either fail the migration loudly "
        f"or null the dangling value, got {dangling_value!r}"
    )
    assert valid_value == transaction_id, (
        "neutralising the dangling row must not touch a resolvable credit transaction; "
        f"got {valid_value!r} expected {transaction_id!r}"
    )
    assert violations == [], (
        "PRAGMA foreign_key_check still reports dangling rows in coupon_redemptions "
        f"(table, rowid, parent, fkid): {violations}"
    )


def test_canonical_upgrade_leaves_no_dangling_foreign_keys(database: Path) -> None:
    """The whole chain must not leave a reference the database cannot resolve."""
    with _connect(database) as connection:
        ids = _seed_orders(connection)
        transaction_id = uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO workspace_credit_transactions "
                "(id, workspace_id, amount, transaction_type) "
                "VALUES (:id, :workspace, 10, 'COUPON_CREDIT')"
            ),
            {"id": transaction_id, "workspace": ids["workspace"]},
        )
        _insert_redemption(
            connection, ids, coupon_code="MICROFKCHECK", credit_transaction_id=transaction_id
        )

    _upgrade(database, "head")

    with _connect(database) as connection:
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()

    assert violations == [], (
        "the upgraded database has dangling foreign keys (table, rowid, parent, fkid): "
        f"{violations}"
    )


# --- 8. downgrade restores the previous shape -------------------------------


def test_downgrade_restores_the_previous_schema_without_losing_rows(database: Path) -> None:
    """Issue #170 requires a functional downgrade for every new revision.

    The assertion is shape-based, not byte-based: only that the previous columns,
    defaults, index names and foreign keys come back and the seeded rows survive.
    """
    with _connect(database) as connection:
        ids = _seed_orders(connection)
        coupon_id, transaction_id, redemption_id = uuid4().hex, uuid4().hex, uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO coupons (id, code, type, discount_percent) "
                "VALUES (:id, 'MICRODOWN', 'DISCOUNT', 10)"
            ),
            {"id": coupon_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workspace_credit_transactions "
                "(id, workspace_id, amount, transaction_type) "
                "VALUES (:id, :workspace, 10, 'COUPON_CREDIT')"
            ),
            {"id": transaction_id, "workspace": ids["workspace"]},
        )
        connection.execute(
            sa.text(
                "INSERT INTO coupon_redemptions "
                "(id, coupon_id, user_id, workspace_id, order_id, credit_transaction_id) "
                "VALUES (:id, :coupon, :user, :workspace, :order, :transaction)"
            ),
            {
                "id": redemption_id,
                "coupon": coupon_id,
                "user": ids["user"],
                "workspace": ids["workspace"],
                "order": ids["order"],
                "transaction": transaction_id,
            },
        )

    _upgrade(database, "head")

    # A round trip only proves something if the upgrade really applied first.
    with _connect(database) as connection:
        assert "updated_at" in _columns(connection, "provider_webhook_events"), (
            "the downgrade test assumes the upgrade added provider_webhook_events.updated_at"
        )
        assert "idx_image_resizes_source_image" in _indexes(connection, "image_resizes"), (
            "the downgrade test assumes the upgrade renamed the image_resizes index"
        )
        assert "workspace_credit_transactions" in {
            fk["table"] for fk in _foreign_keys(connection, "coupon_redemptions")
        }, "the downgrade test assumes the upgrade added the credit transaction foreign key"

    _downgrade(database, LEGACY_REVISION)

    with _connect(database) as connection:
        webhook_columns = _columns(connection, "provider_webhook_events")
        assert "updated_at" not in webhook_columns, (
            "the downgrade must drop provider_webhook_events.updated_at again"
        )
        assert _default(webhook_columns["status"]["default"]) == "", (
            "the downgrade must drop the status default"
        )

        order_columns = _columns(connection, "orders")
        assert order_columns["discount_cents"]["notnull"] is False, (
            "the downgrade must restore the nullable orders.discount_cents"
        )
        assert _default(order_columns["discount_cents"]["default"]) == "", (
            "the downgrade must drop the discount_cents default"
        )
        idempotency_columns = _columns(connection, "provider_idempotency_keys")
        assert _default(idempotency_columns["provider"]["default"]) == "", (
            "the downgrade must drop the provider default"
        )

        indexes = _indexes(connection, "image_resizes")
        assert "ix_image_resizes_source_image_id" in indexes, sorted(indexes)
        assert "uq_image_resizes_storage_bucket_storage_key" in indexes, sorted(indexes)
        assert "idx_image_resizes_source_image" not in indexes, sorted(indexes)
        assert "uq_image_resizes_storage" not in indexes, sorted(indexes)

        foreign_keys = _foreign_keys(connection, "coupon_redemptions")
        assert [fk for fk in foreign_keys if fk["table"] == "workspaces"], (
            "the downgrade must restore the simple workspace foreign key"
        )
        assert not [fk for fk in foreign_keys if fk["table"] == "workspace_credit_transactions"], (
            "the downgrade must drop the workspace_credit_transactions foreign key"
        )

        orders = connection.execute(sa.text("SELECT COUNT(*) FROM orders")).scalar_one()
        assert orders == 2, f"the downgrade must not lose orders, found {orders}"
        redemption = connection.execute(
            sa.text("SELECT credit_transaction_id FROM coupon_redemptions WHERE id = :id"),
            {"id": redemption_id},
        ).scalar_one()
        assert redemption == transaction_id, (
            "the downgrade must not lose the redemption row or its credit transaction link; "
            f"got {redemption!r}"
        )


# --- metadata: the models must offer what the parity gate compares ----------


def test_metadata_declares_updated_at_discount_and_server_defaults() -> None:
    webhook = Base.metadata.tables["provider_webhook_events"]
    assert "updated_at" in webhook.c, "provider_webhook_events.updated_at is missing from the model"
    assert webhook.c.updated_at.nullable is False
    assert _server_default(webhook.c.status).upper() == "RECEIVED"

    idempotency = Base.metadata.tables["provider_idempotency_keys"]
    assert _server_default(idempotency.c.provider).upper() == "PAGARME"

    orders = Base.metadata.tables["orders"]
    assert orders.c.discount_cents.nullable is False
    assert _server_default(orders.c.discount_cents) == "0"


def test_metadata_image_resizes_index_names_match_the_final_modeling() -> None:
    names = {index.name for index in Base.metadata.tables["image_resizes"].indexes}

    assert "idx_image_resizes_source_image" in names, sorted(names)
    assert "uq_image_resizes_storage" in names, sorted(names)
    assert "ix_image_resizes_source_image_id" not in names, sorted(names)
    assert "uq_image_resizes_storage_bucket_storage_key" not in names, sorted(names)


def test_metadata_coupon_redemptions_foreign_keys_follow_the_final_modeling() -> None:
    table = Base.metadata.tables["coupon_redemptions"]

    credit = [
        fk for fk in table.foreign_keys if fk.column.table.name == "workspace_credit_transactions"
    ]
    assert len(credit) == 1, f"expected one credit_transaction foreign key, got {credit}"
    assert credit[0].parent.name == "credit_transaction_id", credit[0]
    assert credit[0].column.name == "id", credit[0]
    assert credit[0].ondelete == "SET NULL", credit[0]

    workspaces = [
        fk
        for fk in table.foreign_keys
        if fk.parent.name == "workspace_id" and fk.column.table.name == "workspaces"
    ]
    assert workspaces == [], f"the simple workspace foreign key must be removed, got {workspaces}"
