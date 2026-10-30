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
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    page_payload,
    success_response,
)
from creator.api.serializers import (
    _asset_data,
    _brand_asset_data,
)
from creator.application.unit_of_work import UnitOfWork
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.modules.asset.schemas import (
    AssetCreateRequest,
    AssetUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)

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
    assets = unit_of_work.assets.list_for_user(
        user_id=current_user.id,
        workspace_id=workspace_id,
        brand_id=brand_id,
        project_id=project_id,
        content_id=content_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(assets, _asset_data), request)


@router.post("/api/v1/assets", tags=["Assets"])
def create_asset(
    payload: AssetCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    asset = unit_of_work.assets.add(
        workspace_id=payload.workspace_id,
        brand_id=payload.brand_id,
        project_id=payload.project_id,
        content_id=payload.content_id,
        uploaded_by_user_id=current_user.id,
        asset_type=payload.asset_type,
        storage_path=payload.storage_path,
        public_url=payload.public_url,
        mime_type=payload.mime_type,
        byte_size=payload.byte_size,
        checksum=payload.checksum,
        metadata=payload.metadata,
    )
    unit_of_work.commit()
    return success_response(_asset_data(asset), request, status_code=201)


@router.get("/api/v1/assets/{id}", tags=["Assets"])
def get_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    brand_assets = getattr(unit_of_work, "brand_assets", None)
    brand_asset = (
        brand_assets.get_for_user(user_id=current_user.id, asset_id=asset_id)
        if brand_assets is not None
        else None
    )
    if brand_asset is not None:
        return success_response(_brand_asset_data(brand_asset), request)
    asset = unit_of_work.assets.get_for_user(user_id=current_user.id, asset_id=asset_id)
    if asset is None:
        raise not_found("Asset")
    return success_response(_asset_data(asset), request)


@router.put("/api/v1/assets/{id}", tags=["Assets"])
def update_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    payload: AssetUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        asset = unit_of_work.assets.update(
            user_id=current_user.id,
            asset_id=asset_id,
            asset_type=payload.asset_type,
            public_url=payload.public_url,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Asset") from error
    unit_of_work.commit()
    return success_response(_asset_data(asset), request)


@router.delete("/api/v1/assets/{id}", tags=["Assets"])
def delete_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        unit_of_work.assets.soft_delete(user_id=current_user.id, asset_id=asset_id)
    except EntityNotFoundError as error:
        raise not_found("Asset") from error
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
