"""HTTP routes for the workspace capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated, Any
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
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord
from creator.workspace import service
from creator.workspace.schemas import (
    WorkspaceCreateRequest,
    WorkspaceInviteCreateRequest,
    WorkspaceInviteUpdateRequest,
    WorkspaceUpdateRequest,
)

router = APIRouter()


@router.get("/api/v1/workspaces", tags=["Workspaces"], operation_id="listWorkspaces")
def list_workspaces(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_workspaces(
            uow=unit_of_work, actor=current_user, page=page, limit=limit, sort=sort, request=request
        ),
        request,
    )


@router.post("/api/v1/workspaces", tags=["Workspaces"], operation_id="createWorkspace")
def create_workspace(
    payload: WorkspaceCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_workspace(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/workspaces/{id}", tags=["Workspaces"], operation_id="getWorkspace")
def get_workspace(
    workspace_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_workspace(
            uow=unit_of_work, actor=current_user, workspace_id=workspace_id, request=request
        ),
        request,
    )


@router.put("/api/v1/workspaces/{id}", tags=["Workspaces"], operation_id="updateWorkspace")
def update_workspace(
    workspace_id: Annotated[UUID, Path(alias="id")],
    payload: WorkspaceUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_workspace(
            uow=unit_of_work,
            actor=current_user,
            workspace_id=workspace_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/workspaces/{id}", tags=["Workspaces"], operation_id="deleteWorkspace")
def delete_workspace(
    workspace_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_workspace(
            uow=unit_of_work, actor=current_user, workspace_id=workspace_id, request=request
        ),
        request,
    )


@router.get(
    "/api/v1/workspace-invites",
    tags=["Workspaces"],
    operation_id="list_workspace_invites_api_v1_workspace_invites_get",
)
def list_workspace_invites(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_workspace_invites(
            uow=unit_of_work, actor=current_user, workspace_id=workspace_id, request=request
        ),
        request,
    )


@router.post(
    "/api/v1/workspace-invites",
    tags=["Workspaces"],
    operation_id="create_workspace_invite_api_v1_workspace_invites_post",
)
def create_workspace_invite(
    payload: WorkspaceInviteCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_workspace_invite(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/workspace-invites/{id}",
    tags=["Workspaces"],
    operation_id="get_workspace_invite_api_v1_workspace_invites__id__get",
)
def get_workspace_invite(
    invite_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_workspace_invite(
            uow=unit_of_work, actor=current_user, invite_id=invite_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/workspace-invites/{id}",
    tags=["Workspaces"],
    operation_id="update_workspace_invite_api_v1_workspace_invites__id__put",
)
def update_workspace_invite(
    invite_id: Annotated[UUID, Path(alias="id")],
    payload: WorkspaceInviteUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_workspace_invite(
            uow=unit_of_work,
            actor=current_user,
            invite_id=invite_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/workspace-invites/{id}",
    tags=["Workspaces"],
    operation_id="delete_workspace_invite_api_v1_workspace_invites__id__delete",
)
def delete_workspace_invite(
    invite_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_workspace_invite(
            uow=unit_of_work, actor=current_user, invite_id=invite_id, request=request
        ),
        request,
    )


@router.get(
    "/api/v1/workspace-invite-usages",
    tags=["Workspaces"],
    operation_id="list_workspace_invite_usages_api_v1_workspace_invite_usages_get",
)
def list_workspace_invite_usages(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_workspace_invite_usages(
            uow=unit_of_work, actor=current_user, workspace_id=workspace_id, request=request
        ),
        request,
    )


@router.post(
    "/api/v1/workspace-invite-usages",
    tags=["Workspaces"],
    operation_id="create_workspace_invite_usage_api_v1_workspace_invite_usages_post",
)
def create_workspace_invite_usage(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_workspace_invite_usage(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/workspace-invite-usages/{id}",
    tags=["Workspaces"],
    operation_id="get_workspace_invite_usage_api_v1_workspace_invite_usages__id__get",
)
def get_workspace_invite_usage(
    usage_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_workspace_invite_usage(
            uow=unit_of_work, actor=current_user, usage_id=usage_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/workspace-invite-usages/{id}",
    tags=["Workspaces"],
    operation_id="update_workspace_invite_usage_api_v1_workspace_invite_usages__id__put",
)
def update_workspace_invite_usage(
    usage_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_workspace_invite_usage(
            uow=unit_of_work,
            actor=current_user,
            usage_id=usage_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/workspace-invite-usages/{id}",
    tags=["Workspaces"],
    operation_id="delete_workspace_invite_usage_api_v1_workspace_invite_usages__id__delete",
)
def delete_workspace_invite_usage(
    usage_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_workspace_invite_usage(
            uow=unit_of_work, actor=current_user, usage_id=usage_id, request=request
        ),
        request,
    )
