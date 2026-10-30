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
from creator.api.errors import (
    not_found,
    require_admin,
)
from creator.api.responses import (
    page_payload,
    success_response,
)
from creator.api.serializers import (
    _settings_data,
    _user_data,
)
from creator.application.unit_of_work import UnitOfWork
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.modules.user.schemas import (
    SettingsUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)

router = APIRouter()


@router.get("/api/v1/users/me", tags=["Users"])
def get_my_profile(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
) -> JSONResponse:
    return success_response(_user_data(current_user), request)


@router.get("/api/v1/settings", tags=["Settings"])
def get_my_settings(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    settings = unit_of_work.settings.get_or_create_for_user(current_user.id)
    unit_of_work.commit()
    return success_response(_settings_data(settings), request)


@router.patch("/api/v1/settings", tags=["Settings"])
def update_my_settings(
    payload: SettingsUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    unit_of_work.settings.get_or_create_for_user(current_user.id)
    changes = payload.model_dump(exclude_unset=True)
    settings = unit_of_work.settings.update_partial(current_user.id, changes)
    unit_of_work.commit()
    return success_response(_settings_data(settings), request)


@router.get("/api/v1/users", tags=["Users"])
def list_users(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    require_admin(current_user)
    users = unit_of_work.users.list(page=page_request(page, limit, sort))
    return success_response(page_payload(users, _user_data), request)


@router.post("/api/v1/users", tags=["Users"])
def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_admin(current_user)
    user = unit_of_work.users.add(
        external_id=payload.external_id,
        email=payload.email,
        display_name=payload.display_name,
        global_role=payload.global_role,
    )
    unit_of_work.commit()
    return success_response(_user_data(user), request, status_code=201)


@router.get("/api/v1/users/{id}", tags=["Users"])
def get_user(
    user_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_admin(current_user)
    user = unit_of_work.users.get_by_id(user_id)
    if user is None:
        raise not_found("User")
    return success_response(_user_data(user), request)


@router.put("/api/v1/users/{id}", tags=["Users"])
def update_user(
    user_id: Annotated[UUID, Path(alias="id")],
    payload: UserUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_admin(current_user)
    try:
        user = unit_of_work.users.update(
            user_id,
            email=payload.email,
            display_name=payload.display_name,
            global_role=payload.global_role,
        )
    except EntityNotFoundError as error:
        raise not_found("User") from error
    unit_of_work.commit()
    return success_response(_user_data(user), request)


@router.delete("/api/v1/users/{id}", tags=["Users"])
def delete_user(
    user_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_admin(current_user)
    try:
        unit_of_work.users.soft_delete(user_id)
    except EntityNotFoundError as error:
        raise not_found("User") from error
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
