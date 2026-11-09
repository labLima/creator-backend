"""Behaviour of the billing and credit satellites (ADR-028, slice T7).

The CHECK and UNIQUE assertions run without foreign-key enforcement (SQLite's
default) so a failure can only come from the constraint under test; SQLite names
the failing constraint in the error, which the assertions match explicitly.
Foreign keys are asserted structurally through the inspector.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base


@pytest.fixture()
def engine() -> Iterator[sa.Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_plan_payment_method_requires_positive_installments(engine: sa.Engine) -> None:
    with engine.begin() as connection, pytest.raises(IntegrityError) as error:
        connection.execute(
            sa.text(
                "INSERT INTO plan_payment_methods "
                "(id, plan_id, method, max_installments, created_at, updated_at) "
                "VALUES (:id, :plan, 'CREDIT_CARD', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "plan": uuid4().hex},
        )
    assert "chk_plan_payment_methods_max_installments" in str(error.value)


def test_plan_payment_method_is_unique_per_plan(engine: sa.Engine) -> None:
    statement = sa.text(
        "INSERT INTO plan_payment_methods "
        "(id, plan_id, method, max_installments, created_at, updated_at) "
        "VALUES (:id, :plan, 'CREDIT_CARD', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )
    with engine.begin() as connection:
        plan_id = uuid4().hex
        connection.execute(statement, {"id": uuid4().hex, "plan": plan_id})
        with pytest.raises(IntegrityError) as error:
            connection.execute(statement, {"id": uuid4().hex, "plan": plan_id})
    assert "UNIQUE constraint failed: plan_payment_methods" in str(error.value)


def test_charge_transaction_rejects_negative_amount(engine: sa.Engine) -> None:
    with engine.begin() as connection, pytest.raises(IntegrityError) as error:
        connection.execute(
            sa.text(
                "INSERT INTO charge_transactions "
                "(id, charge_id, provider, status, amount_cents, created_at, updated_at) "
                "VALUES (:id, :charge, 'PAGARME', 'PAID', -1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "charge": uuid4().hex},
        )
    assert "chk_charge_transactions_amount_nonnegative" in str(error.value)


def test_charge_transaction_provider_vocabulary_is_closed(engine: sa.Engine) -> None:
    with engine.begin() as connection, pytest.raises(IntegrityError) as error:
        connection.execute(
            sa.text(
                "INSERT INTO charge_transactions "
                "(id, charge_id, provider, status, amount_cents, created_at, updated_at) "
                "VALUES (:id, :charge, 'NOT_A_PROVIDER', 'PAID', 100, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "charge": uuid4().hex},
        )
    assert "payment_provider" in str(error.value)


def test_charge_transaction_is_idempotent_per_provider(engine: sa.Engine) -> None:
    statement = sa.text(
        "INSERT INTO charge_transactions "
        "(id, charge_id, provider, external_id, status, amount_cents, created_at, updated_at) "
        "VALUES (:id, :charge, 'PAGARME', 'ext-1', 'PAID', 100, "
        "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )
    with engine.begin() as connection:
        charge_id = uuid4().hex
        connection.execute(statement, {"id": uuid4().hex, "charge": charge_id})
        with pytest.raises(IntegrityError) as error:
            connection.execute(statement, {"id": uuid4().hex, "charge": charge_id})
    assert "UNIQUE constraint failed: charge_transactions" in str(error.value)


@pytest.mark.parametrize(
    "origins",
    [
        (False, False, False),
        (True, True, False),
        (False, True, True),
    ],
)
def test_fiscal_invoice_requires_exactly_one_origin(
    engine: sa.Engine, origins: tuple[bool, bool, bool]
) -> None:
    order, invoice, subscription = (uuid4().hex if set_ else None for set_ in origins)
    with engine.begin() as connection, pytest.raises(IntegrityError) as error:
        connection.execute(
            sa.text(
                "INSERT INTO fiscal_invoices "
                "(id, billing_account_id, order_id, invoice_id, subscription_id, "
                "amount_cents, currency, status, created_at, updated_at) "
                "VALUES (:id, :account, :order_id, :invoice_id, :subscription_id, "
                "100, 'BRL', 'PENDING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": uuid4().hex,
                "account": uuid4().hex,
                "order_id": order,
                "invoice_id": invoice,
                "subscription_id": subscription,
            },
        )
    assert "chk_fiscal_invoices_one_origin" in str(error.value)


def test_fiscal_invoice_validates_amount_and_currency(engine: sa.Engine) -> None:
    base = (
        "INSERT INTO fiscal_invoices "
        "(id, billing_account_id, order_id, amount_cents, currency, status, "
        "created_at, updated_at) VALUES (:id, :account, :origin, :amount, :currency, "
        "'PENDING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )
    with engine.begin() as connection:
        row = {
            "id": uuid4().hex,
            "account": uuid4().hex,
            "origin": uuid4().hex,
            "amount": 100,
            "currency": "BRL",
        }
        connection.execute(sa.text(base), row)
        with pytest.raises(IntegrityError) as error:
            connection.execute(sa.text(base), {**row, "id": uuid4().hex, "amount": -1})
        assert "chk_fiscal_invoices_amount_nonnegative" in str(error.value)
        with pytest.raises(IntegrityError) as error:
            connection.execute(sa.text(base), {**row, "id": uuid4().hex, "currency": "brl"})
        assert "chk_fiscal_invoices_currency_format" in str(error.value)


@pytest.mark.parametrize(
    ("original", "remaining"),
    [(0, 0), (10, -1), (10, 11)],
)
def test_credit_lot_amounts_are_consistent(
    engine: sa.Engine, original: int, remaining: int
) -> None:
    with engine.begin() as connection, pytest.raises(IntegrityError) as error:
        connection.execute(
            sa.text(
                "INSERT INTO workspace_credit_lots "
                "(id, workspace_id, grant_transaction_id, original_amount, "
                "remaining_amount, created_at, updated_at) "
                "VALUES (:id, :workspace, :grant, :original, :remaining, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": uuid4().hex,
                "workspace": uuid4().hex,
                "grant": uuid4().hex,
                "original": original,
                "remaining": remaining,
            },
        )
    assert "chk_credit_lots_amounts" in str(error.value)


def test_credit_lot_consumption_requires_positive_amount(engine: sa.Engine) -> None:
    with engine.begin() as connection, pytest.raises(IntegrityError) as error:
        connection.execute(
            sa.text(
                "INSERT INTO workspace_credit_lot_consumptions "
                "(id, workspace_id, lot_id, transaction_id, amount, created_at) "
                "VALUES (:id, :workspace, :lot, :transaction, 0, CURRENT_TIMESTAMP)"
            ),
            {
                "id": uuid4().hex,
                "workspace": uuid4().hex,
                "lot": uuid4().hex,
                "transaction": uuid4().hex,
            },
        )
    assert "chk_lot_consumptions_amount" in str(error.value)


def test_workspace_scoped_foreign_keys_are_composite(engine: sa.Engine) -> None:
    inspector = sa.inspect(engine)
    lots = {
        tuple(foreign_key["constrained_columns"]): foreign_key
        for foreign_key in inspector.get_foreign_keys("workspace_credit_lots")
    }
    assert lots[("grant_transaction_id", "workspace_id")]["referred_table"] == (
        "workspace_credit_transactions"
    )
    assert lots[("grant_transaction_id", "workspace_id")]["options"]["ondelete"] == "RESTRICT"

    consumptions = {
        tuple(foreign_key["constrained_columns"])
        for foreign_key in inspector.get_foreign_keys("workspace_credit_lot_consumptions")
    }
    assert ("lot_id", "workspace_id") in consumptions
    assert ("transaction_id", "workspace_id") in consumptions


def test_parent_unique_keys_exist_for_composite_foreign_keys(engine: sa.Engine) -> None:
    inspector = sa.inspect(engine)
    transaction_indexes = {
        index["name"]: index for index in inspector.get_indexes("workspace_credit_transactions")
    }
    assert transaction_indexes["uq_credit_tx_id_workspace"]["unique"]
    lot_indexes = {index["name"]: index for index in inspector.get_indexes("workspace_credit_lots")}
    assert lot_indexes["uq_credit_lots_id_workspace"]["unique"]


def test_fiscal_invoice_unique_indexes_are_partial(engine: sa.Engine) -> None:
    """Two documents without an access key are allowed; a duplicate key is not."""
    statement = sa.text(
        "INSERT INTO fiscal_invoices "
        "(id, billing_account_id, order_id, amount_cents, currency, status, "
        "access_key, series, number, created_at, updated_at) "
        "VALUES (:id, :account, :origin, 100, 'BRL', 'PENDING', :access_key, "
        ":series, :number, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )

    def row(**overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "id": uuid4().hex,
            "account": uuid4().hex,
            "origin": uuid4().hex,
            "access_key": None,
            "series": None,
            "number": None,
        }
        base.update(overrides)
        return base

    with engine.begin() as connection:
        # partial index: rows without an access key do not collide
        connection.execute(statement, row())
        connection.execute(statement, row())

        key = "35260112345678000199550010000000011000000017"
        connection.execute(statement, row(access_key=key))
        with pytest.raises(IntegrityError) as error:
            connection.execute(statement, row(access_key=key))
        assert "fiscal_invoices" in str(error.value)

        # partial index: number/series collide only for the same billing account
        account = uuid4().hex
        connection.execute(
            statement, row(account=account, access_key="k-1", series="1", number="1")
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                statement, row(account=account, access_key="k-2", series="1", number="1")
            )
