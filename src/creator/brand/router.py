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
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    page_payload,
    success_response,
)
from creator.api.serializers import (
    _brand_asset_data,
    _brand_color_data,
    _brand_data,
    _brand_settings_data,
)
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
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/brands", tags=["Brands"])
def list_brands(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    brands = unit_of_work.brands.list_for_user(
        user_id=current_user.id,
        workspace_id=workspace_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(brands, _brand_data), request)


@router.post("/api/v1/brands", tags=["Brands"])
def create_brand(
    payload: BrandCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    brand = unit_of_work.brands.add(
        workspace_id=payload.workspace_id,
        created_by_user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        brand_voice=payload.brand_voice,
        metadata=payload.metadata,
    )
    unit_of_work.commit()
    return success_response(_brand_data(brand), request, status_code=201)


@router.get("/api/v1/brands/{id}", tags=["Brands"])
def get_brand(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    brand = unit_of_work.brands.get_for_user(user_id=current_user.id, brand_id=brand_id)
    if brand is None:
        raise not_found("Brand")
    return success_response(_brand_data(brand), request)


@router.put("/api/v1/brands/{id}", tags=["Brands"])
def update_brand(
    brand_id: Annotated[UUID, Path(alias="id")],
    payload: BrandUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        brand = unit_of_work.brands.update(
            user_id=current_user.id,
            brand_id=brand_id,
            name=payload.name,
            description=payload.description,
            brand_voice=payload.brand_voice,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Brand") from error
    unit_of_work.commit()
    return success_response(_brand_data(brand), request)


@router.delete("/api/v1/brands/{id}", tags=["Brands"])
def delete_brand(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        unit_of_work.brands.soft_delete(user_id=current_user.id, brand_id=brand_id)
    except EntityNotFoundError as error:
        raise not_found("Brand") from error
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/brands/{id}/settings", tags=["Brands"])
def get_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    settings = unit_of_work.brand_settings.get_for_user(
        user_id=current_user.id,
        brand_id=brand_id,
    )
    if settings is None:
        raise not_found("Brand settings")
    return success_response(_brand_settings_data(settings), request)


@router.put("/api/v1/brands/{id}/settings", tags=["Brands"])
def upsert_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    payload: BrandSettingsUpsertRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    settings = unit_of_work.brand_settings.upsert(
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        brand_id=brand_id,
        voice_settings=payload.voice_settings,
        visual_settings=payload.visual_settings,
        generation_defaults=payload.generation_defaults,
        metadata=payload.metadata,
    )
    unit_of_work.commit()
    return success_response(_brand_settings_data(settings), request)


@router.patch("/api/v1/brands/{id}/settings", tags=["Brands"])
def update_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    payload: BrandSettingsUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        settings = unit_of_work.brand_settings.update(
            user_id=current_user.id,
            brand_id=brand_id,
            voice_settings=payload.voice_settings,
            visual_settings=payload.visual_settings,
            generation_defaults=payload.generation_defaults,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Brand settings") from error
    unit_of_work.commit()
    return success_response(_brand_settings_data(settings), request)


@router.delete("/api/v1/brands/{id}/settings", tags=["Brands"])
def delete_brand_settings(
    brand_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        unit_of_work.brand_settings.soft_delete(user_id=current_user.id, brand_id=brand_id)
    except EntityNotFoundError as error:
        raise not_found("Brand settings") from error
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/brand-assets", tags=["Brand Assets"])
def list_brand_assets(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    brand_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    result = unit_of_work.brand_assets.list_for_user(
        user_id=current_user.id,
        brand_id=brand_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(result, _brand_asset_data), request)


@router.post("/api/v1/brand-assets", tags=["Brand Assets"])
def create_brand_asset(
    payload: BrandAssetCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    brand = unit_of_work.brands.get_for_user(user_id=current_user.id, brand_id=payload.brand_id)
    if brand is None:
        raise not_found("Brand")
    require_workspace_write(unit_of_work, user_id=current_user.id, workspace_id=brand.workspace_id)
    asset = unit_of_work.brand_assets.add(
        brand_id=payload.brand_id,
        type=payload.type,
        file_url=payload.file_url,
        file_name=payload.file_name,
        description=payload.description,
    )
    unit_of_work.commit()
    return success_response(_brand_asset_data(asset), request, status_code=201)


@router.get("/api/v1/brand-assets/{id}", tags=["Brand Assets"])
def get_brand_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    asset = unit_of_work.brand_assets.get_for_user(user_id=current_user.id, asset_id=asset_id)
    if asset is None:
        raise not_found("Brand asset")
    return success_response(_brand_asset_data(asset), request)


@router.put("/api/v1/brand-assets/{id}", tags=["Brand Assets"])
def update_brand_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    payload: BrandAssetUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.brand_assets.get_for_user(user_id=current_user.id, asset_id=asset_id)
    if existing is None:
        raise not_found("Brand asset")
    brand = unit_of_work.brands.get_for_user(user_id=current_user.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Brand asset")
    require_workspace_write(unit_of_work, user_id=current_user.id, workspace_id=brand.workspace_id)
    updated = unit_of_work.brand_assets.update(
        asset_id=asset_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_brand_asset_data(updated), request)


@router.delete("/api/v1/brand-assets/{id}", tags=["Brand Assets"])
def delete_brand_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.brand_assets.get_for_user(user_id=current_user.id, asset_id=asset_id)
    if existing is None:
        raise not_found("Brand asset")
    brand = unit_of_work.brands.get_for_user(user_id=current_user.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Brand asset")
    require_workspace_write(unit_of_work, user_id=current_user.id, workspace_id=brand.workspace_id)
    unit_of_work.brand_assets.soft_delete(asset_id=asset_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/brand-colors", tags=["Brands"])
def list_brand_colors(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    brand_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _brand_color_data(x)
                for x in unit_of_work.brand_colors.list_for_user(
                    user_id=current_user.id, brand_id=brand_id
                )
            ]
        },
        request,
    )


@router.post("/api/v1/brand-colors", tags=["Brands"])
def create_brand_color(
    payload: BrandColorCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    data = payload.model_dump()
    data["created_by"] = current_user.id
    item = unit_of_work.brand_colors.add(fields=data)
    unit_of_work.commit()
    return success_response(_brand_color_data(item), request, status_code=201)


@router.get("/api/v1/brand-colors/{id}", tags=["Brands"])
def get_brand_color(
    color_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.brand_colors.get_for_user(user_id=current_user.id, color_id=color_id)
    if item is None:
        raise not_found("Brand color")
    return success_response(_brand_color_data(item), request)


@router.put("/api/v1/brand-colors/{id}", tags=["Brands"])
def update_brand_color(
    color_id: Annotated[UUID, Path(alias="id")],
    payload: BrandColorUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.brand_colors.get_for_user(user_id=current_user.id, color_id=color_id) is None:
        raise not_found("Brand color")
    item = unit_of_work.brand_colors.update(
        color_id=color_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_brand_color_data(item), request)


@router.delete("/api/v1/brand-colors/{id}", tags=["Brands"])
def delete_brand_color(
    color_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.brand_colors.get_for_user(user_id=current_user.id, color_id=color_id) is None:
        raise not_found("Brand color")
    unit_of_work.brand_colors.soft_delete(color_id=color_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
