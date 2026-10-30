"""Request payloads for the invoice capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class InvoiceCreateRequest(CreatorDTO):
    billing_account_id: UUID
    subscription_id: UUID | None = None
    amount_cents: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    billing_at: datetime | None = None
    due_at: datetime | None = None


class InvoiceUpdateRequest(CreatorDTO):
    billing_at: datetime | None = None
    due_at: datetime | None = None
    amount_cents: int | None = Field(default=None, ge=0)
