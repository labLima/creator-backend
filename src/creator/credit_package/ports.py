"""Persistence ports owned by the credit_package capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreditPackageRecord:
    id: UUID
    code: str
    name: str
    credits_amount: int
    price_cents: int
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CreditPackageRepository(Protocol):
    def list(self) -> list[CreditPackageRecord]: ...
    def get(self, *, package_id: UUID) -> CreditPackageRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> CreditPackageRecord: ...
    def update(self, *, package_id: UUID, fields: dict[str, object]) -> CreditPackageRecord: ...
    def soft_delete(self, *, package_id: UUID) -> None: ...
