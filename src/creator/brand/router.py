"""HTTP routes for the brand capability.

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
from creator.brand import service
from creator.brand.schemas import (
    BrandAssetCreateRequest,
    BrandAssetUpdateRequest,
    BrandColorCreateRequest,
    BrandColorUpdateRequest,
    BrandCreateRequest,
    BrandSettingsUpdateRequest,
    BrandSettingsUpsertRequest,
    BrandUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/brands", tags=["Brands"], operation_id="listBrands")
def list_brands(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_brands(
            uow=unit_of_work,
            actor=current_user,
            workspace_id=workspace_id,
            page=page,
            limit=limit,
            sort=sort,
            request=request,
        ),
        request,
    )


@router.post(
    "/api/v1/brands",
    tags=["Brands"],
    operation_id="createBrand",
    responses={"403": {"$ref": "#/components/responses/WorkspaceAccessDenied"}},
)
def create_brand(
    payload: BrandCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_brand(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/brands/{id}",
    tags=["Brands"],
    operation_id="getBrand",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_brand(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_brand(uow=unit_of_work, actor=current_user, brand_id=brand_id, request=request),
        request,
    )


@router.put(
    "/api/v1/brands/{id}",
    tags=["Brands"],
    operation_id="updateBrand",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def update_brand(
    brand_id: Annotated[UUID, Path(alias="id")],
    payload: BrandUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_brand(
            uow=unit_of_work,
            actor=current_user,
            brand_id=brand_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/brands/{id}",
    tags=["Brands"],
    operation_id="deleteBrand",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def delete_brand(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_brand(
            uow=unit_of_work, actor=current_user, brand_id=brand_id, request=request
        ),
        request,
    )


@router.get(
    "/api/v1/brands/{id}/settings",
    tags=["Brands"],
    operation_id="getBrandSettings",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_brand_settings(
            uow=unit_of_work, actor=current_user, brand_id=brand_id, request=request
        ),
        request,
    )


@router.put("/api/v1/brands/{id}/settings", tags=["Brands"], operation_id="upsertBrandSettings")
def upsert_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    payload: BrandSettingsUpsertRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.upsert_brand_settings(
            uow=unit_of_work,
            actor=current_user,
            brand_id=brand_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.patch("/api/v1/brands/{id}/settings", tags=["Brands"], operation_id="updateBrandSettings")
def update_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    payload: BrandSettingsUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_brand_settings(
            uow=unit_of_work,
            actor=current_user,
            brand_id=brand_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/brands/{id}/settings", tags=["Brands"], operation_id="deleteBrandSettings")
def delete_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_brand_settings(
            uow=unit_of_work, actor=current_user, brand_id=brand_id, request=request
        ),
        request,
    )


@router.get("/api/v1/brand-assets", tags=["Brand Assets"], operation_id="listBrandAssets")
def list_brand_assets(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    brand_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_brand_assets(
            uow=unit_of_work,
            actor=current_user,
            brand_id=brand_id,
            page=page,
            limit=limit,
            sort=sort,
            request=request,
        ),
        request,
    )


@router.post("/api/v1/brand-assets", tags=["Brand Assets"], operation_id="createBrandAsset")
def create_brand_asset(
    payload: BrandAssetCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_brand_asset(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/brand-assets/{id}",
    tags=["Brand Assets"],
    operation_id="getBrandAsset",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_brand_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_brand_asset(
            uow=unit_of_work, actor=current_user, asset_id=asset_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/brand-assets/{id}",
    tags=["Brand Assets"],
    operation_id="updateBrandAsset",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def update_brand_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    payload: BrandAssetUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_brand_asset(
            uow=unit_of_work,
            actor=current_user,
            asset_id=asset_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/brand-assets/{id}",
    tags=["Brand Assets"],
    operation_id="deleteBrandAsset",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def delete_brand_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_brand_asset(
            uow=unit_of_work, actor=current_user, asset_id=asset_id, request=request
        ),
        request,
    )


@router.get(
    "/api/v1/brand-colors",
    tags=["Brands"],
    operation_id="list_brand_colors_api_v1_brand_colors_get",
)
def list_brand_colors(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    brand_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_brand_colors(
            uow=unit_of_work, actor=current_user, brand_id=brand_id, request=request
        ),
        request,
    )


@router.post(
    "/api/v1/brand-colors",
    tags=["Brands"],
    operation_id="create_brand_color_api_v1_brand_colors_post",
)
def create_brand_color(
    payload: BrandColorCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_brand_color(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/brand-colors/{id}",
    tags=["Brands"],
    operation_id="get_brand_color_api_v1_brand_colors__id__get",
)
def get_brand_color(
    color_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_brand_color(
            uow=unit_of_work, actor=current_user, color_id=color_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/brand-colors/{id}",
    tags=["Brands"],
    operation_id="update_brand_color_api_v1_brand_colors__id__put",
)
def update_brand_color(
    color_id: Annotated[UUID, Path(alias="id")],
    payload: BrandColorUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_brand_color(
            uow=unit_of_work,
            actor=current_user,
            color_id=color_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/brand-colors/{id}",
    tags=["Brands"],
    operation_id="delete_brand_color_api_v1_brand_colors__id__delete",
)
def delete_brand_color(
    color_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_brand_color(
            uow=unit_of_work, actor=current_user, color_id=color_id, request=request
        ),
        request,
    )
