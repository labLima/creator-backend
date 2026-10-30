"""Repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.coupon.ports import CouponRedemptionRecord, CouponRedemptionRepository
from creator.credit.ports import (
    WorkspaceCreditTransactionRecord,
    WorkspaceCreditTransactionRepository,
)


@dataclass(frozen=True, slots=True)
class OrderRecord:
    id: UUID
    billing_account_id: UUID
    workspace_id: UUID
    credit_package_id: UUID | None
    subtotal_cents: int
    discount_cents: int
    amount_cents: int
    currency: str
    status: str
    closed: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class OrderRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[OrderRecord]: ...
    def get_for_user(self, *, user_id: UUID, order_id: UUID) -> OrderRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> OrderRecord: ...
    def update(self, *, order_id: UUID, fields: dict[str, object]) -> OrderRecord: ...
    def soft_delete(self, *, order_id: UUID) -> None: ...


__all__ = [
    "CouponRedemptionRecord",
    "CouponRedemptionRepository",
    "OrderRecord",
    "OrderRepository",
    "WorkspaceCreditTransactionRecord",
    "WorkspaceCreditTransactionRepository",
]
