"""Persistence ports owned by the persona capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class PersonaRecord:
    id: UUID
    brand_id: UUID
    created_by: UUID
    name: str
    age: int | None
    gender: str | None
    main_goal: str | None
    challenge: str | None
    interest: str | None
    routine: str | None
    journey: str | None
    trigger: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PersonaRepository(Protocol):
    def add(self, *, created_by: UUID, **fields: object) -> PersonaRecord: ...
    def get_for_user(self, *, user_id: UUID, persona_id: UUID) -> PersonaRecord | None: ...
    def update(self, *, persona_id: UUID, fields: dict[str, object]) -> PersonaRecord: ...
    def soft_delete(self, *, persona_id: UUID) -> None: ...
    def list_for_user(
        self, *, user_id: UUID, brand_id: UUID | None = None, page: PageRequest | None = None
    ) -> Page[PersonaRecord]: ...
