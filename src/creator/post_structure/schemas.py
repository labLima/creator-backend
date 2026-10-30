"""Request payloads for the post_structure capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class PostStructureCreateRequest(CreatorDTO):
    workspace_id: UUID
    planning_id: UUID
    title: str | None = Field(default=None, max_length=100)
    objective: str | None = Field(default=None, max_length=300)
    big_idea: str | None = Field(default=None, max_length=150)
    main_message: str | None = Field(default=None, max_length=150)
    headline: str | None = Field(default=None, max_length=50)
    image_cta: str | None = Field(default=None, max_length=30)
    art_guiding: str | None = Field(default=None, max_length=1000)
    format: str | None = None
    ratio: str | None = None
    resolution: str | None = None


class PostStructureUpdateRequest(CreatorDTO):
    title: str | None = Field(default=None, max_length=100)
    objective: str | None = Field(default=None, max_length=300)
    big_idea: str | None = Field(default=None, max_length=150)
    main_message: str | None = Field(default=None, max_length=150)
    headline: str | None = Field(default=None, max_length=50)
    image_cta: str | None = Field(default=None, max_length=30)
    art_guiding: str | None = Field(default=None, max_length=1000)
    status: str | None = Field(default=None, max_length=20)
    format: str | None = None
    ratio: str | None = None
    resolution: str | None = None
