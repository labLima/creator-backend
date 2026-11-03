"""Persistence ports owned by the invoice capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InvoiceRecord:
    id: UUID
    billing_account_id: UUID
    subscription_id: UUID | None
    amount_cents: int
    currency: str
    status: str
    billing_at: datetime | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class InvoiceRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[InvoiceRecord]: ...
    def get_for_user(self, *, user_id: UUID, invoice_id: UUID) -> InvoiceRecord | None: ...
    def add(
        self,
        *,
        billing_account_id: UUID,
        subscription_id: UUID | None,
        amount_cents: int,
        currency: str,
        billing_at: datetime | None,
        due_at: datetime | None,
    ) -> InvoiceRecord: ...
    def update(self, *, invoice_id: UUID, fields: dict[str, object]) -> InvoiceRecord: ...
    def soft_delete(self, *, invoice_id: UUID) -> None: ...
