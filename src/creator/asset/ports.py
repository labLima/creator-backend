"""Persistence ports owned by the asset capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject


@dataclass(frozen=True, slots=True)
class AssetRecord:
    id: UUID
    workspace_id: UUID
    brand_id: UUID | None
    project_id: UUID | None
    content_id: UUID | None
    uploaded_by_user_id: UUID | None
    asset_type: str
    storage_path: str
    public_url: str | None
    mime_type: str
    byte_size: int
    checksum: str | None
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class AssetRepository(Protocol):
    def add(
        self,
        *,
        workspace_id: UUID,
        uploaded_by_user_id: UUID | None,
        asset_type: str,
        storage_path: str,
        mime_type: str,
        byte_size: int,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        content_id: UUID | None = None,
        public_url: str | None = None,
        checksum: str | None = None,
        metadata: JsonObject | None = None,
    ) -> AssetRecord: ...

    def get_for_user(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        include_deleted: bool = False,
    ) -> AssetRecord | None: ...

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        content_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[AssetRecord]: ...

    def update(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        asset_type: str | None = None,
        public_url: str | None = None,
        metadata: JsonObject | None = None,
    ) -> AssetRecord: ...

    def soft_delete(self, *, user_id: UUID, asset_id: UUID) -> None: ...
