"""Request payloads for the generation capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from creator.core.schemas import CreatorDTO


class GenerateImageRequest(CreatorDTO):
    content_id: UUID
    style: Literal["photographic", "illustration", "product_render"] | None = None


class RegenerateImageRequest(CreatorDTO):
    style: Literal["photographic", "illustration", "product_render"] | None = None


class IndependentGenerationRequest(CreatorDTO):
    """Input for one specialist-backed Content component Generation."""

    brand_id: UUID
    artifact_type: Literal["IMAGE", "COPY", "CAPTION"]
    operation: Literal["CREATE", "REGENERATE", "TRANSFORM"] = "CREATE"
    briefing: str = Field(min_length=1, max_length=20_000)
    source_content_id: UUID | None = None
    direction: str | None = Field(default=None, min_length=1, max_length=20_000)
    restrictions: list[str] = Field(default_factory=list, max_length=30)
    review_image: bool = False
    title: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_operation(self) -> IndependentGenerationRequest:
        if self.operation == "CREATE" and self.source_content_id is not None:
            raise ValueError("CREATE must not reference source Content")
        if self.operation != "CREATE" and self.source_content_id is None:
            raise ValueError("REGENERATE and TRANSFORM require source Content")
        if self.artifact_type == "IMAGE" and self.direction is None:
            raise ValueError("IMAGE Generation requires a visual direction")
        if self.artifact_type != "IMAGE" and self.review_image:
            raise ValueError("review_image is only valid for IMAGE")
        return self


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
