"""Request payloads for the workspace capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class WorkspaceCreateRequest(CreatorDTO):
    name: str = Field(min_length=1, max_length=50)


class WorkspaceUpdateRequest(CreatorDTO):
    name: str = Field(min_length=1, max_length=50)


class WorkspaceInviteCreateRequest(CreatorDTO):
    workspace_id: UUID
    type: str = Field(min_length=1, max_length=10)
    role: str = Field(min_length=1, max_length=20)
    email: str | None = None
    max_uses: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None


class WorkspaceInviteUpdateRequest(CreatorDTO):
    role: str | None = Field(default=None, max_length=20)
    email: str | None = None
    max_uses: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None
    is_active: bool | None = None
