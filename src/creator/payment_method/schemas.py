"""Request payloads for the payment_method capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentMethodCreateRequest(BaseModel):
    billing_account_id: UUID
    holder_name: str | None = Field(default=None, max_length=64)
    holder_document: str | None = Field(default=None, max_length=16)
    card_brand: (
        Literal[
            "VISA",
            "MASTERCARD",
            "AMEX",
            "ELO",
            "HIPERCARD",
            "DINERS",
            "DISCOVER",
            "JCB",
            "AURA",
            "CABAL",
            "OTHER",
        ]
        | None
    ) = None
    card_last_four: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    card_type: Literal["CREDIT", "DEBIT"] | None = None
    is_default: bool = False


class PaymentMethodUpdateRequest(BaseModel):
    holder_name: str | None = None
    holder_document: str | None = None
    is_default: bool | None = None
