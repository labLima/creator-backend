"""Persistence ports owned by the brand capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject


@dataclass(frozen=True, slots=True)
class BrandRecord:
    id: UUID
    workspace_id: UUID
    created_by: UUID | None
    name: str
    segment: str | None
    promise: str | None
    goals: str | None
    indicators: str | None
    inspirations: str | None
    restrictions: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class BrandRepository(Protocol):
    def add(
        self,
        *,
        workspace_id: UUID,
        created_by: UUID | None,
        name: str,
        segment: str | None = None,
        promise: str | None = None,
        goals: str | None = None,
        indicators: str | None = None,
        inspirations: str | None = None,
        restrictions: str | None = None,
    ) -> BrandRecord: ...

    def get_for_user(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        include_deleted: bool = False,
    ) -> BrandRecord | None: ...

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[BrandRecord]: ...

    def update(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        name: str | None = None,
        segment: str | None = None,
        promise: str | None = None,
        goals: str | None = None,
        indicators: str | None = None,
        inspirations: str | None = None,
        restrictions: str | None = None,
    ) -> BrandRecord: ...

    def soft_delete(self, *, user_id: UUID, brand_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class BrandSettingsRecord:
    id: UUID
    workspace_id: UUID
    brand_id: UUID
    voice_settings: JsonObject
    visual_settings: JsonObject
    generation_defaults: JsonObject
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class BrandSettingsRepository(Protocol):
    def get_for_user(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        include_deleted: bool = False,
    ) -> BrandSettingsRecord | None: ...

    def upsert(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        brand_id: UUID,
        voice_settings: JsonObject | None = None,
        visual_settings: JsonObject | None = None,
        generation_defaults: JsonObject | None = None,
        metadata: JsonObject | None = None,
    ) -> BrandSettingsRecord: ...

    def update(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        voice_settings: JsonObject | None = None,
        visual_settings: JsonObject | None = None,
        generation_defaults: JsonObject | None = None,
        metadata: JsonObject | None = None,
    ) -> BrandSettingsRecord: ...

    def soft_delete(self, *, user_id: UUID, brand_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class BrandColorRecord:
    id: UUID
    brand_id: UUID
    name: str | None
    hex: str
    position: int | None
    created_at: datetime
    updated_at: datetime


class BrandColorRepository(Protocol):
    def list_for_user(
        self, *, user_id: UUID, brand_id: UUID | None = None
    ) -> list[BrandColorRecord]: ...
    def get_for_user(self, *, user_id: UUID, color_id: UUID) -> BrandColorRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> BrandColorRecord: ...
    def update(self, *, color_id: UUID, fields: dict[str, object]) -> BrandColorRecord: ...
    def soft_delete(self, *, color_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class BrandAssetRecord:
    id: UUID
    brand_id: UUID
    type: str
    storage_bucket: str
    storage_key: str
    file_name: str | None
    description: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class BrandAssetRepository(Protocol):
    def add(
        self,
        *,
        brand_id: UUID,
        type: str,
        storage_bucket: str,
        storage_key: str,
        file_name: str | None = None,
        description: str | None = None,
        created_by: UUID | None = None,
    ) -> BrandAssetRecord: ...
    def get_for_user(self, *, user_id: UUID, asset_id: UUID) -> BrandAssetRecord | None: ...
    def update(self, *, asset_id: UUID, fields: dict[str, object]) -> BrandAssetRecord: ...
    def soft_delete(self, *, asset_id: UUID) -> None: ...
    def list_for_user(
        self, *, user_id: UUID, brand_id: UUID | None = None, page: PageRequest | None = None
    ) -> Page[BrandAssetRecord]: ...
