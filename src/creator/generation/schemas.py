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


class SceneReviewDecisionRequest(CreatorDTO):
    decision: Literal["APPROVE", "REJECT"]


class IndependentGenerationRequest(CreatorDTO):
    """Input for one specialist-backed Content component Generation."""

    brand_id: UUID | None = None
    artifact_type: Literal["IMAGE", "COPY", "CAPTION"]
    operation: Literal["CREATE", "REGENERATE", "TRANSFORM"] = "CREATE"
    briefing: str | None = Field(default=None, min_length=1, max_length=20_000)
    planning_id: UUID | None = None
    post_structure_id: UUID | None = None
    source_content_id: UUID | None = None
    source_image_id: UUID | None = None
    destination_preset: Literal["1080x1080", "1080x1350", "1080x1920", "1920x1080"] | None = None
    direction: str | None = Field(default=None, min_length=1, max_length=20_000)
    restrictions: list[str] = Field(default_factory=list, max_length=30)
    review_image: bool = False
    compose_text: bool = False
    headline: str | None = Field(default=None, max_length=500)
    supporting_text: str | None = Field(default=None, max_length=2_000)
    call_to_action: str | None = Field(default=None, max_length=300)
    title: str | None = Field(default=None, max_length=255)
    reference_asset_ids: list[UUID] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_operation(self) -> IndependentGenerationRequest:
        if len(set(self.reference_asset_ids)) != len(self.reference_asset_ids):
            raise ValueError("reference_asset_ids must not contain duplicates")
        if self.reference_asset_ids and self.artifact_type != "IMAGE":
            raise ValueError("reference_asset_ids are only valid for IMAGE")
        from_planning = self.planning_id is not None or self.post_structure_id is not None
        if from_planning:
            if self.planning_id is None or self.post_structure_id is None:
                raise ValueError(
                    "Planning image Generation requires planning_id and post_structure_id"
                )
            if self.artifact_type != "IMAGE" or self.operation != "CREATE":
                raise ValueError("Planning input is only supported for IMAGE CREATE")
            if self.source_content_id is not None:
                raise ValueError("Planning IMAGE CREATE must not reference source Content")
        elif self.brand_id is None or self.briefing is None:
            raise ValueError("brand_id and briefing are required without Planning input")
        if self.operation == "CREATE" and self.source_content_id is not None:
            raise ValueError("CREATE must not reference source Content")
        if self.operation == "CREATE" and self.source_image_id is not None:
            raise ValueError("CREATE must not reference a source image")
        if self.operation != "CREATE" and self.source_content_id is None:
            raise ValueError("REGENERATE and TRANSFORM require source Content")
        if self.artifact_type == "IMAGE" and not from_planning and self.direction is None:
            raise ValueError("IMAGE Generation requires a visual direction")
        if self.artifact_type == "IMAGE" and self.operation == "TRANSFORM":
            if self.source_image_id is None or self.destination_preset is None:
                raise ValueError("IMAGE TRANSFORM requires source_image_id and destination_preset")
        elif self.source_image_id is not None or self.destination_preset is not None:
            raise ValueError(
                "Source image and destination preset are only valid for IMAGE TRANSFORM"
            )
        if self.artifact_type != "IMAGE" and self.review_image:
            raise ValueError("review_image is only valid for IMAGE")
        has_text = any((self.headline, self.supporting_text, self.call_to_action))
        if self.artifact_type != "IMAGE" and (self.compose_text or has_text):
            raise ValueError("text composition is only valid for IMAGE")
        if self.compose_text and not has_text:
            raise ValueError("text composition requires at least one approved text field")
        if not self.compose_text and has_text:
            raise ValueError("approved text fields require compose_text")
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
