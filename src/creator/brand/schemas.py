"""Request payloads for the brand capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from creator.core.schemas import CreatorDTO


class BrandColorCreateRequest(BaseModel):
    brand_id: UUID
    name: str | None = Field(default=None, max_length=50)
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    position: int | None = None


class BrandColorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    position: int | None = None


BrandAssetType = Literal["LOGO", "IMAGE", "FONT", "ICON", "DOCUMENT", "OTHER"]


class BrandAssetCreateRequest(CreatorDTO):
    brand_id: UUID
    type: BrandAssetType
    storage_bucket: str = Field(min_length=1, max_length=63)
    storage_key: str = Field(min_length=1, max_length=1024)
    file_name: str | None = None
    description: str | None = None


class BrandAssetUpdateRequest(CreatorDTO):
    type: BrandAssetType | None = None
    storage_bucket: str | None = Field(default=None, min_length=1, max_length=63)
    storage_key: str | None = Field(default=None, min_length=1, max_length=1024)
    file_name: str | None = None
    description: str | None = None


class BrandCreateRequest(CreatorDTO):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=100)
    segment: str | None = Field(default=None, max_length=100)
    promise: str | None = Field(default=None, max_length=250)
    goals: str | None = Field(default=None, max_length=1800)
    indicators: str | None = Field(default=None, max_length=250)
    inspirations: str | None = Field(default=None, max_length=1500)
    restrictions: str | None = Field(default=None, max_length=200)


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
    name: str | None = Field(default=None, min_length=1, max_length=100)
    segment: str | None = Field(default=None, max_length=100)
    promise: str | None = Field(default=None, max_length=250)
    goals: str | None = Field(default=None, max_length=1800)
    indicators: str | None = Field(default=None, max_length=250)
    inspirations: str | None = Field(default=None, max_length=1500)
    restrictions: str | None = Field(default=None, max_length=200)
