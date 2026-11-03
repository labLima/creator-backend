"""Request payloads for the generation capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class GenerateImageRequest(CreatorDTO):
    content_id: UUID
    style: Literal["photographic", "illustration", "product_render"] | None = None


class RegenerateImageRequest(CreatorDTO):
    style: Literal["photographic", "illustration", "product_render"] | None = None


class GenerationCreateRequest(CreatorDTO):
    workspace_id: UUID
    content_id: UUID
    brand_id: UUID | None = None
    project_id: UUID | None = None
    type: Literal["IMAGE", "TEXT"] = "TEXT"
    model: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=1, max_length=20_000)
    parameters: dict[str, object] = Field(default_factory=dict)


class GenerationUpdateRequest(CreatorDTO):
    model: str | None = Field(default=None, min_length=1, max_length=255)
    prompt: str | None = Field(default=None, min_length=1, max_length=20_000)
    parameters: dict[str, object] | None = None
