"""Request payloads for the refund capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RefundCreateRequest(BaseModel):
    billing_account_id: UUID
    invoice_id: UUID | None = None
    amount_cents: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    reason: str | None = None


class RefundUpdateRequest(BaseModel):
    reason: str | None = None
    status: str | None = None
