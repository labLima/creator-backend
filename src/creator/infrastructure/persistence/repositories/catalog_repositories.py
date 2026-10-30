"""Compatibility shim; implementations moved to capability repositories."""

from __future__ import annotations

from creator.coupon.repository import SqlAlchemyCouponRepository
from creator.credit_package.repository import SqlAlchemyCreditPackageRepository

__all__ = [
    "SqlAlchemyCouponRepository",
    "SqlAlchemyCreditPackageRepository",
]
