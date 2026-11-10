"""SQLAlchemy implementation of the coupon persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.coupon.models as coupon_models
import creator.order.models as order_models
import creator.subscription.models as subscription_models
from creator.coupon.ports import (
    CouponRecord,
    CouponRedemptionRecord,
    CouponRedemptionRepository,
    CouponRepository,
)


class SqlAlchemyCouponRepository(CouponRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x: coupon_models.Coupon) -> CouponRecord:
        return CouponRecord(
            x.id,
            x.code,
            x.type,
            float(x.discount_percent) if x.discount_percent is not None else None,
            x.credits,
            x.applies_to,
            x.min_purchase_cents,
            x.max_redemptions,
            x.once_per_workspace,
            self.s.scalar(
                select(func.count())
                .select_from(coupon_models.CouponRedemption)
                .where(coupon_models.CouponRedemption.coupon_id == x.id)
            )
            or 0,
            x.expires_at,
            x.is_active,
            x.internal_note,
            x.created_by,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def list(self):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(coupon_models.Coupon).where(coupon_models.Coupon.deleted_at.is_(None))
            ).all()
        ]

    def get(self, *, coupon_id: UUID):
        x = self.s.scalar(
            select(coupon_models.Coupon).where(
                coupon_models.Coupon.id == coupon_id, coupon_models.Coupon.deleted_at.is_(None)
            )
        )
        return self._r(x) if x else None

    def add(self, *, fields):
        x = coupon_models.Coupon(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, coupon_id: UUID, fields):
        x = self.s.get(coupon_models.Coupon, coupon_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, coupon_id: UUID):
        x = self.s.get(coupon_models.Coupon, coupon_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyCouponRedemptionRepository(CouponRedemptionRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _billing_account_id(self, x) -> UUID:
        if x.order_id is not None:
            found = self.s.scalar(
                select(order_models.Order.billing_account_id).where(
                    order_models.Order.id == x.order_id
                )
            )
            if found is not None:
                return found
        if x.subscription_id is not None:
            found = self.s.scalar(
                select(subscription_models.Subscription.billing_account_id).where(
                    subscription_models.Subscription.id == x.subscription_id
                )
            )
            if found is not None:
                return found
        return cast(UUID, x.id)

    def _r(self, x):
        return CouponRedemptionRecord(
            id=x.id,
            coupon_id=x.coupon_id,
            billing_account_id=self._billing_account_id(x),
            order_id=x.order_id,
            subscription_id=x.subscription_id,
            discount_percent_applied=(
                float(x.discount_percent_applied)
                if x.discount_percent_applied is not None
                else None
            ),
            discount_amount_cents=x.discount_amount_cents,
            credits_applied=x.credits_applied,
            status=x.status,
            created_at=x.created_at,
            updated_at=x.updated_at,
            deleted_at=None,
        )

    def _owned(self, uid, rid):
        return self.s.scalar(
            select(coupon_models.CouponRedemption).where(
                coupon_models.CouponRedemption.id == rid,
                coupon_models.CouponRedemption.user_id == uid,
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(coupon_models.CouponRedemption).where(
                    coupon_models.CouponRedemption.user_id == user_id
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, redemption_id):
        x = self._owned(user_id, redemption_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        values = dict(fields)
        user_id = values.pop("user_id", None)
        workspace_id = values.pop("workspace_id", None)
        billing_account_id = values.pop("billing_account_id", None)
        values.pop("redemptions_count", None)
        if user_id is None and billing_account_id is not None:
            user_id = self.s.scalar(
                select(billing_account_models.BillingAccount.user_id).where(
                    billing_account_models.BillingAccount.id == billing_account_id
                )
            )
        if workspace_id is None and values.get("order_id") is not None:
            workspace_id = self.s.scalar(
                select(order_models.Order.workspace_id).where(
                    order_models.Order.id == values["order_id"]
                )
            )
        if workspace_id is None and values.get("subscription_id") is not None:
            workspace_id = self.s.scalar(
                select(subscription_models.Subscription.workspace_id).where(
                    subscription_models.Subscription.id == values["subscription_id"]
                )
            )
        if user_id is None or workspace_id is None:
            raise ValueError("Coupon redemption requires user and workspace")
        values["user_id"] = user_id
        values["workspace_id"] = workspace_id
        values["status"] = str(values.get("status") or "APPLIED").upper()
        values.setdefault("redeemed_at", datetime.now(UTC))
        x = coupon_models.CouponRedemption(**values)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, redemption_id, fields):
        x = self.s.get(coupon_models.CouponRedemption, redemption_id)
        if x is None:
            raise ValueError("Coupon redemption not found")
        for key, value in fields.items():
            if key == "status" and value is not None:
                value = str(value).upper()
                x.canceled_at = datetime.now(UTC) if value == "CANCELED" else None
            if key in {"billing_account_id", "deleted_at"}:
                continue
            if hasattr(x, key):
                setattr(x, key, value)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, redemption_id):
        x = self.s.get(coupon_models.CouponRedemption, redemption_id)
        if x is None:
            raise ValueError("Coupon redemption not found")
        self.s.delete(x)
        self.s.flush()
