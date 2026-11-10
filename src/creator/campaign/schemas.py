"""Request payloads for the campaign capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class CampaignCreateRequest(CreatorDTO):
    workspace_id: UUID
    brand_id: UUID
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    target_audience: str | None = Field(default=None, max_length=300)
    objectives: str | None = Field(default=None, max_length=400)
    expected_action: str | None = Field(default=None, max_length=250)


class CampaignUpdateRequest(CreatorDTO):
    brand_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    target_audience: str | None = Field(default=None, max_length=300)
    objectives: str | None = Field(default=None, max_length=400)
    expected_action: str | None = Field(default=None, max_length=250)
