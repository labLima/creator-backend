from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PipelineEventType(StrEnum):
    WORKFLOW_STARTED = "WorkflowStarted"
    BUSINESS_COMPLETED = "BusinessCompleted"
    PLANNER_COMPLETED = "PlannerCompleted"
    WRITER_COMPLETED = "WriterCompleted"
    ARTIST_COMPLETED = "ArtistCompleted"
    REVIEWER_COMPLETED = "ReviewerCompleted"
    WRITER_REFINEMENT_REQUESTED = "WriterRefinementRequested"


class PipelinePayloadReference(BaseModel):
    """References required to load stage input from Creator-owned persistence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_name: str | None = Field(default=None, min_length=1, max_length=100)
    schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    input_ref: str | None = Field(default=None, min_length=1, max_length=255)
    feedback_ref: str | None = Field(default=None, min_length=1, max_length=255)
    predecessor_role: str | None = Field(default=None, min_length=1, max_length=32)
    item_count: int | None = Field(default=None, ge=1, le=20)
    attempt: int = Field(default=1, ge=1, le=5)


class PipelineEvent(BaseModel):
    """Durable event envelope; the payload remains in the workflow step."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: PipelineEventType
    event_version: str = Field(pattern=r"^1\.0$")
    workspace_id: UUID
    run_id: UUID
    step_id: UUID | None = None
    predecessor_step_id: UUID | None = None
    correlation_id: UUID
    request_id: UUID | None = None
    input_hash: str | None = Field(default=None, min_length=64, max_length=64)
    output_hash: str | None = Field(default=None, min_length=64, max_length=64)
    payload_ref: PipelinePayloadReference = Field(default_factory=PipelinePayloadReference)
