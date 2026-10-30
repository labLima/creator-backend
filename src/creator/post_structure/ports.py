"""Persistence ports owned by the post_structure capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class PostStructureRecord:
    id: UUID
    workspace_id: UUID
    planning_id: UUID
    created_by: UUID
    title: str | None
    objective: str | None
    big_idea: str | None
    main_message: str | None
    headline: str | None
    image_cta: str | None
    art_guiding: str | None
    status: str | None
    format: str | None
    ratio: str | None
    resolution: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PostStructureRepository(Protocol):
    def add(
        self, *, workspace_id: UUID, planning_id: UUID, created_by: UUID, **fields: str | None
    ) -> PostStructureRecord: ...
    def get_for_user(
        self, *, user_id: UUID, post_structure_id: UUID
    ) -> PostStructureRecord | None: ...
    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        planning_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[PostStructureRecord]: ...

    def update(
        self, *, post_structure_id: UUID, fields: dict[str, str | None]
    ) -> PostStructureRecord | None: ...

    def soft_delete(self, *, post_structure_id: UUID) -> bool: ...
