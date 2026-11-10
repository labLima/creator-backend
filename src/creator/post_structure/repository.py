"""SQLAlchemy implementation of the post_structure persistence ports.

The legacy ``post_structure`` table is still present until T13, but this
repository already writes the final modeling: a ``posts`` row plus a
``post_designs`` row and its first ``design_slides`` entry. The HTTP record is
kept stable by mapping the former flat columns onto those tables.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.content_plan.models as content_plan_models
import creator.post.models as post_models
import creator.workspace.models as workspace_models
from creator.core.pagination import Page, PageRequest
from creator.post_structure.ports import PostStructureRecord

_FORMATS = {"STATIC": "IMAGE", "IMAGE": "IMAGE", "CAROUSEL": "CAROUSEL", "STORIES": "STORIES"}
_RATIOS = {
    "1:1": "RATIO_1_1",
    "4:5": "RATIO_4_5",
    "9:16": "RATIO_9_16",
    "16:9": "RATIO_16_9",
    "RATIO_1_1": "RATIO_1_1",
    "RATIO_4_5": "RATIO_4_5",
    "RATIO_9_16": "RATIO_9_16",
    "RATIO_16_9": "RATIO_16_9",
}
_RESOLUTIONS = {
    "RATIO_1_1": "1080x1080",
    "RATIO_4_5": "1080x1350",
    "RATIO_9_16": "1080x1920",
    "RATIO_16_9": "1920x1080",
}
_STATUSES = {"DRAFT", "SCHEDULED", "PUBLISHED"}


def _format(value: str | None) -> str:
    return _FORMATS.get((value or "").upper(), "IMAGE")


def _ratio(value: str | None) -> str:
    return _RATIOS.get((value or "").upper(), "RATIO_1_1")


def _resolution(ratio: str) -> str | None:
    return _RESOLUTIONS.get(ratio)


def _status(value: str | None, *, scheduled_at: datetime | None = None) -> str:
    normalized = (value or "DRAFT").upper()
    if normalized not in _STATUSES:
        return "DRAFT"
    if normalized == "SCHEDULED" and scheduled_at is None:
        return "DRAFT"
    return normalized


class SqlAlchemyPostStructureRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        workspace_id: UUID,
        planning_id: UUID,
        created_by: UUID | None,
        **fields: str | None,
    ) -> PostStructureRecord:
        plan = self._session.get(content_plan_models.ContentPlan, planning_id)
        if plan is None or plan.deleted_at is not None:
            raise ValueError("Planning does not exist")
        brand = self._session.get(brand_models.Brand, plan.brand_id)
        if brand is None or brand.workspace_id != workspace_id:
            raise ValueError("Planning and post structure workspace do not match")

        publish = _status(fields.get("status")) == "PUBLISHED" and created_by is not None
        post = post_models.Post(
            content_plan_id=plan.id,
            created_by=created_by,
            title=fields.get("title"),
            objective=fields.get("objective"),
            big_idea=fields.get("big_idea"),
            main_message=fields.get("main_message"),
            publication_status="PUBLISHED" if publish else "DRAFT",
            approval_status="APPROVED" if publish else "PENDING",
            approved_by=created_by if publish else None,
            approved_at=datetime.now(UTC) if publish else None,
            published_at=datetime.now(UTC) if publish else None,
        )
        self._session.add(post)
        self._session.flush()

        design = post_models.PostDesign(
            post_id=post.id,
            format=_format(fields.get("format")),
            ratio=_ratio(fields.get("ratio")),
        )
        self._session.add(design)
        self._session.flush()
        self._session.add(
            post_models.DesignSlide(
                post_design_id=design.id,
                position=0,
                headline=fields.get("headline"),
                cta=fields.get("image_cta"),
                art_direction=fields.get("art_guiding") or "",
            )
        )
        self._session.flush()
        return self._record(post, workspace_id)

    def get_for_user(self, *, user_id: UUID, post_structure_id: UUID) -> PostStructureRecord | None:
        found = self._session.execute(
            self._select(user_id).where(post_models.Post.id == post_structure_id)
        ).one_or_none()
        if found is None:
            return None
        post, workspace_id = found
        return self._record(cast(post_models.Post, post), cast(UUID, workspace_id))

    def update(
        self, *, post_structure_id: UUID, fields: dict[str, str | None]
    ) -> PostStructureRecord | None:
        post = self._session.get(post_models.Post, post_structure_id)
        if post is None or post.deleted_at is not None:
            return None
        workspace_id = self._workspace_id(post)

        for field_name in ("title", "objective", "big_idea", "main_message"):
            if field_name in fields:
                setattr(post, field_name, fields[field_name])
        if "status" in fields:
            status = _status(fields["status"], scheduled_at=post.scheduled_at)
            publish = status == "PUBLISHED" and post.created_by is not None
            post.publication_status = "PUBLISHED" if publish else "DRAFT"
            post.published_at = datetime.now(UTC) if publish else None
            if publish:
                post.approval_status = "APPROVED"
                post.approved_by = post.created_by
                post.approved_at = post.published_at

        design = self._session.scalar(
            select(post_models.PostDesign).where(post_models.PostDesign.post_id == post.id)
        )
        if design is not None:
            if "format" in fields:
                design.format = _format(fields["format"])
            if "ratio" in fields:
                design.ratio = _ratio(fields["ratio"])
            slide = self._session.scalar(
                select(post_models.DesignSlide)
                .where(post_models.DesignSlide.post_design_id == design.id)
                .order_by(post_models.DesignSlide.position)
            )
            if slide is not None:
                if "headline" in fields:
                    slide.headline = fields["headline"]
                if "image_cta" in fields:
                    slide.cta = fields["image_cta"]
                if "art_guiding" in fields:
                    slide.art_direction = fields["art_guiding"] or ""
        post.updated_at = datetime.now(UTC)
        self._session.flush()
        return self._record(post, workspace_id)

    def soft_delete(self, *, post_structure_id: UUID) -> bool:
        post = self._session.get(post_models.Post, post_structure_id)
        if post is None or post.deleted_at is not None:
            return False
        timestamp = datetime.now(UTC)
        post.deleted_at = timestamp
        post.updated_at = timestamp
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
            .select_from(post_models.Post)
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
        if workspace_id is not None:
            statement = statement.where(brand_models.Brand.workspace_id == workspace_id)
            count = count.where(brand_models.Brand.workspace_id == workspace_id)
        if planning_id is not None:
            statement = statement.where(post_models.Post.content_plan_id == planning_id)
            count = count.where(post_models.Post.content_plan_id == planning_id)
        order = (
            asc(post_models.Post.created_at)
            if page.sort == "asc"
            else desc(post_models.Post.created_at)
        )
        rows = self._session.execute(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        return Page(
            items=[
                self._record(cast(post_models.Post, post), cast(UUID, workspace_id_))
                for post, workspace_id_ in rows
            ],
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def _select(self, user_id: UUID) -> Any:
        return (
            select(post_models.Post, brand_models.Brand.workspace_id)
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

    def _workspace_id(self, post: post_models.Post) -> UUID:
        workspace_id = self._session.scalar(
            select(brand_models.Brand.workspace_id)
            .join(
                content_plan_models.ContentPlan,
                content_plan_models.ContentPlan.brand_id == brand_models.Brand.id,
            )
            .where(content_plan_models.ContentPlan.id == post.content_plan_id)
        )
        if workspace_id is None:
            raise ValueError("Post structure workspace not found")
        return workspace_id

    def _record(self, post: post_models.Post, workspace_id: UUID) -> PostStructureRecord:
        design = self._session.scalar(
            select(post_models.PostDesign).where(post_models.PostDesign.post_id == post.id)
        )
        slide = None
        if design is not None:
            slide = self._session.scalar(
                select(post_models.DesignSlide)
                .where(post_models.DesignSlide.post_design_id == design.id)
                .order_by(post_models.DesignSlide.position)
            )
        ratio = design.ratio if design is not None else "RATIO_1_1"
        return PostStructureRecord(
            id=post.id,
            workspace_id=workspace_id,
            planning_id=post.content_plan_id,
            created_by=post.created_by,
            title=post.title,
            objective=post.objective,
            big_idea=post.big_idea,
            main_message=post.main_message,
            headline=slide.headline if slide is not None else None,
            image_cta=slide.cta if slide is not None else None,
            art_guiding=slide.art_direction if slide is not None else None,
            status=post.publication_status,
            format=design.format if design is not None else None,
            ratio=ratio,
            resolution=_resolution(ratio),
            created_at=post.created_at,
            updated_at=post.updated_at,
            deleted_at=post.deleted_at,
        )
