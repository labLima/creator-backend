"""Ports owned by the generation capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.content.ports import ImageMetadata, ImageRecord
from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.domain.generation import GenerationJobStatus
from creator.domain.pipeline_events import PipelineEvent
from creator.user.ports import UserRecord


class GenerationQueue(Protocol):
    def enqueue_image_generation(self, *, job_id: UUID, request_id: UUID) -> object: ...

    def enqueue_agent_workflow(self, *, run_id: UUID, request_id: UUID) -> object: ...

    def enqueue_pipeline_event(self, *, event_id: UUID, event: PipelineEvent) -> object: ...


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    id: UUID
    workspace_id: UUID
    content_id: UUID
    brand_id: UUID | None
    project_id: UUID | None
    requested_by_user_id: UUID | None
    generation_type: str
    model: str
    prompt: str
    parameters: JsonObject
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class GenerationRepository(Protocol):
    def add(
        self,
        *,
        workspace_id: UUID,
        content_id: UUID,
        requested_by_user_id: UUID | None,
        model: str,
        prompt: str,
        generation_type: str = "TEXT",
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        parameters: JsonObject | None = None,
    ) -> GenerationRecord: ...

    def get_for_user(
        self,
        *,
        user_id: UUID,
        generation_id: UUID,
        include_deleted: bool = False,
    ) -> GenerationRecord | None: ...

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        content_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[GenerationRecord]: ...

    def update(
        self,
        *,
        user_id: UUID,
        generation_id: UUID,
        model: str | None = None,
        prompt: str | None = None,
        parameters: JsonObject | None = None,
    ) -> GenerationRecord: ...

    def soft_delete(self, *, user_id: UUID, generation_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class GenerationJobRecord:
    id: UUID
    workspace_id: UUID
    generation_id: UUID
    content_id: UUID
    status: GenerationJobStatus
    external_id: str | None
    attempt_count: int
    max_attempts: int
    failure_code: str | None
    failure_message: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    request_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GenerationHistoryFilters:
    workspace_id: UUID | None = None
    content_id: UUID | None = None
    status: GenerationJobStatus | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    include_deleted: bool = False


@dataclass(frozen=True, slots=True)
class GenerationJobStatusEventRecord:
    id: UUID
    generation_job_id: UUID
    previous_status: GenerationJobStatus | None
    status: GenerationJobStatus
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ImageGenerationStatusRecord:
    job: GenerationJobRecord
    parameters: JsonObject
    image: ImageRecord | None = None


@dataclass(frozen=True, slots=True)
class ImageGenerationWorkItem:
    job: GenerationJobRecord
    model: str
    prompt: str
    parameters: JsonObject
    requested_by_user: UserRecord


class ImageGenerationRepository(Protocol):
    def create_image_generation(
        self,
        *,
        workspace_id: UUID,
        content_id: UUID,
        requested_by_user_id: UUID | None,
        model: str,
        prompt: str,
        parameters: JsonObject | None = None,
        external_id: str | None = None,
        max_attempts: int = 1,
        request_id: UUID | None = None,
    ) -> GenerationJobRecord: ...

    def get_job_for_user(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        include_deleted: bool = False,
    ) -> GenerationJobRecord | None: ...

    def list_history_for_user(
        self,
        *,
        user_id: UUID,
        filters: GenerationHistoryFilters | None = None,
        page: PageRequest | None = None,
    ) -> Page[GenerationJobRecord]: ...

    def claim_next_pending(
        self, *, workspace_id: UUID | None = None
    ) -> GenerationJobRecord | None: ...

    def next_image_version(self, content_id: UUID) -> int: ...

    def reserve_image_version(self, job_id: UUID) -> int: ...

    def get_status_for_user(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        include_deleted: bool = False,
    ) -> ImageGenerationStatusRecord | None: ...

    def get_status_by_external_id_for_user(
        self,
        *,
        user_id: UUID,
        external_id: str,
        include_deleted: bool = False,
    ) -> ImageGenerationStatusRecord | None: ...

    def claim_pending_by_id(self, job_id: UUID) -> ImageGenerationWorkItem | None: ...

    def get_image_by_generation_id(self, generation_id: UUID) -> ImageRecord | None: ...

    def fail_stale_processing(
        self,
        *,
        older_than: datetime,
        failure_code: str,
        failure_message: str,
    ) -> int: ...

    def get_image_for_user(
        self,
        *,
        user_id: UUID,
        image_id: UUID,
        include_deleted: bool = False,
    ) -> ImageRecord | None: ...

    def complete_job(self, job_id: UUID, image: ImageMetadata) -> ImageRecord: ...

    def fail_job(
        self,
        job_id: UUID,
        *,
        failure_code: str,
        failure_message: str,
    ) -> GenerationJobRecord: ...


@dataclass(frozen=True, slots=True)
class GeneratedImageRecord:
    id: UUID
    workspace_id: UUID
    design_structure_id: UUID
    signed_url: str | None
    size: str | None
    resolution: str | None
    image_ratio: str | None
    status: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class GeneratedImageRepository(Protocol):
    def get_for_user(self, *, user_id: UUID, image_id: UUID) -> GeneratedImageRecord | None: ...
