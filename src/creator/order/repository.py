"""SQLAlchemy implementation of the order persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.order.models as order_models
from creator.order.ports import OrderRecord, OrderRepository


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return OrderRecord(
            x.id,
            x.billing_account_id,
            x.workspace_id,
            x.credit_package_id,
            x.subtotal_cents,
            x.discount_cents,
            x.amount_cents,
            x.currency,
            x.status,
            x.closed,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, oid):
        return self.s.scalar(
            select(order_models.Order)
            .join(billing_account_models.BillingAccount)
            .where(
                order_models.Order.id == oid,
                billing_account_models.BillingAccount.user_id == uid,
                order_models.Order.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(order_models.Order)
                .join(billing_account_models.BillingAccount)
                .where(
                    billing_account_models.BillingAccount.user_id == user_id,
                    order_models.Order.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, order_id):
        x = self._owned(user_id, order_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = order_models.Order(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, order_id, fields):
        x = self.s.get(order_models.Order, order_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Order not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, order_id):
        x = self.s.get(order_models.Order, order_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Order not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
