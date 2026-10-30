"""Request payloads for the brand capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from creator.core.schemas import CreatorDTO


class BrandColorCreateRequest(BaseModel):
    brand_id: UUID
    workspace_id: UUID
    order: int = 0
    color_name: str | None = None
    hex_code: str | None = None


class BrandColorUpdateRequest(BaseModel):
    order: int | None = None
    color_name: str | None = None
    hex_code: str | None = None


class BrandAssetCreateRequest(CreatorDTO):
    brand_id: UUID
    type: str = Field(min_length=1, max_length=30)
    file_url: str = Field(min_length=1, max_length=2048)
    file_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class BrandAssetUpdateRequest(CreatorDTO):
    type: str | None = Field(default=None, min_length=1, max_length=30)
    file_url: str | None = Field(default=None, min_length=1, max_length=2048)
    file_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class BrandCreateRequest(CreatorDTO):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    brand_voice: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class BrandSettingsUpdateRequest(CreatorDTO):
    voice_settings: dict[str, object] | None = None
    visual_settings: dict[str, object] | None = None
    generation_defaults: dict[str, object] | None = None
    metadata: dict[str, object] | None = None


class BrandSettingsUpsertRequest(CreatorDTO):
    workspace_id: UUID
    voice_settings: dict[str, object] = Field(default_factory=dict)
    visual_settings: dict[str, object] = Field(default_factory=dict)
    generation_defaults: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class BrandUpdateRequest(CreatorDTO):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    brand_voice: str | None = None
    metadata: dict[str, object] | None = None
