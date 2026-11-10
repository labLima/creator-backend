"""Request payloads for the workspace capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from creator.core.schemas import CreatorDTO


class WorkspaceCreateRequest(CreatorDTO):
    name: str = Field(min_length=1, max_length=50)


class WorkspaceUpdateRequest(CreatorDTO):
    name: str = Field(min_length=1, max_length=50)


class WorkspaceInviteCreateRequest(CreatorDTO):
    workspace_id: UUID
    type: Literal["EMAIL", "LINK"]
    role: Literal["OWNER", "MANAGER", "EDITOR", "VIEWER"]
    email: str | None = Field(default=None, max_length=254)
    max_uses: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_type_fields(self) -> WorkspaceInviteCreateRequest:
        if self.type == "EMAIL":
            if self.email is None:
                raise ValueError("EMAIL invites require email")
            if self.max_uses is not None:
                raise ValueError("EMAIL invites do not use max_uses")
        else:
            if self.max_uses is None:
                raise ValueError("LINK invites require max_uses")
            if self.email is not None:
                raise ValueError("LINK invites do not use email")
        return self


class WorkspaceInviteUpdateRequest(CreatorDTO):
    role: Literal["OWNER", "MANAGER", "EDITOR", "VIEWER"] | None = None
    email: str | None = Field(default=None, max_length=254)
    max_uses: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None
    is_active: bool | None = None
