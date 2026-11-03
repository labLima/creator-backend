"""Persistence ports owned by the plan capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PlanRecord:
    id: UUID
    code: str
    type: str
    name: str
    description: str | None
    metadata: dict[str, object]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PlanRepository(Protocol):
    def list(self) -> list[PlanRecord]: ...
    def get(self, *, plan_id: UUID) -> PlanRecord | None: ...
    def add(
        self,
        *,
        code: str,
        type: str,
        name: str,
        description: str | None,
        metadata: dict[str, object],
        is_active: bool,
    ) -> PlanRecord: ...
    def update(self, *, plan_id: UUID, fields: dict[str, object]) -> PlanRecord: ...
    def soft_delete(self, *, plan_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class PlanItemRecord:
    id: UUID
    plan_id: UUID
    name: str
    description: str | None
    quantity: int
    cycles: int | None
    pricing_scheme_type: str | None
    price_cents: int
    price_brackets: dict[str, object] | None
    status: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PlanItemRepository(Protocol):
    def list(self, *, plan_id: UUID | None = None) -> list[PlanItemRecord]: ...
    def get(self, *, item_id: UUID) -> PlanItemRecord | None: ...
    def add(
        self,
        *,
        plan_id: UUID,
        name: str,
        description: str | None,
        quantity: int,
        cycles: int | None,
        pricing_scheme_type: str | None,
        price_cents: int,
        price_brackets: dict[str, object] | None,
        status: str | None,
    ) -> PlanItemRecord: ...
    def update(self, *, item_id: UUID, fields: dict[str, object]) -> PlanItemRecord: ...
    def soft_delete(self, *, item_id: UUID) -> None: ...
