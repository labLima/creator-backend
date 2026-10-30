"""Request payloads for the coupon capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CouponCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    type: str
    applies_to: str
    discount_percent: float | None = None
    credits_amount: int | None = None
    min_purchase_cents: int | None = None
    max_redemptions: int | None = None
    once_per_workspace: bool = False
    expires_at: datetime | None = None
    is_active: bool = True
    internal_note: str | None = None


class CouponRedemptionCreateRequest(BaseModel):
    coupon_id: UUID
    billing_account_id: UUID
    order_id: UUID | None = None
    subscription_id: UUID | None = None
    discount_percent_applied: float | None = None
    discount_amount_cents: int | None = None
    credits_applied: int | None = None


class CouponRedemptionUpdateRequest(BaseModel):
    status: str | None = None


class CouponUpdateRequest(BaseModel):
    type: str | None = None
    applies_to: str | None = None
    discount_percent: float | None = None
    credits_amount: int | None = None
    min_purchase_cents: int | None = None
    max_redemptions: int | None = None
    once_per_workspace: bool | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None
    internal_note: str | None = None
