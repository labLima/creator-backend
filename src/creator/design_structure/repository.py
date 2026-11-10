"""SQLAlchemy implementation of the design_structure persistence ports.

A design structure is the ``post_designs`` row of a post in the final modeling;
the legacy table only stored the link, so the mapping is direct and the record
keeps ``post_structure_id`` as the post id.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.content_plan.models as content_plan_models
import creator.post.models as post_models
import creator.workspace.models as workspace_models
from creator.design_structure.ports import DesignStructureRecord, DesignStructureRepository


def _record(row: post_models.PostDesign) -> DesignStructureRecord:
    return DesignStructureRecord(
        id=row.id,
        post_structure_id=row.post_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=None,
    )


class SqlAlchemyDesignStructureRepository(DesignStructureRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _scoped(self, user_id: UUID) -> Any:
        return (
            select(post_models.PostDesign)
            .join(post_models.Post, post_models.Post.id == post_models.PostDesign.post_id)
            .join(
                content_plan_models.ContentPlan,
                content_plan_models.ContentPlan.id == post_models.Post.content_plan_id,
            )
            .join(
                brand_models.Brand,
                brand_models.Brand.id == content_plan_models.ContentPlan.brand_id,
            )
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.Brand.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                post_models.Post.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id: UUID) -> list[DesignStructureRecord]:
        return [self._r(row) for row in self.s.scalars(self._scoped(user_id)).all()]

    def get_for_user(self, *, user_id: UUID, design_id: UUID) -> DesignStructureRecord | None:
        row = self.s.scalar(self._scoped(user_id).where(post_models.PostDesign.id == design_id))
        return self._r(row) if row else None

    def add(self, *, post_structure_id: UUID) -> DesignStructureRecord:
        post = self.s.get(post_models.Post, post_structure_id)
        if post is None or post.deleted_at is not None:
            raise ValueError("Post structure does not exist")
        design = self.s.scalar(
            select(post_models.PostDesign).where(
                post_models.PostDesign.post_id == post_structure_id
            )
        )
        if design is None:
            design = post_models.PostDesign(
                post_id=post_structure_id, format="IMAGE", ratio="RATIO_1_1"
            )
            self.s.add(design)
            self.s.flush()
        return _record(design)

    def update(self, *, design_id: UUID, fields: dict[str, object]) -> DesignStructureRecord:
        row = self.s.get(post_models.PostDesign, design_id)
        if row is None:
            raise ValueError("Design structure not found")
        for key in ("format", "ratio"):
            if key in fields:
                setattr(row, key, fields[key])
        row.updated_at = datetime.now(UTC)
        self.s.flush()
        return _record(row)

    def soft_delete(self, *, design_id: UUID) -> None:
        row = self.s.get(post_models.PostDesign, design_id)
        if row is None:
            raise ValueError("Design structure not found")
        self.s.delete(row)
        self.s.flush()

    def _r(self, row: post_models.PostDesign) -> DesignStructureRecord:
        return _record(row)
