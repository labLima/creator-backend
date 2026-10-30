from __future__ import annotations

# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.billing_account import models as billing_account_tables
from creator.coupon import models as coupon_tables
from creator.coupon.ports import CouponRedemptionRecord, CouponRedemptionRepository
from creator.credit import models as credit_tables
from creator.credit.ports import (
    WorkspaceCreditTransactionRecord,
    WorkspaceCreditTransactionRepository,
)
from creator.order import models as order_tables
from creator.order.ports import OrderRecord, OrderRepository
from creator.workspace import models as workspace_tables


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
            select(order_tables.Order)
            .join(billing_account_tables.BillingAccount)
            .where(
                order_tables.Order.id == oid,
                billing_account_tables.BillingAccount.user_id == uid,
                order_tables.Order.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(order_tables.Order)
                .join(billing_account_tables.BillingAccount)
                .where(
                    billing_account_tables.BillingAccount.user_id == user_id,
                    order_tables.Order.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, order_id):
        x = self._owned(user_id, order_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = order_tables.Order(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, order_id, fields):
        x = self.s.get(order_tables.Order, order_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Order not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, order_id):
        x = self.s.get(order_tables.Order, order_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Order not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyWorkspaceCreditTransactionRepository(WorkspaceCreditTransactionRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x: credit_tables.WorkspaceCreditTransaction) -> WorkspaceCreditTransactionRecord:
        return WorkspaceCreditTransactionRecord(
            x.id,
            x.workspace_id,
            x.amount,
            x.transaction_type,
            x.reference_type,
            x.reference_id,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def list_for_user(
        self, *, user_id: UUID, workspace_id: UUID | None = None
    ) -> list[WorkspaceCreditTransactionRecord]:
        q = (
            select(credit_tables.WorkspaceCreditTransaction)
            .join(
                workspace_tables.WorkspaceMembership,
                workspace_tables.WorkspaceMembership.workspace_id
                == credit_tables.WorkspaceCreditTransaction.workspace_id,
            )
            .where(
                workspace_tables.WorkspaceMembership.user_id == user_id,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                credit_tables.WorkspaceCreditTransaction.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            q = q.where(credit_tables.WorkspaceCreditTransaction.workspace_id == workspace_id)
        return [self._r(x) for x in self.s.scalars(q).all()]

    def get_for_user(
        self, *, user_id: UUID, transaction_id: UUID
    ) -> WorkspaceCreditTransactionRecord | None:
        x = self.s.scalar(
            select(credit_tables.WorkspaceCreditTransaction)
            .join(
                workspace_tables.WorkspaceMembership,
                workspace_tables.WorkspaceMembership.workspace_id
                == credit_tables.WorkspaceCreditTransaction.workspace_id,
            )
            .where(
                credit_tables.WorkspaceCreditTransaction.id == transaction_id,
                workspace_tables.WorkspaceMembership.user_id == user_id,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                credit_tables.WorkspaceCreditTransaction.deleted_at.is_(None),
            )
        )
        return self._r(x) if x else None

    def add(self, *, fields: dict[str, object]) -> WorkspaceCreditTransactionRecord:
        x = credit_tables.WorkspaceCreditTransaction(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, transaction_id: UUID) -> None:
        x = self.s.get(credit_tables.WorkspaceCreditTransaction, transaction_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Workspace credit transaction not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyCouponRedemptionRepository(CouponRedemptionRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return CouponRedemptionRecord(
            x.id,
            x.coupon_id,
            x.billing_account_id,
            x.order_id,
            x.subscription_id,
            float(x.discount_percent_applied) if x.discount_percent_applied is not None else None,
            x.discount_amount_cents,
            x.credits_applied,
            x.status,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, rid):
        return self.s.scalar(
            select(coupon_tables.CouponRedemption)
            .join(billing_account_tables.BillingAccount)
            .where(
                coupon_tables.CouponRedemption.id == rid,
                billing_account_tables.BillingAccount.user_id == uid,
                coupon_tables.CouponRedemption.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(coupon_tables.CouponRedemption)
                .join(billing_account_tables.BillingAccount)
                .where(
                    billing_account_tables.BillingAccount.user_id == user_id,
                    coupon_tables.CouponRedemption.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, redemption_id):
        x = self._owned(user_id, redemption_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = coupon_tables.CouponRedemption(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, redemption_id, fields):
        x = self.s.get(coupon_tables.CouponRedemption, redemption_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon redemption not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, redemption_id):
        x = self.s.get(coupon_tables.CouponRedemption, redemption_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon redemption not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
