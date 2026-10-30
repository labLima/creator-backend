"""Use cases for the project capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.responses import page_payload
from creator.api.serializers import _project_data
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_projects(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
    brand_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    projects = uow.projects.list_for_user(
        user_id=actor.id,
        workspace_id=workspace_id,
        brand_id=brand_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(projects, _project_data)


def create_project(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    project = uow.projects.add(
        workspace_id=payload.workspace_id,
        brand_id=payload.brand_id,
        created_by_user_id=actor.id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        metadata=payload.metadata,
    )
    uow.commit()

    return _project_data(project)


def get_project(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    project_id: Any,
) -> Any:
    project = uow.projects.get_for_user(
        user_id=actor.id,
        project_id=project_id,
    )
    if project is None:
        raise not_found("Project")

    return _project_data(project)


def update_project(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    project_id: Any,
    payload: Any,
) -> Any:
    try:
        project = uow.projects.update(
            user_id=actor.id,
            project_id=project_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Project") from error
    uow.commit()

    return _project_data(project)


def delete_project(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    project_id: Any,
) -> Any:
    try:
        uow.projects.soft_delete(user_id=actor.id, project_id=project_id)
    except EntityNotFoundError as error:
        raise not_found("Project") from error
    uow.commit()

    return {"deleted": True}
