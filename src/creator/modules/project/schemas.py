"""Request payloads for the project capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class ProjectCreateRequest(CreatorDTO):
    workspace_id: UUID
    brand_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: Literal["ACTIVE", "ARCHIVED"] = "ACTIVE"
    metadata: dict[str, object] = Field(default_factory=dict)


class ProjectUpdateRequest(CreatorDTO):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: Literal["ACTIVE", "ARCHIVED"] | None = None
    metadata: dict[str, object] | None = None
