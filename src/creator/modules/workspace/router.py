"""HTTP routes for the workspace capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_uow,
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
    _workspace_data,
    _workspace_invite_data,
    _workspace_invite_usage_data,
    _workspace_membership_data,
)
from creator.application.unit_of_work import UnitOfWork
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.modules.workspace.schemas import (
    WorkspaceCreateRequest,
    WorkspaceInviteCreateRequest,
    WorkspaceInviteUpdateRequest,
    WorkspaceUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)

router = APIRouter()


@router.get("/api/v1/workspaces", tags=["Workspaces"])
def list_workspaces(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    workspaces = unit_of_work.workspaces.list_for_user(
        user_id=current_user.id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(workspaces, _workspace_data), request)


@router.post("/api/v1/workspaces", tags=["Workspaces"])
def create_workspace(
    payload: WorkspaceCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    created = unit_of_work.workspaces.create_for_user(
        user_id=current_user.id,
        name=payload.name,
    )
    unit_of_work.commit()
    return success_response(
        {
            "workspace": _workspace_data(created.workspace),
            "membership": _workspace_membership_data(created.membership),
        },
        request,
        status_code=201,
    )


@router.get("/api/v1/workspaces/{id}", tags=["Workspaces"])
def get_workspace(
    workspace_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    workspace = unit_of_work.workspaces.get_for_user(
        user_id=current_user.id,
        workspace_id=workspace_id,
    )
    if workspace is None:
        raise not_found("Workspace")
    return success_response(_workspace_data(workspace), request)


@router.put("/api/v1/workspaces/{id}", tags=["Workspaces"])
def update_workspace(
    workspace_id: Annotated[UUID, Path(alias="id")],
    payload: WorkspaceUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        workspace = unit_of_work.workspaces.update(
            user_id=current_user.id,
            workspace_id=workspace_id,
            name=payload.name,
        )
    except EntityNotFoundError as error:
        raise not_found("Workspace") from error
    unit_of_work.commit()
    return success_response(_workspace_data(workspace), request)


@router.delete("/api/v1/workspaces/{id}", tags=["Workspaces"])
def delete_workspace(
    workspace_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        workspace = unit_of_work.workspaces.soft_delete_for_user(
            user_id=current_user.id,
            workspace_id=workspace_id,
        )
    except EntityNotFoundError as error:
        raise not_found("Workspace") from error
    unit_of_work.commit()
    return success_response({"workspace": _workspace_data(workspace)}, request)


@router.get("/api/v1/workspace-invites", tags=["Workspaces"])
def list_workspace_invites(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _workspace_invite_data(x)
                for x in unit_of_work.workspace_invites.list_for_user(
                    user_id=current_user.id, workspace_id=workspace_id
                )
            ]
        },
        request,
    )


@router.post("/api/v1/workspace-invites", tags=["Workspaces"])
def create_workspace_invite(
    payload: WorkspaceInviteCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    item = unit_of_work.workspace_invites.add(
        **payload.model_dump(), created_by=current_user.id, token=uuid4().hex
    )
    unit_of_work.commit()
    return success_response(_workspace_invite_data(item), request, status_code=201)


@router.get("/api/v1/workspace-invites/{id}", tags=["Workspaces"])
def get_workspace_invite(
    invite_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.workspace_invites.get_for_user(user_id=current_user.id, invite_id=invite_id)
    if item is None:
        raise not_found("Workspace invite")
    return success_response(_workspace_invite_data(item), request)


@router.put("/api/v1/workspace-invites/{id}", tags=["Workspaces"])
def update_workspace_invite(
    invite_id: Annotated[UUID, Path(alias="id")],
    payload: WorkspaceInviteUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.workspace_invites.get_for_user(user_id=current_user.id, invite_id=invite_id)
        is None
    ):
        raise not_found("Workspace invite")
    item = unit_of_work.workspace_invites.update(
        invite_id=invite_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_workspace_invite_data(item), request)


@router.delete("/api/v1/workspace-invites/{id}", tags=["Workspaces"])
def delete_workspace_invite(
    invite_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.workspace_invites.get_for_user(user_id=current_user.id, invite_id=invite_id)
        is None
    ):
        raise not_found("Workspace invite")
    unit_of_work.workspace_invites.soft_delete(invite_id=invite_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/workspace-invite-usages", tags=["Workspaces"])
def list_workspace_invite_usages(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _workspace_invite_usage_data(x)
                for x in unit_of_work.workspace_invite_usages.list_for_user(
                    user_id=current_user.id, workspace_id=workspace_id
                )
            ]
        },
        request,
    )


@router.post("/api/v1/workspace-invite-usages", tags=["Workspaces"])
def create_workspace_invite_usage(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    payload["user_id"] = current_user.id
    item = unit_of_work.workspace_invite_usages.add(fields=payload)
    unit_of_work.commit()
    return success_response(_workspace_invite_usage_data(item), request, status_code=201)


@router.get("/api/v1/workspace-invite-usages/{id}", tags=["Workspaces"])
def get_workspace_invite_usage(
    usage_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.workspace_invite_usages.get_for_user(
        user_id=current_user.id, usage_id=usage_id
    )
    if item is None:
        raise not_found("Workspace invite usage")
    return success_response(_workspace_invite_usage_data(item), request)


@router.put("/api/v1/workspace-invite-usages/{id}", tags=["Workspaces"])
def update_workspace_invite_usage(
    usage_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.workspace_invite_usages.get_for_user(
            user_id=current_user.id, usage_id=usage_id
        )
        is None
    ):
        raise not_found("Workspace invite usage")
    item = unit_of_work.workspace_invite_usages.update(usage_id=usage_id, fields=payload)
    unit_of_work.commit()
    return success_response(_workspace_invite_usage_data(item), request)


@router.delete("/api/v1/workspace-invite-usages/{id}", tags=["Workspaces"])
def delete_workspace_invite_usage(
    usage_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.workspace_invite_usages.get_for_user(
            user_id=current_user.id, usage_id=usage_id
        )
        is None
    ):
        raise not_found("Workspace invite usage")
    unit_of_work.workspace_invite_usages.soft_delete(usage_id=usage_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
