"""Request payloads for the charge capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class ChargeCreateRequest(CreatorDTO):
    billing_account_id: UUID
    invoice_id: UUID | None = None
    amount_cents: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class ChargeUpdateRequest(CreatorDTO):
    amount_cents: int | None = Field(default=None, ge=0)
