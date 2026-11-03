"""Persistence ports owned by the campaign capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class CampaignRecord:
    id: UUID
    workspace_id: UUID
    created_by: UUID
    name: str
    description: str | None
    target_audience: str | None
    objectives: str | None
    voice: str | None
    start_at: datetime | None
    end_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CampaignRepository(Protocol):
    def add(
        self,
        *,
        workspace_id: UUID,
        created_by: UUID,
        name: str,
        description: str | None = None,
        target_audience: str | None = None,
        objectives: str | None = None,
        voice: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> CampaignRecord: ...

    def get_for_user(self, *, user_id: UUID, campaign_id: UUID) -> CampaignRecord | None: ...

    def update(self, *, campaign_id: UUID, fields: dict[str, object]) -> CampaignRecord: ...

    def soft_delete(self, *, campaign_id: UUID) -> None: ...

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[CampaignRecord]: ...
