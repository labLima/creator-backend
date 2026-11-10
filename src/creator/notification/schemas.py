"""Request payloads for the notification capability.

Vocabulary follows ``Creator_DB_final.sql`` (ADR-028, T24). Response bodies are
serialised by ``creator.application.serializers``; only requests are typed here.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO
from creator.domain.notification import (
    DevicePlatform,
    NotificationChannel,
    NotificationResourceType,
    NotificationType,
)


class NotificationCreateRequest(CreatorDTO):
    workspace_id: UUID
    type: NotificationType
    title: str = Field(min_length=1, max_length=150)
    body: str | None = Field(default=None, min_length=1, max_length=2000)
    payload: dict[str, object] = Field(default_factory=dict)
    resource_type: NotificationResourceType | None = None
    resource_id: UUID | None = None


class NotificationPreferenceRequest(CreatorDTO):
    type: NotificationType
    channel: NotificationChannel
    is_enabled: bool = True


class NotificationUpdateRequest(CreatorDTO):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    body: str | None = Field(default=None, min_length=1, max_length=2000)
    payload: dict[str, object] | None = None
    resource_type: NotificationResourceType | None = None
    resource_id: UUID | None = None


class UserDeviceCreateRequest(CreatorDTO):
    platform: DevicePlatform
    fcm_token: str = Field(min_length=1, max_length=255)


class UserDeviceUpdateRequest(CreatorDTO):
    platform: DevicePlatform | None = None
    fcm_token: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
