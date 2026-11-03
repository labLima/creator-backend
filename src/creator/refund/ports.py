"""Persistence ports owned by the refund capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RefundRecord:
    id: UUID
    billing_account_id: UUID
    invoice_id: UUID | None
    amount_cents: int
    currency: str
    reason: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class RefundRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[RefundRecord]: ...
    def get_for_user(self, *, user_id: UUID, refund_id: UUID) -> RefundRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> RefundRecord: ...
    def update(self, *, refund_id: UUID, fields: dict[str, object]) -> RefundRecord: ...
    def soft_delete(self, *, refund_id: UUID) -> None: ...
