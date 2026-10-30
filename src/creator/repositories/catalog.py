"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.coupon.ports import CouponRecord, CouponRepository
from creator.credit_package.ports import CreditPackageRecord, CreditPackageRepository

__all__ = [
    "CouponRecord",
    "CouponRepository",
    "CreditPackageRecord",
    "CreditPackageRepository",
]
