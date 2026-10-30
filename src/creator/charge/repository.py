"""SQLAlchemy implementation of the charge persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.charge.models as charge_models
from creator.charge.ports import ChargeRecord, ChargeRepository


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
        row.deleted_at,
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
                charge_models.Charge.deleted_at.is_(None),
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
                charge_models.Charge.deleted_at.is_(None),
            )
        ).all()
        return [_charge(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, charge_id: UUID) -> ChargeRecord | None:
        row = self._owned(user_id, charge_id)
        return _charge(row) if row else None

    def add(
        self, *, billing_account_id: UUID, invoice_id: UUID | None, amount_cents: int, currency: str
    ) -> ChargeRecord:
        row = charge_models.Charge(
            billing_account_id=billing_account_id,
            invoice_id=invoice_id,
            amount_cents=amount_cents,
            currency=currency,
            status="pending",
        )
        self._session.add(row)
        self._session.flush()
        return _charge(row)

    def update(self, *, charge_id: UUID, fields: dict[str, object]) -> ChargeRecord:
        row = self._session.get(charge_models.Charge, charge_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Charge not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _charge(row)

    def soft_delete(self, *, charge_id: UUID) -> None:
        row = self._session.get(charge_models.Charge, charge_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Charge not found")
        row.deleted_at = datetime.now(UTC)
        row.updated_at = row.deleted_at
        self._session.flush()
