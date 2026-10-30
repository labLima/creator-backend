"""Ports owned by the generation capability."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from creator.domain.pipeline_events import PipelineEvent


class GenerationQueue(Protocol):
    def enqueue_image_generation(self, *, job_id: UUID, request_id: UUID) -> object: ...

    def enqueue_agent_workflow(self, *, run_id: UUID, request_id: UUID) -> object: ...

    def enqueue_pipeline_event(self, *, event_id: UUID, event: PipelineEvent) -> object: ...
