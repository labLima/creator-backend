"""SQLAlchemy implementation of the campaign persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.campaign.models as campaign_models
import creator.workspace.models as workspace_models
from creator.campaign.ports import CampaignRecord
from creator.core.pagination import Page, PageRequest


def _record(row: campaign_models.Campaign, workspace_id: UUID) -> CampaignRecord:
    return CampaignRecord(
        id=row.id,
        brand_id=row.brand_id,
        workspace_id=workspace_id,
        created_by=row.created_by,
        name=row.name,
        description=row.description,
        target_audience=row.target_audience,
        objectives=row.objectives,
        expected_action=row.expected_action,
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
        brand_id: UUID,
        workspace_id: UUID,
        created_by: UUID | None,
        name: str,
        description: str | None = None,
        target_audience: str | None = None,
        objectives: str | None = None,
        expected_action: str | None = None,
    ) -> CampaignRecord:
        brand_workspace = self._session.scalar(
            select(brand_models.Brand.workspace_id).where(brand_models.Brand.id == brand_id)
        )
        if brand_workspace != workspace_id:
            raise ValueError("Campaign brand does not belong to the workspace")
        row = campaign_models.Campaign(
            brand_id=brand_id,
            created_by=created_by,
            name=name,
            description=description,
            target_audience=target_audience,
            objectives=objectives,
            expected_action=expected_action,
        )
        self._session.add(row)
        self._session.flush()
        return _record(row, workspace_id)

    def update(self, *, campaign_id: UUID, fields: dict[str, object]) -> CampaignRecord:
        allowed = {
            "brand_id",
            "name",
            "description",
            "target_audience",
            "objectives",
            "expected_action",
        }
        unexpected = set(fields) - allowed
        if unexpected:
            raise ValueError(f"unsupported field(s) for campaign: {sorted(unexpected)}")
        row = self._session.get(campaign_models.Campaign, campaign_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Campaign not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        workspace_id = self._session.scalar(
            select(brand_models.Brand.workspace_id).where(brand_models.Brand.id == row.brand_id)
        )
        if workspace_id is None:
            raise ValueError("Campaign brand not found")
        return _record(row, workspace_id)

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
        found = self._session.execute(
            self._select(user_id).where(campaign_models.Campaign.id == campaign_id)
        ).one_or_none()
        if found is None:
            return None
        row, workspace_id = found
        return _record(cast(Any, row), cast(UUID, workspace_id))

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
            .join(brand_models.Brand, brand_models.Brand.id == campaign_models.Campaign.brand_id)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.Brand.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                campaign_models.Campaign.deleted_at.is_(None),
                brand_models.Brand.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            statement = statement.where(brand_models.Brand.workspace_id == workspace_id)
            count = count.where(brand_models.Brand.workspace_id == workspace_id)
        order = (
            asc(campaign_models.Campaign.created_at)
            if page.sort == "asc"
            else desc(campaign_models.Campaign.created_at)
        )
        rows = self._session.execute(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        return Page(
            items=[
                _record(cast(Any, row), cast(UUID, workspace_id_)) for row, workspace_id_ in rows
            ],
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def _select(self, user_id: UUID) -> Any:
        return (
            select(campaign_models.Campaign, brand_models.Brand.workspace_id)
            .join(brand_models.Brand, brand_models.Brand.id == campaign_models.Campaign.brand_id)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.Brand.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                campaign_models.Campaign.deleted_at.is_(None),
                brand_models.Brand.deleted_at.is_(None),
            )
        )
