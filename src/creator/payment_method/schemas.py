"""Request payloads for the payment_method capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class PaymentMethodCreateRequest(BaseModel):
    billing_account_id: UUID
    holder_name: str | None = None
    holder_document: str | None = None
    card_brand: str | None = None
    card_last_four: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    card_type: str | None = None
    is_default: bool = False


class PaymentMethodUpdateRequest(BaseModel):
    holder_name: str | None = None
    holder_document: str | None = None
    is_default: bool | None = None
