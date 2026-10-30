"""Request payloads for the notification capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class NotificationCreateRequest(CreatorDTO):
    workspace_id: UUID
    type: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=150)
    body: str = Field(min_length=1, max_length=2000)
    payload: dict[str, object] = Field(default_factory=dict)
    resource_type: str | None = Field(default=None, max_length=40)
    resource_id: UUID | None = None


class NotificationPreferenceRequest(CreatorDTO):
    type: str = Field(min_length=1, max_length=30)
    channel: str = Field(min_length=1, max_length=10)
    is_enabled: bool = True


class NotificationUpdateRequest(CreatorDTO):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    body: str | None = Field(default=None, min_length=1, max_length=2000)
    payload: dict[str, object] | None = None
    resource_type: str | None = Field(default=None, max_length=40)
    resource_id: UUID | None = None


class UserDeviceCreateRequest(CreatorDTO):
    platform: str = Field(min_length=1, max_length=10)
    fcm_token: str = Field(min_length=1, max_length=255)


class UserDeviceUpdateRequest(CreatorDTO):
    platform: str | None = Field(default=None, min_length=1, max_length=10)
    fcm_token: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
