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
    created_by_user_id: UUID | None
    name: str
    description: str | None
    brand_voice: str | None
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class BrandRepository(Protocol):
    def add(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID | None,
        name: str,
        description: str | None = None,
        brand_voice: str | None = None,
        metadata: JsonObject | None = None,
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
        description: str | None = None,
        brand_voice: str | None = None,
        metadata: JsonObject | None = None,
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
    workspace_id: UUID
    created_by: UUID
    order: int
    color_name: str | None
    hex_code: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


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
    file_url: str
    file_name: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class BrandAssetRepository(Protocol):
    def add(
        self,
        *,
        brand_id: UUID,
        type: str,
        file_url: str,
        file_name: str | None = None,
        description: str | None = None,
    ) -> BrandAssetRecord: ...
    def get_for_user(self, *, user_id: UUID, asset_id: UUID) -> BrandAssetRecord | None: ...
    def update(self, *, asset_id: UUID, fields: dict[str, object]) -> BrandAssetRecord: ...
    def soft_delete(self, *, asset_id: UUID) -> None: ...
    def list_for_user(
        self, *, user_id: UUID, brand_id: UUID | None = None, page: PageRequest | None = None
    ) -> Page[BrandAssetRecord]: ...
