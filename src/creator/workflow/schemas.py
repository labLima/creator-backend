"""Request payloads for the workflow capability.

Moved from `creator.generation.schemas`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from creator.core.schemas import CreatorDTO


class ImageWorkflowRequest(CreatorDTO):
    brand_id: UUID | None = None
    planning_id: UUID | None = None
    post_structure_id: UUID | None = None
    campaign: str | None = Field(default=None, min_length=1, max_length=4_000)
    persona: str | None = Field(default=None, min_length=1, max_length=2_000)
    quantity: int = Field(default=1, ge=1, le=20)
    extra_instructions: str | None = Field(default=None, max_length=4_000)
    human_review: Literal["AUTO", "OPTIONAL"] = "AUTO"
    max_refinements: int | None = Field(default=None, ge=0, le=10)
    extensions: dict[str, object] = Field(default_factory=dict)
    compose_text: bool = False
    headline: str | None = Field(default=None, max_length=500)
    supporting_text: str | None = Field(default=None, max_length=2_000)
    call_to_action: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_composition(self) -> ImageWorkflowRequest:
        planning_mode = self.planning_id is not None or self.post_structure_id is not None
        if planning_mode and (self.planning_id is None or self.post_structure_id is None):
            raise ValueError("planning_id and post_structure_id must be provided together")
        if not planning_mode and (
            self.brand_id is None or self.campaign is None or self.persona is None
        ):
            raise ValueError("brand_id, campaign, and persona are required without Planning")
        has_text = any((self.headline, self.supporting_text, self.call_to_action))
        if self.compose_text and not has_text:
            raise ValueError("text composition requires at least one approved text field")
        if not self.compose_text and has_text:
            raise ValueError("approved text fields require compose_text")
        return self


class ImageWorkflowDecisionRequest(CreatorDTO):
    decision: Literal["APPROVE", "REFINE", "REJECT"]
    feedback: str | None = Field(default=None, max_length=4_000)
