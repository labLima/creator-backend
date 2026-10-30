"""Persistence ports owned by the content capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject


@dataclass(frozen=True, slots=True)
class ContentRecord:
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    content_type: str
    title: str | None
    payload: JsonObject
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    brand_id: UUID | None = None
    project_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ContentDetailRecord:
    content: ContentRecord
    images: list[ImageRecord]


@dataclass(frozen=True, slots=True)
class GeneratedTextContentRecord:
    content: ContentRecord
    generation_id: UUID
    generation_model: str
    generation_parameters: JsonObject


@dataclass(frozen=True, slots=True)
class ContentFilters:
    workspace_id: UUID | None = None
    content_type: str | None = None
    query: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    include_deleted: bool = False


class ContentRepository(Protocol):
    def add(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID | None,
        content_type: str = "IMAGE",
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        title: str | None = None,
        payload: JsonObject | None = None,
    ) -> ContentRecord: ...

    def create_text_generation(
        self,
        *,
        workspace_id: UUID,
        requested_by_user_id: UUID,
        title: str,
        payload: JsonObject,
        model: str,
        prompt: str,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        parameters: JsonObject | None = None,
    ) -> GeneratedTextContentRecord: ...

    def user_has_workspace_access(self, *, user_id: UUID, workspace_id: UUID) -> bool: ...

    def get_by_id_for_user(
        self,
        *,
        user_id: UUID,
        content_id: UUID,
        include_deleted: bool = False,
    ) -> ContentRecord | None: ...

    def get_detail_by_id_for_user(
        self,
        *,
        user_id: UUID,
        content_id: UUID,
    ) -> ContentDetailRecord | None: ...

    def list_for_user(
        self,
        *,
        user_id: UUID,
        filters: ContentFilters | None = None,
        page: PageRequest | None = None,
    ) -> Page[ContentRecord]: ...

    def update(
        self,
        content_id: UUID,
        *,
        user_id: UUID,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        title: str | None = None,
        payload: JsonObject | None = None,
    ) -> ContentRecord: ...

    def soft_delete(self, *, user_id: UUID, content_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class ImageRecord:
    id: UUID
    workspace_id: UUID
    content_id: UUID
    generation_id: UUID
    version_number: int
    storage_path: str
    public_url: str
    mime_type: str
    width: int
    height: int
    model: str
    prompt: str
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    storage_path: str
    public_url: str
    mime_type: str
    width: int
    height: int
    model: str
    prompt: str
    version_number: int | None = None
    metadata: JsonObject = field(default_factory=dict)
