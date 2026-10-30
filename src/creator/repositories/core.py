"""Repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.asset.ports import AssetRecord, AssetRepository
from creator.brand.ports import (
    BrandRecord,
    BrandRepository,
    BrandSettingsRecord,
    BrandSettingsRepository,
)
from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.generation.ports import GenerationRecord, GenerationRepository


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    id: UUID
    workspace_id: UUID
    brand_id: UUID | None
    created_by_user_id: UUID | None
    name: str
    description: str | None
    status: str
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ProjectRepository(Protocol):
    def add(
        self,
        *,
        workspace_id: UUID,
        brand_id: UUID | None,
        created_by_user_id: UUID | None,
        name: str,
        description: str | None = None,
        status: str = "ACTIVE",
        metadata: JsonObject | None = None,
    ) -> ProjectRecord: ...

    def get_for_user(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        include_deleted: bool = False,
    ) -> ProjectRecord | None: ...

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        brand_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[ProjectRecord]: ...

    def update(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        metadata: JsonObject | None = None,
    ) -> ProjectRecord: ...

    def soft_delete(self, *, user_id: UUID, project_id: UUID) -> None: ...


__all__ = [
    "AssetRecord",
    "AssetRepository",
    "BrandRecord",
    "BrandRepository",
    "BrandSettingsRecord",
    "BrandSettingsRepository",
    "GenerationRecord",
    "GenerationRepository",
    "ProjectRecord",
    "ProjectRepository",
]
