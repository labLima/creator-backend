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
from creator.api.responses import (
    success_response,
)
from creator.project import service
from creator.project.schemas import (
    ProjectCreateRequest,
    ProjectUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

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
    return success_response(
        service.list_projects(
            uow=unit_of_work,
            actor=current_user,
            workspace_id=workspace_id,
            brand_id=brand_id,
            page=page,
            limit=limit,
            sort=sort,
            request=request,
        ),
        request,
    )


@router.post("/api/v1/projects", tags=["Projects"])
def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_project(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/projects/{id}", tags=["Projects"])
def get_project(
    project_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_project(
            uow=unit_of_work, actor=current_user, project_id=project_id, request=request
        ),
        request,
    )


@router.put("/api/v1/projects/{id}", tags=["Projects"])
def update_project(
    project_id: Annotated[UUID, Path(alias="id")],
    payload: ProjectUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_project(
            uow=unit_of_work,
            actor=current_user,
            project_id=project_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/projects/{id}", tags=["Projects"])
def delete_project(
    project_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_project(
            uow=unit_of_work, actor=current_user, project_id=project_id, request=request
        ),
        request,
    )
