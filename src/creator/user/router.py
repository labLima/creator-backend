"""HTTP routes for the user capability.

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
from creator.uow import UnitOfWork
from creator.user import service
from creator.user.ports import UserRecord
from creator.user.schemas import (
    SettingsUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)

router = APIRouter()


@router.get("/api/v1/users/me", tags=["Users"])
def get_my_profile(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_my_profile(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.get("/api/v1/settings", tags=["Settings"])
def get_my_settings(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_my_settings(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.patch("/api/v1/settings", tags=["Settings"])
def update_my_settings(
    payload: SettingsUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_my_settings(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
    )


@router.get("/api/v1/users", tags=["Users"])
def list_users(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_users(
            uow=unit_of_work, actor=current_user, page=page, limit=limit, sort=sort, request=request
        ),
        request,
    )


@router.post("/api/v1/users", tags=["Users"])
def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_user(uow=unit_of_work, actor=current_user, payload=payload, request=request),
        request,
        status_code=201,
    )


@router.get("/api/v1/users/{id}", tags=["Users"])
def get_user(
    user_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_user(uow=unit_of_work, actor=current_user, user_id=user_id, request=request),
        request,
    )


@router.put("/api/v1/users/{id}", tags=["Users"])
def update_user(
    user_id: Annotated[UUID, Path(alias="id")],
    payload: UserUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_user(
            uow=unit_of_work, actor=current_user, user_id=user_id, payload=payload, request=request
        ),
        request,
    )


@router.delete("/api/v1/users/{id}", tags=["Users"])
def delete_user(
    user_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_user(uow=unit_of_work, actor=current_user, user_id=user_id, request=request),
        request,
    )
