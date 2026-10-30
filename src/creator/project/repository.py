"""SQLAlchemy repositories for the project capability."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.orm import Session

from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.domain.exceptions import EntityNotFoundError
from creator.infrastructure.persistence.sql import as_datetime as _datetime
from creator.infrastructure.persistence.sql import as_optional_datetime as _optional_datetime
from creator.infrastructure.persistence.sql import flush_or_raise, user_has_workspace_role
from creator.infrastructure.persistence.sql import json_object as _json
from creator.infrastructure.persistence.sql import now as _now
from creator.infrastructure.persistence.sql import paginate as _page
from creator.infrastructure.persistence.sql import scoped_resource_count as _scoped_resource_count
from creator.infrastructure.persistence.sql import scoped_resource_select as _scoped_resource_select
from creator.project import models as project_tables
from creator.project.ports import ProjectRecord


def _project_record(row: project_tables.Project) -> ProjectRecord:
    return ProjectRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        brand_id=row.brand_id,
        created_by_user_id=row.created_by_user_id,
        name=row.name,
        description=row.description,
        status=row.status,
        metadata=_json(row.metadata_json),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


def _user_has_workspace_role(
    session: Session,
    *,
    user_id: UUID,
    workspace_id: UUID,
    minimum_role: str = "viewer",
) -> bool:
    return user_has_workspace_role(
        session,
        user_id=user_id,
        workspace_id=workspace_id,
        minimum_role=minimum_role,
    )


class SqlAlchemyProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        workspace_id: UUID,
        brand_id: UUID | None,
        created_by_user_id: UUID | None,
        name: str,
        description: str | None = None,
        status: str = "ACTIVE",
        metadata: JsonObject | None = None,
    ) -> ProjectRecord:
        if created_by_user_id is not None and not _user_has_workspace_role(
            self._session,
            user_id=created_by_user_id,
            workspace_id=workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Workspace not found")
        row = project_tables.Project(
            workspace_id=workspace_id,
            brand_id=brand_id,
            created_by_user_id=created_by_user_id,
            name=name,
            description=description,
            status=status,
            metadata_json=_json(metadata),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _project_record(row)

    def get_for_user(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        include_deleted: bool = False,
    ) -> ProjectRecord | None:
        statement = self._scoped_select(user_id).where(project_tables.Project.id == project_id)
        if not include_deleted:
            statement = statement.where(project_tables.Project.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _project_record(row) if row else None

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        brand_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[ProjectRecord]:
        page = page or PageRequest()
        statement = self._scoped_select(user_id).where(project_tables.Project.deleted_at.is_(None))
        count_statement = self._scoped_count(user_id).where(
            project_tables.Project.deleted_at.is_(None)
        )
        if workspace_id is not None:
            statement = statement.where(project_tables.Project.workspace_id == workspace_id)
            count_statement = count_statement.where(
                project_tables.Project.workspace_id == workspace_id
            )
        if brand_id is not None:
            statement = statement.where(project_tables.Project.brand_id == brand_id)
            count_statement = count_statement.where(project_tables.Project.brand_id == brand_id)
        rows, total = _page(
            self._session, statement, count_statement, project_tables.Project.created_at, page
        )
        return Page(
            items=[_project_record(row) for row in rows],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def update(
        self,
        *,
        user_id: UUID,
        project_id: UUID,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        metadata: JsonObject | None = None,
    ) -> ProjectRecord:
        row = self._writable_project(user_id=user_id, project_id=project_id)
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        if status is not None:
            row.status = status
        if metadata is not None:
            row.metadata_json = _json(metadata)
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _project_record(row)

    def soft_delete(self, *, user_id: UUID, project_id: UUID) -> None:
        row = self._writable_project(user_id=user_id, project_id=project_id)
        timestamp = _now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        flush_or_raise(self._session)

    def _writable_project(self, *, user_id: UUID, project_id: UUID) -> project_tables.Project:
        row = self._session.scalars(
            self._scoped_select(user_id).where(
                project_tables.Project.id == project_id,
                project_tables.Project.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None or not _user_has_workspace_role(
            self._session,
            user_id=user_id,
            workspace_id=row.workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Project not found")
        return cast(project_tables.Project, row)

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_select(user_id, project_tables.Project)

    def _scoped_count(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_count(user_id, project_tables.Project)
