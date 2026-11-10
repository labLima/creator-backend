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
    brand_id: UUID
    # Derived from ``brands.workspace_id``: the final modeling has no
    # ``campaigns.workspace_id`` column, but every consumer authorizes or scopes
    # by the workspace, so the repository joins the brand and exposes it here.
    workspace_id: UUID
    created_by: UUID | None
    name: str
    description: str | None
    target_audience: str | None
    objectives: str | None
    expected_action: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CampaignRepository(Protocol):
    def add(
        self,
        *,
        brand_id: UUID,
        workspace_id: UUID,
        created_by: UUID | None,
        name: str,
        description: str | None = None,
        target_audience: str | None = None,
        objectives: str | None = None,
        expected_action: str | None = None,
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
