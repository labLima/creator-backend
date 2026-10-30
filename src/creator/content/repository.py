"""SQLAlchemy repositories for the content capability."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, Text, and_, asc, desc, func, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.orm import Session

from creator.content import models as content_tables
from creator.content.ports import (
    ContentDetailRecord,
    ContentFilters,
    ContentRecord,
    GeneratedTextContentRecord,
    ImageRecord,
)
from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.domain.exceptions import EntityNotFoundError
from creator.generation import models as generation_tables
from creator.infrastructure.database.enums import ContentType, GenerationType
from creator.infrastructure.persistence.sql import as_datetime as _datetime
from creator.infrastructure.persistence.sql import as_optional_datetime as _optional_datetime
from creator.infrastructure.persistence.sql import enum_value as _enum_value
from creator.infrastructure.persistence.sql import flush_or_raise
from creator.infrastructure.persistence.sql import json_object as _json
from creator.infrastructure.persistence.sql import now as _now
from creator.workspace import models as workspace_tables


def _content_record(row: content_tables.Content) -> ContentRecord:
    return ContentRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        created_by_user_id=row.created_by_user_id,
        content_type=_enum_value(row.content_type),
        title=row.title,
        payload=_json(row.payload),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
        brand_id=row.brand_id,
        project_id=row.project_id,
    )


def _image_record(row: content_tables.Image) -> ImageRecord:
    return ImageRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        content_id=row.content_id,
        generation_id=row.generation_id,
        version_number=row.version_number,
        storage_path=row.storage_path,
        public_url=row.public_url,
        mime_type=row.mime_type,
        width=row.width,
        height=row.height,
        model=row.model,
        prompt=row.prompt,
        metadata=_json(row.metadata_json),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


class SqlAlchemyContentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID | None,
        content_type: str = "IMAGE",
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        title: str | None = None,
        payload: JsonObject | None = None,
    ) -> ContentRecord:
        row = content_tables.Content(
            workspace_id=workspace_id,
            created_by_user_id=created_by_user_id,
            content_type=content_type,
            brand_id=brand_id,
            project_id=project_id,
            title=title,
            payload=_json(payload),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _content_record(row)

    def create_text_generation(
        self,
        *,
        workspace_id: UUID,
        requested_by_user_id: UUID,
        title: str,
        payload: JsonObject,
        model: str,
        prompt: str,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        parameters: JsonObject | None = None,
    ) -> GeneratedTextContentRecord:
        if not self.user_has_workspace_access(
            user_id=requested_by_user_id,
            workspace_id=workspace_id,
        ):
            raise EntityNotFoundError("Workspace not found")

        content = content_tables.Content(
            workspace_id=workspace_id,
            created_by_user_id=requested_by_user_id,
            content_type=ContentType.TEXT,
            brand_id=brand_id,
            project_id=project_id,
            title=title,
            payload=_json(payload),
        )
        self._session.add(content)
        flush_or_raise(self._session)

        generation = generation_tables.Generation(
            workspace_id=workspace_id,
            content_id=content.id,
            requested_by_user_id=requested_by_user_id,
            generation_type=GenerationType.TEXT,
            brand_id=brand_id,
            project_id=project_id,
            model=model,
            prompt=prompt,
            parameters=_json(parameters),
        )
        self._session.add(generation)
        flush_or_raise(self._session)

        return GeneratedTextContentRecord(
            content=_content_record(content),
            generation_id=generation.id,
            generation_model=model,
            generation_parameters=_json(generation.parameters),
        )

    def user_has_workspace_access(self, *, user_id: UUID, workspace_id: UUID) -> bool:
        statement = (
            select(func.count())
            .select_from(workspace_tables.WorkspaceMembership)
            .join(
                workspace_tables.Workspace,
                and_(
                    workspace_tables.Workspace.id
                    == workspace_tables.WorkspaceMembership.workspace_id,
                    workspace_tables.Workspace.deleted_at.is_(None),
                ),
            )
            .where(
                workspace_tables.WorkspaceMembership.user_id == user_id,
                workspace_tables.WorkspaceMembership.workspace_id == workspace_id,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
            )
        )
        return self._session.execute(statement).scalar_one() > 0

    def get_by_id_for_user(
        self,
        *,
        user_id: UUID,
        content_id: UUID,
        include_deleted: bool = False,
    ) -> ContentRecord | None:
        statement = self._scoped_select(user_id).where(content_tables.Content.id == content_id)
        if not include_deleted:
            statement = statement.where(content_tables.Content.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _content_record(row) if row else None

    def get_detail_by_id_for_user(
        self,
        *,
        user_id: UUID,
        content_id: UUID,
    ) -> ContentDetailRecord | None:
        content = self.get_by_id_for_user(user_id=user_id, content_id=content_id)
        if content is None:
            return None
        images = self._session.scalars(
            select(content_tables.Image)
            .where(
                content_tables.Image.content_id == content.id,
                content_tables.Image.workspace_id == content.workspace_id,
                content_tables.Image.deleted_at.is_(None),
            )
            .order_by(content_tables.Image.version_number.desc(), content_tables.Image.id.desc())
        ).all()
        return ContentDetailRecord(
            content=content,
            images=[_image_record(image) for image in images],
        )

    def list_for_user(
        self,
        *,
        user_id: UUID,
        filters: ContentFilters | None = None,
        page: PageRequest | None = None,
    ) -> Page[ContentRecord]:
        filters = filters or ContentFilters()
        page = page or PageRequest()
        statement = self._apply_content_filters(self._scoped_select(user_id), filters)
        count_statement = self._apply_content_filters(self._scoped_count(user_id), filters)
        order_column = (
            asc(content_tables.Content.created_at)
            if page.sort == "asc"
            else desc(content_tables.Content.created_at)
        )
        id_order = (
            asc(content_tables.Content.id)
            if page.sort == "asc"
            else desc(content_tables.Content.id)
        )
        rows = self._session.scalars(
            statement.order_by(order_column, id_order).offset(page.offset).limit(page.limit)
        ).all()
        total: int = self._session.execute(count_statement).scalar_one()
        return Page(
            items=[_content_record(row) for row in rows],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def update(
        self,
        content_id: UUID,
        *,
        user_id: UUID,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        title: str | None = None,
        payload: JsonObject | None = None,
    ) -> ContentRecord:
        row = self._session.scalars(
            self._scoped_select(user_id).where(
                content_tables.Content.id == content_id,
                content_tables.Content.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Content not found")
        if title is not None:
            row.title = title
        if brand_id is not None:
            row.brand_id = brand_id
        if project_id is not None:
            row.project_id = project_id
        if payload is not None:
            row.payload = _json(payload)
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _content_record(row)

    def soft_delete(self, *, user_id: UUID, content_id: UUID) -> None:
        row = self._session.scalars(
            self._scoped_select(user_id).where(content_tables.Content.id == content_id)
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Content not found")
        if row.deleted_at is not None:
            return
        timestamp = _now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        flush_or_raise(self._session)

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return (
            select(content_tables.Content)
            .join(
                workspace_tables.WorkspaceMembership,
                and_(
                    workspace_tables.WorkspaceMembership.workspace_id
                    == content_tables.Content.workspace_id,
                    workspace_tables.WorkspaceMembership.user_id == user_id,
                    workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                ),
            )
            .where(workspace_tables.WorkspaceMembership.deleted_at.is_(None))
        )

    def _scoped_count(self, user_id: UUID) -> Select[Any]:
        return (
            select(func.count())
            .select_from(content_tables.Content)
            .join(
                workspace_tables.WorkspaceMembership,
                and_(
                    workspace_tables.WorkspaceMembership.workspace_id
                    == content_tables.Content.workspace_id,
                    workspace_tables.WorkspaceMembership.user_id == user_id,
                    workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                ),
            )
        )

    def _apply_content_filters(
        self,
        statement: Select[Any],
        filters: ContentFilters,
    ) -> Select[Any]:
        if not filters.include_deleted:
            statement = statement.where(content_tables.Content.deleted_at.is_(None))
        if filters.workspace_id is not None:
            statement = statement.where(content_tables.Content.workspace_id == filters.workspace_id)
        if filters.content_type is not None:
            statement = statement.where(content_tables.Content.content_type == filters.content_type)
        if filters.query is not None:
            query = filters.query.strip()
            if query:
                pattern = f"%{query.lower()}%"
                search_text = func.lower(
                    func.coalesce(content_tables.Content.title, "")
                    + " "
                    + sql_cast(content_tables.Content.payload, Text)
                )
                statement = statement.where(search_text.like(pattern))
        if filters.created_from is not None:
            statement = statement.where(content_tables.Content.created_at >= filters.created_from)
        if filters.created_to is not None:
            statement = statement.where(content_tables.Content.created_at <= filters.created_to)
        return statement
