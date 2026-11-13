"""SQLAlchemy implementation of the charge persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.charge.models as charge_models
from creator.charge.ports import (
    ChargeRecord,
    ChargeRepository,
    ChargeWithLastTransactionRecord,
)

# The T20 view over ``charges`` and ``charge_transactions``. Declared as a light
# table clause because only the two derived columns are read from it; the charge
# itself still comes from the ORM entity, so the record keeps the model's types.
_CHARGES_WITH_LAST_TRANSACTION = table(
    "charges_with_last_transaction",
    column("id"),
    column("last_transaction_id"),
    column("last_transaction_status"),
)


def _charge(row: charge_models.Charge) -> ChargeRecord:
    return ChargeRecord(
        row.id,
        row.billing_account_id,
        row.invoice_id,
        row.amount_cents,
        row.currency,
        row.status,
        row.created_at,
        row.updated_at,
        None,
    )


class SqlAlchemyChargeRepository(ChargeRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _owned(self, user_id: UUID, charge_id: UUID) -> charge_models.Charge | None:
        return self._session.scalar(
            select(charge_models.Charge)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id == charge_models.Charge.billing_account_id,
            )
            .where(
                charge_models.Charge.id == charge_id,
                billing_account_models.BillingAccount.user_id == user_id,
            )
        )

    def list_for_user(self, *, user_id: UUID) -> list[ChargeRecord]:
        rows = self._session.scalars(
            select(charge_models.Charge)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id == charge_models.Charge.billing_account_id,
            )
            .where(
                billing_account_models.BillingAccount.user_id == user_id,
            )
        ).all()
        return [_charge(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, charge_id: UUID) -> ChargeRecord | None:
        row = self._owned(user_id, charge_id)
        return _charge(row) if row else None

    def get_with_last_transaction_for_user(
        self, *, user_id: UUID, charge_id: UUID
    ) -> ChargeWithLastTransactionRecord | None:
        """Read the charge together with the latest charge transaction.

        The pair comes from the ``charges_with_last_transaction`` view, which orders
        the transactions by ``(created_at, id)`` descending. The join to
        ``billing_accounts`` keeps the read tenant scoped, like ``get_for_user``.
        """
        view = _CHARGES_WITH_LAST_TRANSACTION
        row = self._session.execute(
            select(
                charge_models.Charge,
                view.c.last_transaction_id,
                view.c.last_transaction_status,
            )
            .select_from(charge_models.Charge)
            .join(view, view.c.id == charge_models.Charge.id)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id == charge_models.Charge.billing_account_id,
            )
            .where(
                charge_models.Charge.id == charge_id,
                billing_account_models.BillingAccount.user_id == user_id,
            )
        ).first()
        if row is None:
            return None

        return ChargeWithLastTransactionRecord(
            charge=_charge(row[0]),
            last_transaction_id=row[1],
            last_transaction_status=row[2],
        )

    def add(
        self, *, billing_account_id: UUID, invoice_id: UUID | None, amount_cents: int, currency: str
    ) -> ChargeRecord:
        row = charge_models.Charge(
            billing_account_id=billing_account_id,
            invoice_id=invoice_id,
            payment_method="CREDIT_CARD",
            amount_cents=amount_cents,
            currency=currency,
            status="pending",
        )
        self._session.add(row)
        self._session.flush()
        return _charge(row)

    def update(self, *, charge_id: UUID, fields: dict[str, object]) -> ChargeRecord:
        row = self._session.get(charge_models.Charge, charge_id)
        if row is None:
            raise ValueError("Charge not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _charge(row)

    def soft_delete(self, *, charge_id: UUID) -> None:
        row = self._session.get(charge_models.Charge, charge_id)
        if row is None:
            raise ValueError("Charge not found")
        self._session.delete(row)
        self._session.flush()
