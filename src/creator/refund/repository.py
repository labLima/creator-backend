"""SQLAlchemy implementation of the refund persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.refund.models as refund_models
from creator.refund.ports import RefundRecord, RefundRepository


class SqlAlchemyRefundRepository(RefundRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return RefundRecord(
            x.id,
            x.billing_account_id,
            x.invoice_id,
            x.amount_cents,
            x.currency,
            x.reason,
            x.status,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, rid):
        return self.s.scalar(
            select(refund_models.Refund)
            .join(billing_account_models.BillingAccount)
            .where(
                refund_models.Refund.id == rid,
                billing_account_models.BillingAccount.user_id == uid,
                refund_models.Refund.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(refund_models.Refund)
                .join(billing_account_models.BillingAccount)
                .where(
                    billing_account_models.BillingAccount.user_id == user_id,
                    refund_models.Refund.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, refund_id):
        x = self._owned(user_id, refund_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = refund_models.Refund(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, refund_id, fields):
        x = self.s.get(refund_models.Refund, refund_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Refund not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, refund_id):
        x = self.s.get(refund_models.Refund, refund_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Refund not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
