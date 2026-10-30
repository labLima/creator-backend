"""Persistence ports owned by the billing_account capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BillingAccountRecord:
    id: UUID
    user_id: UUID
    payer_type: str
    name: str
    email: str
    phone: str | None
    document: str | None
    document_type: str | None
    company_name: str | None
    provider: str | None
    provider_customer_id: str | None
    provider_customer_code: str | None
    delinquent: bool
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class BillingAccountRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[BillingAccountRecord]: ...
    def get_for_user(self, *, user_id: UUID, account_id: UUID) -> BillingAccountRecord | None: ...
    def add(
        self,
        *,
        user_id: UUID,
        payer_type: str,
        name: str,
        email: str,
        phone: str | None,
        document: str | None,
        document_type: str | None,
    ) -> BillingAccountRecord: ...
    def update(
        self, *, user_id: UUID, account_id: UUID, fields: dict[str, object]
    ) -> BillingAccountRecord: ...
    def soft_delete(self, *, user_id: UUID, account_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class BillingAddressRecord:
    id: UUID
    billing_account_id: UUID
    street: str | None
    number: str | None
    complement: str | None
    neighborhood: str | None
    zip_code: str | None
    city: str | None
    state: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class BillingAddressRepository(Protocol):
    def list_for_user(
        self, *, user_id: UUID, account_id: UUID | None = None
    ) -> list[BillingAddressRecord]: ...
    def get_for_user(self, *, user_id: UUID, address_id: UUID) -> BillingAddressRecord | None: ...
    def add(
        self, *, billing_account_id: UUID, fields: dict[str, object]
    ) -> BillingAddressRecord: ...
    def update(self, *, address_id: UUID, fields: dict[str, object]) -> BillingAddressRecord: ...
    def soft_delete(self, *, address_id: UUID) -> None: ...
