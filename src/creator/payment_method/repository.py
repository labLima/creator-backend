"""SQLAlchemy implementation of the payment_method persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.payment_method.models as payment_method_models
from creator.payment_method.ports import BillingPaymentMethodRecord, BillingPaymentMethodRepository


def _method_fields(fields: dict[str, object]) -> dict[str, object]:
    mapping = {
        "card_brand": "brand",
        "card_type": "type",
        "card_status": "status",
        "provider_card_id": "external_id",
    }
    values: dict[str, object] = {}
    for key, value in fields.items():
        target = mapping.get(key, key)
        if target == "brand":
            value = str(value).upper() if value is not None else None
        elif target == "type":
            value = str(value).upper() if value is not None else None
        values[target] = value
    return values


class SqlAlchemyBillingPaymentMethodRepository(BillingPaymentMethodRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _record(self, x: payment_method_models.BillingPaymentMethod) -> BillingPaymentMethodRecord:
        return BillingPaymentMethodRecord(
            id=x.id,
            billing_account_id=x.billing_account_id,
            holder_name=x.holder_name,
            holder_document=x.holder_document,
            card_brand=x.brand,
            card_last_four=x.card_last_four,
            exp_month=x.exp_month,
            exp_year=x.exp_year,
            card_type=x.type,
            card_status=x.status,
            is_default=x.is_default,
            created_at=x.created_at,
            updated_at=x.updated_at,
            deleted_at=None,
        )

    def _owned(self, uid: UUID, mid: UUID):
        return self.s.scalar(
            select(payment_method_models.BillingPaymentMethod)
            .join(billing_account_models.BillingAccount)
            .where(
                payment_method_models.BillingPaymentMethod.id == mid,
                billing_account_models.BillingAccount.user_id == uid,
                payment_method_models.BillingPaymentMethod.status != "DELETED",
            )
        )

    def list_for_user(self, *, user_id: UUID, account_id: UUID | None = None):
        q = (
            select(payment_method_models.BillingPaymentMethod)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_account_models.BillingAccount.user_id == user_id,
                payment_method_models.BillingPaymentMethod.status != "DELETED",
            )
        )
        if account_id is not None:
            q = q.where(payment_method_models.BillingPaymentMethod.billing_account_id == account_id)
        return [self._record(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id: UUID, method_id: UUID):
        x = self._owned(user_id, method_id)
        return self._record(x) if x else None

    def add(self, *, billing_account_id: UUID, fields: dict[str, object]):
        values = _method_fields(fields)
        values.setdefault("status", "ACTIVE")
        x = payment_method_models.BillingPaymentMethod(
            billing_account_id=billing_account_id, **values
        )
        self.s.add(x)
        self.s.flush()
        return self._record(x)

    def update(self, *, method_id: UUID, fields: dict[str, object]):
        x = self.s.get(payment_method_models.BillingPaymentMethod, method_id)
        if x is None or x.status == "DELETED":
            raise ValueError("Billing payment method not found")
        for key, value in _method_fields(fields).items():
            setattr(x, key, value)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._record(x)

    def soft_delete(self, *, method_id: UUID):
        x = self.s.get(payment_method_models.BillingPaymentMethod, method_id)
        if x is None or x.status == "DELETED":
            raise ValueError("Billing payment method not found")
        x.status = "DELETED"
        x.updated_at = datetime.now(UTC)
        self.s.flush()
