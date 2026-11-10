"""SQLAlchemy implementation of the refund persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.charge.models as charge_models
import creator.refund.models as refund_models
from creator.refund.ports import RefundRecord, RefundRepository


class SqlAlchemyRefundRepository(RefundRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        charge = self.s.get(charge_models.Charge, x.charge_id)
        return RefundRecord(
            id=x.id,
            billing_account_id=charge.billing_account_id if charge else x.id,
            invoice_id=charge.invoice_id if charge else None,
            amount_cents=x.amount_cents,
            currency=x.currency,
            reason=x.reason_code,
            status=x.status,
            created_at=x.created_at,
            updated_at=x.updated_at,
            deleted_at=None,
        )

    def _owned(self, uid, rid):
        return self.s.scalar(
            select(refund_models.Refund)
            .join(charge_models.Charge, charge_models.Charge.id == refund_models.Refund.charge_id)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id == charge_models.Charge.billing_account_id,
            )
            .where(
                refund_models.Refund.id == rid,
                billing_account_models.BillingAccount.user_id == uid,
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(refund_models.Refund)
                .join(
                    charge_models.Charge,
                    charge_models.Charge.id == refund_models.Refund.charge_id,
                )
                .join(
                    billing_account_models.BillingAccount,
                    billing_account_models.BillingAccount.id
                    == charge_models.Charge.billing_account_id,
                )
                .where(billing_account_models.BillingAccount.user_id == user_id)
            ).all()
        ]

    def get_for_user(self, *, user_id, refund_id):
        x = self._owned(user_id, refund_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        values = dict(fields)
        values.setdefault("provider", "PAGARME")
        if values.get("reason_code") is not None:
            reason = str(values["reason_code"]).upper()
            allowed = {
                "CUSTOMER_REQUEST",
                "CHARGEBACK",
                "FRAUD_SUSPECT",
                "DUPLICATE",
                "SERVICE_FAILURE",
                "OTHER",
            }
            values["reason_code"] = reason if reason in allowed else None
        x = refund_models.Refund(**values)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, refund_id, fields):
        x = self.s.get(refund_models.Refund, refund_id)
        if x is None:
            raise ValueError("Refund not found")
        mapping = {"reason": "reason_code"}
        for key, value in fields.items():
            target = mapping.get(key, key)
            if target == "status" and value is not None:
                value = str(value).upper()
            if hasattr(x, target):
                setattr(x, target, value)
        if x.status != "PENDING" and x.processed_at is None:
            x.processed_at = datetime.now(UTC)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, refund_id):
        x = self.s.get(refund_models.Refund, refund_id)
        if x is None:
            raise ValueError("Refund not found")
        x.status = "FAILED"
        x.updated_at = datetime.now(UTC)
        self.s.flush()
