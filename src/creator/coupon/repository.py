"""SQLAlchemy implementation of the coupon persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.coupon.models as coupon_models
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
            x.credits_amount,
            x.applies_to,
            x.min_purchase_cents,
            x.max_redemptions,
            x.once_per_workspace,
            x.redemptions_count,
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
            select(coupon_models.CouponRedemption)
            .join(billing_account_models.BillingAccount)
            .where(
                coupon_models.CouponRedemption.id == rid,
                billing_account_models.BillingAccount.user_id == uid,
                coupon_models.CouponRedemption.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(coupon_models.CouponRedemption)
                .join(billing_account_models.BillingAccount)
                .where(
                    billing_account_models.BillingAccount.user_id == user_id,
                    coupon_models.CouponRedemption.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, redemption_id):
        x = self._owned(user_id, redemption_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = coupon_models.CouponRedemption(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, redemption_id, fields):
        x = self.s.get(coupon_models.CouponRedemption, redemption_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon redemption not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, redemption_id):
        x = self.s.get(coupon_models.CouponRedemption, redemption_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon redemption not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
