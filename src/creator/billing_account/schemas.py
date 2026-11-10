"""Request payloads for the billing_account capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from creator.core.schemas import CreatorDTO


class BillingAccountCreateRequest(CreatorDTO):
    user_id: UUID
    payer_type: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=1, max_length=254)
    phone: str | None = Field(default=None, max_length=20)
    document: str | None = Field(default=None, max_length=50)
    document_type: str | None = Field(default=None, max_length=10)


class BillingAccountUpdateRequest(CreatorDTO):
    payer_type: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    email: str | None = Field(default=None, min_length=1, max_length=254)
    phone: str | None = Field(default=None, max_length=20)
    document: str | None = Field(default=None, max_length=50)
    document_type: str | None = Field(default=None, max_length=10)
    company_name: str | None = Field(default=None, max_length=64)


class BillingAddressCreateRequest(BaseModel):
    billing_account_id: UUID
    street: str = Field(min_length=1, max_length=256)
    number: str = Field(min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=128)
    neighborhood: str | None = Field(default=None, max_length=64)
    zip_code: str = Field(pattern=r"^[0-9]{8}$")
    city: str = Field(min_length=1, max_length=64)
    state: str = Field(pattern=r"^[A-Z]{2}$")
    country: str = Field(default="BR", pattern=r"^[A-Z]{2}$")


class BillingAddressUpdateRequest(BaseModel):
    street: str | None = Field(default=None, min_length=1, max_length=256)
    number: str | None = Field(default=None, min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=128)
    neighborhood: str | None = Field(default=None, max_length=64)
    zip_code: str | None = Field(default=None, pattern=r"^[0-9]{8}$")
    city: str | None = Field(default=None, min_length=1, max_length=64)
    state: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
