"""SQLAlchemy implementation of the campaign persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

import creator.campaign.models as campaign_models
import creator.workspace.models as workspace_models
from creator.campaign.ports import CampaignRecord
from creator.core.pagination import Page, PageRequest


def _record(row: campaign_models.Campaign) -> CampaignRecord:
    return CampaignRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        created_by=row.created_by,
        name=row.name,
        description=row.description,
        target_audience=row.target_audience,
        objectives=row.objectives,
        voice=row.voice,
        start_at=row.start_at,
        end_at=row.end_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class _CampaignRepositoryBase:
    def __init__(self, session: Session) -> None:
        self._session = session

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
    ) -> CampaignRecord:
        row = campaign_models.Campaign(
            workspace_id=workspace_id,
            created_by=created_by,
            name=name,
            description=description,
            target_audience=target_audience,
            objectives=objectives,
            voice=voice,
            start_at=start_at,
            end_at=end_at,
        )
        self._session.add(row)
        self._session.flush()
        return _record(row)

    def update(self, *, campaign_id: UUID, fields: dict[str, object]) -> CampaignRecord:
        row = self._session.get(campaign_models.Campaign, campaign_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Campaign not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _record(row)

    def soft_delete(self, *, campaign_id: UUID) -> None:
        row = self._session.get(campaign_models.Campaign, campaign_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Campaign not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()


class SqlAlchemyCampaignRepository(_CampaignRepositoryBase):
    def get_for_user(self, *, user_id: UUID, campaign_id: UUID) -> CampaignRecord | None:
        row = self._session.scalars(
            self._select(user_id).where(campaign_models.Campaign.id == campaign_id)
        ).one_or_none()
        return _record(row) if row else None

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[CampaignRecord]:
        page = page or PageRequest()
        statement = self._select(user_id)
        count = (
            select(func.count())
            .select_from(campaign_models.Campaign)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == campaign_models.Campaign.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                campaign_models.Campaign.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            statement = statement.where(campaign_models.Campaign.workspace_id == workspace_id)
            count = count.where(campaign_models.Campaign.workspace_id == workspace_id)
        order = (
            asc(campaign_models.Campaign.created_at)
            if page.sort == "asc"
            else desc(campaign_models.Campaign.created_at)
        )
        rows = self._session.scalars(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        return Page(
            items=[_record(row) for row in rows],
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def _select(self, user_id: UUID) -> Select[Any]:
        return (
            select(campaign_models.Campaign)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == campaign_models.Campaign.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                campaign_models.Campaign.deleted_at.is_(None),
            )
        )
