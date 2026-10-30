"""Request payloads for the campaign capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class CampaignCreateRequest(CreatorDTO):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=30)
    description: str | None = Field(default=None, max_length=500)
    target_audience: str | None = Field(default=None, max_length=300)
    objectives: str | None = Field(default=None, max_length=400)
    voice: str | None = Field(default=None, max_length=20)
    start_at: datetime | None = None
    end_at: datetime | None = None


class CampaignUpdateRequest(CreatorDTO):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    description: str | None = Field(default=None, max_length=500)
    target_audience: str | None = Field(default=None, max_length=300)
    objectives: str | None = Field(default=None, max_length=400)
    voice: str | None = Field(default=None, max_length=20)
    start_at: datetime | None = None
    end_at: datetime | None = None
