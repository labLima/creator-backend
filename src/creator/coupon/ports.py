"""Persistence ports owned by the coupon capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CouponRecord:
    id: UUID
    code: str
    type: str
    discount_percent: float | None
    credits_amount: int | None
    applies_to: str
    min_purchase_cents: int | None
    max_redemptions: int | None
    once_per_workspace: bool
    redemptions_count: int
    expires_at: datetime | None
    is_active: bool
    internal_note: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CouponRepository(Protocol):
    def list(self) -> list[CouponRecord]: ...
    def get(self, *, coupon_id: UUID) -> CouponRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> CouponRecord: ...
    def update(self, *, coupon_id: UUID, fields: dict[str, object]) -> CouponRecord: ...
    def soft_delete(self, *, coupon_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class CouponRedemptionRecord:
    id: UUID
    coupon_id: UUID
    billing_account_id: UUID
    order_id: UUID | None
    subscription_id: UUID | None
    discount_percent_applied: float | None
    discount_amount_cents: int | None
    credits_applied: int | None
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CouponRedemptionRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[CouponRedemptionRecord]: ...
    def get_for_user(
        self, *, user_id: UUID, redemption_id: UUID
    ) -> CouponRedemptionRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> CouponRedemptionRecord: ...
    def update(
        self, *, redemption_id: UUID, fields: dict[str, object]
    ) -> CouponRedemptionRecord: ...
    def soft_delete(self, *, redemption_id: UUID) -> None: ...
