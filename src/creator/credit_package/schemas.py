"""Request payloads for the credit_package capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreditPackageCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=64)
    credits_amount: int = Field(gt=0)
    price_cents: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    is_active: bool = True


class CreditPackageUpdateRequest(BaseModel):
    name: str | None = None
    credits_amount: int | None = None
    price_cents: int | None = None
    currency: str | None = None
    is_active: bool | None = None
