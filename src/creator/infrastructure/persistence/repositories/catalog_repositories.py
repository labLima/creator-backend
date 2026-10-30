from __future__ import annotations

# mypy: disable-error-code=no-untyped-def
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.coupon import models as coupon_tables
from creator.coupon.ports import CouponRecord, CouponRepository
from creator.credit_package import models as credit_package_tables
from creator.credit_package.ports import CreditPackageRecord, CreditPackageRepository


class SqlAlchemyCouponRepository(CouponRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x: coupon_tables.Coupon) -> CouponRecord:
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
                select(coupon_tables.Coupon).where(coupon_tables.Coupon.deleted_at.is_(None))
            ).all()
        ]

    def get(self, *, coupon_id: UUID):
        x = self.s.scalar(
            select(coupon_tables.Coupon).where(
                coupon_tables.Coupon.id == coupon_id, coupon_tables.Coupon.deleted_at.is_(None)
            )
        )
        return self._r(x) if x else None

    def add(self, *, fields):
        x = coupon_tables.Coupon(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, coupon_id: UUID, fields):
        x = self.s.get(coupon_tables.Coupon, coupon_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, coupon_id: UUID):
        x = self.s.get(coupon_tables.Coupon, coupon_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Coupon not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyCreditPackageRepository(CreditPackageRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x: credit_package_tables.CreditPackage) -> CreditPackageRecord:
        return CreditPackageRecord(
            x.id,
            x.code,
            x.name,
            x.credits_amount,
            x.price_cents,
            x.currency,
            x.is_active,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def list(self):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(credit_package_tables.CreditPackage).where(
                    credit_package_tables.CreditPackage.deleted_at.is_(None)
                )
            ).all()
        ]

    def get(self, *, package_id: UUID):
        x = self.s.scalar(
            select(credit_package_tables.CreditPackage).where(
                credit_package_tables.CreditPackage.id == package_id,
                credit_package_tables.CreditPackage.deleted_at.is_(None),
            )
        )
        return self._r(x) if x else None

    def add(self, *, fields):
        x = credit_package_tables.CreditPackage(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, package_id: UUID, fields):
        x = self.s.get(credit_package_tables.CreditPackage, package_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Credit package not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, package_id: UUID):
        x = self.s.get(credit_package_tables.CreditPackage, package_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Credit package not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
