"""Persistence ports owned by the charge capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChargeRecord:
    id: UUID
    billing_account_id: UUID
    invoice_id: UUID | None
    amount_cents: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ChargeRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[ChargeRecord]: ...
    def get_for_user(self, *, user_id: UUID, charge_id: UUID) -> ChargeRecord | None: ...
    def add(
        self, *, billing_account_id: UUID, invoice_id: UUID | None, amount_cents: int, currency: str
    ) -> ChargeRecord: ...
    def update(self, *, charge_id: UUID, fields: dict[str, object]) -> ChargeRecord: ...
    def soft_delete(self, *, charge_id: UUID) -> None: ...
