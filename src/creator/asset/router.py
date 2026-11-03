"""HTTP routes for the asset capability.

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
from creator.asset import service
from creator.asset.schemas import (
    AssetCreateRequest,
    AssetUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/assets", tags=["Assets"])
def list_assets(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
    brand_id: UUID | None = None,
    project_id: UUID | None = None,
    content_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_assets(
            uow=unit_of_work,
            actor=current_user,
            workspace_id=workspace_id,
            brand_id=brand_id,
            project_id=project_id,
            content_id=content_id,
            page=page,
            limit=limit,
            sort=sort,
            request=request,
        ),
        request,
    )


@router.post("/api/v1/assets", tags=["Assets"])
def create_asset(
    payload: AssetCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_asset(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/assets/{id}", tags=["Assets"])
def get_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_asset(uow=unit_of_work, actor=current_user, asset_id=asset_id, request=request),
        request,
    )


@router.put("/api/v1/assets/{id}", tags=["Assets"])
def update_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    payload: AssetUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_asset(
            uow=unit_of_work,
            actor=current_user,
            asset_id=asset_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/assets/{id}", tags=["Assets"])
def delete_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_asset(
            uow=unit_of_work, actor=current_user, asset_id=asset_id, request=request
        ),
        request,
    )
