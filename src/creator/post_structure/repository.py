"""SQLAlchemy implementation of the post_structure persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

import creator.campaign.models as campaign_models
import creator.planning.models as planning_models
import creator.post_structure.models as post_structure_models
import creator.workspace.models as workspace_models
from creator.core.pagination import Page, PageRequest
from creator.post_structure.ports import PostStructureRecord


def _post_record(row: post_structure_models.PostStructure) -> PostStructureRecord:
    return PostStructureRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        planning_id=row.planning_id,
        created_by=row.created_by,
        title=row.post_title,
        objective=row.post_objective,
        big_idea=row.post_big_idea,
        main_message=row.post_main_message,
        headline=row.post_headline,
        image_cta=row.image_cta,
        art_guiding=row.art_guiding,
        status=row.post_status,
        format=row.content_format,
        ratio=row.art_ratio,
        resolution=row.art_resolution,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyPostStructureRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self, *, workspace_id: UUID, planning_id: UUID, created_by: UUID, **fields: str | None
    ) -> PostStructureRecord:
        planning = self._session.get(planning_models.Planning, planning_id)
        if planning is None or planning.deleted_at is not None:
            raise ValueError("Planning does not exist")
        campaign = self._session.get(campaign_models.Campaign, planning.campaign_id)
        if campaign is None or campaign.workspace_id != workspace_id:
            raise ValueError("Planning and post structure workspace do not match")
        field_names = {
            "title": "post_title",
            "objective": "post_objective",
            "big_idea": "post_big_idea",
            "main_message": "post_main_message",
            "headline": "post_headline",
            "status": "post_status",
            "format": "content_format",
            "ratio": "art_ratio",
            "resolution": "art_resolution",
        }
        fields = {field_names.get(key, key): value for key, value in fields.items()}
        row = post_structure_models.PostStructure(
            workspace_id=workspace_id, planning_id=planning_id, created_by=created_by, **fields
        )
        self._session.add(row)
        self._session.flush()
        return _post_record(row)

    def get_for_user(self, *, user_id: UUID, post_structure_id: UUID) -> PostStructureRecord | None:
        row = self._session.scalars(
            self._select(user_id).where(post_structure_models.PostStructure.id == post_structure_id)
        ).one_or_none()
        return _post_record(row) if row else None

    def update(
        self, *, post_structure_id: UUID, fields: dict[str, str | None]
    ) -> PostStructureRecord | None:
        row = self._session.get(post_structure_models.PostStructure, post_structure_id)
        if row is None or row.deleted_at is not None:
            return None
        for field, value in fields.items():
            setattr(
                row,
                {
                    "title": "post_title",
                    "objective": "post_objective",
                    "big_idea": "post_big_idea",
                    "main_message": "post_main_message",
                    "headline": "post_headline",
                    "status": "post_status",
                    "format": "content_format",
                    "ratio": "art_ratio",
                    "resolution": "art_resolution",
                }.get(field, field),
                value,
            )
        self._session.flush()
        return _post_record(row)

    def soft_delete(self, *, post_structure_id: UUID) -> bool:
        row = self._session.get(post_structure_models.PostStructure, post_structure_id)
        if row is None or row.deleted_at is not None:
            return False
        row.deleted_at = datetime.now(UTC)
        self._session.flush()
        return True

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        planning_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[PostStructureRecord]:
        page = page or PageRequest()
        statement = self._select(user_id)
        count = (
            select(func.count())
            .select_from(post_structure_models.PostStructure)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == post_structure_models.PostStructure.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                post_structure_models.PostStructure.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            statement = statement.where(
                post_structure_models.PostStructure.workspace_id == workspace_id
            )
            count = count.where(post_structure_models.PostStructure.workspace_id == workspace_id)
        if planning_id is not None:
            statement = statement.where(
                post_structure_models.PostStructure.planning_id == planning_id
            )
            count = count.where(post_structure_models.PostStructure.planning_id == planning_id)
        order = (
            asc(post_structure_models.PostStructure.created_at)
            if page.sort == "asc"
            else desc(post_structure_models.PostStructure.created_at)
        )
        rows = self._session.scalars(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        return Page(
            items=[_post_record(row) for row in rows],
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def _select(self, user_id: UUID) -> Select[Any]:
        return (
            select(post_structure_models.PostStructure)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == post_structure_models.PostStructure.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                post_structure_models.PostStructure.deleted_at.is_(None),
            )
        )
