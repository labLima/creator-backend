"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.coupon.ports import CouponRedemptionRecord, CouponRedemptionRepository
from creator.credit.ports import (
    WorkspaceCreditTransactionRecord,
    WorkspaceCreditTransactionRepository,
)
from creator.order.ports import OrderRecord, OrderRepository

__all__ = [
    "CouponRedemptionRecord",
    "CouponRedemptionRepository",
    "OrderRecord",
    "OrderRepository",
    "WorkspaceCreditTransactionRecord",
    "WorkspaceCreditTransactionRepository",
]
