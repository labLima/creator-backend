"""Persistence ports owned by the planning capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class PlanningRecord:
    id: UUID
    brand_id: UUID
    campaign_id: UUID
    persona_id: UUID
    created_by: UUID
    info: str | None
    static_amount: int | None
    carousel_amount: int | None
    stories_amount: int | None
    special_dates: str | None
    start_period: datetime | None
    end_period: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PlanningRepository(Protocol):
    def add(self, *, created_by: UUID, **fields: object) -> PlanningRecord: ...
    def get_for_user(self, *, user_id: UUID, planning_id: UUID) -> PlanningRecord | None: ...
    def update(self, *, planning_id: UUID, fields: dict[str, object]) -> PlanningRecord: ...
    def soft_delete(self, *, planning_id: UUID) -> None: ...
    def list_for_user(
        self, *, user_id: UUID, campaign_id: UUID | None = None, page: PageRequest | None = None
    ) -> Page[PlanningRecord]: ...
