"""Request payloads for the content capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from creator.core.schemas import CreatorDTO


class ContentCreateRequest(CreatorDTO):
    workspace_id: UUID
    planning_id: UUID | None = None
    brand_id: UUID | None = None
    project_id: UUID | None = None
    type: Literal["IMAGE", "TEXT"] = "IMAGE"
    title: str | None = Field(default=None, max_length=255)
    payload: dict[str, object] = Field(default_factory=dict)


class ContentUpdateRequest(CreatorDTO):
    brand_id: UUID | None = None
    project_id: UUID | None = None
    title: str | None = Field(default=None, max_length=255)
    payload: dict[str, object] | None = None


class GenerateContentRequest(CreatorDTO):
    workspace_id: UUID
    topic: str = Field(min_length=1, max_length=255)
    audience: str = Field(min_length=1, max_length=255)
    tone: (
        Literal["professional", "friendly", "persuasive", "educational", "formal", "casual"] | None
    ) = None
    content_type: Literal[
        "social_post", "email", "ad_copy", "landing_page", "blog_post", "product_description"
    ]
    brand_voice: str | None = Field(default=None, min_length=1, max_length=1_000)


class ImproveContentRequest(CreatorDTO):
    workspace_id: UUID
    text: str | None = Field(default=None, min_length=1, max_length=20_000)
    content_id: UUID | None = None
    objective: Literal["shorten", "persuasive", "formal", "seo", "audience_adaptation"]
    context: dict[str, Any] = Field(default_factory=dict)
    audience: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_target_and_context(self) -> ImproveContentRequest:
        if (self.text is None) == (self.content_id is None):
            raise ValueError("Provide exactly one of text or content_id")
        if self.objective == "audience_adaptation" and self.audience is None:
            raise ValueError("audience is required for audience_adaptation")
        return self
