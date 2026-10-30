"""HTTP routes for the project capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_uow,
)
from creator.api.dtos import (
    ProjectCreateRequest,
    ProjectUpdateRequest,
)
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    page_payload,
    success_response,
)
from creator.api.serializers import (
    _project_data,
)
from creator.application.unit_of_work import UnitOfWork
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.repositories import (
    UserRecord,
)

router = APIRouter()


@router.get("/api/v1/projects", tags=["Projects"])
def list_projects(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
    brand_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    projects = unit_of_work.projects.list_for_user(
        user_id=current_user.id,
        workspace_id=workspace_id,
        brand_id=brand_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(projects, _project_data), request)


@router.post("/api/v1/projects", tags=["Projects"])
def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    project = unit_of_work.projects.add(
        workspace_id=payload.workspace_id,
        brand_id=payload.brand_id,
        created_by_user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        metadata=payload.metadata,
    )
    unit_of_work.commit()
    return success_response(_project_data(project), request, status_code=201)


@router.get("/api/v1/projects/{id}", tags=["Projects"])
def get_project(
    project_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    project = unit_of_work.projects.get_for_user(
        user_id=current_user.id,
        project_id=project_id,
    )
    if project is None:
        raise not_found("Project")
    return success_response(_project_data(project), request)


@router.put("/api/v1/projects/{id}", tags=["Projects"])
def update_project(
    project_id: Annotated[UUID, Path(alias="id")],
    payload: ProjectUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        project = unit_of_work.projects.update(
            user_id=current_user.id,
            project_id=project_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Project") from error
    unit_of_work.commit()
    return success_response(_project_data(project), request)


@router.delete("/api/v1/projects/{id}", tags=["Projects"])
def delete_project(
    project_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        unit_of_work.projects.soft_delete(user_id=current_user.id, project_id=project_id)
    except EntityNotFoundError as error:
        raise not_found("Project") from error
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
