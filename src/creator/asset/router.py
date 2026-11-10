"""HTTP routes for the asset capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError

from creator.api.dependencies import (
    get_current_user,
    get_storage_provider,
    get_uow,
)
from creator.api.responses import (
    success_response,
)
from creator.asset import service
from creator.asset.ports import AssetRecord
from creator.asset.schemas import (
    AssetCreateRequest,
    AssetUpdateRequest,
)
from creator.config import Settings, get_settings
from creator.services.storage.provider import StorageProvider, UploadObjectRequest
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.post(
    "/api/v1/assets/reference-images",
    tags=["Assets"],
    operation_id="uploadReferenceImage",
    status_code=201,
    responses={"503": {"description": "Reference image storage or registration is unavailable."}},
)
async def upload_reference_image(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
    workspace_id: Annotated[UUID, Form()],
    brand_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
) -> JSONResponse:
    from creator.application.errors import require_workspace_write

    brand = unit_of_work.brand.brands.get_for_user(user_id=current_user.id, brand_id=brand_id)
    if brand is None or brand.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404, detail={"code": "BRAND_NOT_FOUND", "message": "Brand not found"}
        )
    require_workspace_write(unit_of_work, user_id=current_user.id, workspace_id=workspace_id)
    content = await file.read(min(settings.storage_max_object_bytes, 10 * 1024 * 1024) + 1)
    await file.close()
    if len(content) > min(settings.storage_max_object_bytes, 10 * 1024 * 1024):
        raise HTTPException(
            status_code=413,
            detail={"code": "IMAGE_TOO_LARGE", "message": "Image exceeds the upload limit"},
        )
    try:
        with Image.open(BytesIO(content)) as image:
            detected = Image.MIME.get(image.format or "")
            width, height = image.size
            image.verify()
        expected = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
        if detected not in expected or file.content_type != detected or width < 1 or height < 1:
            raise ValueError("invalid image")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_REFERENCE_IMAGE", "message": "Reference image is invalid"},
        ) from error
    asset_id = uuid4()
    extension = expected[detected].lower()
    path = f"workspaces/{workspace_id}/brands/{brand_id}/references/{asset_id}.{extension}"
    checksum = hashlib.sha256(content).hexdigest()
    try:
        stored = storage.upload(
            UploadObjectRequest(
                path=path, content=content, mime_type=str(detected), checksum_sha256=checksum
            )
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "REFERENCE_IMAGE_STORAGE_UNAVAILABLE",
                "message": "Reference image could not be stored",
            },
        ) from None
    try:
        record = unit_of_work.assets.add(
            workspace_id=workspace_id,
            brand_id=brand_id,
            uploaded_by_user_id=current_user.id,
            asset_type="REFERENCE_IMAGE",
            storage_path=path,
            mime_type=str(detected),
            byte_size=len(content),
            checksum=checksum,
            metadata={"reference_image_upload": True, "width": width, "height": height},
        )
        unit_of_work.commit()
    except Exception:
        try:
            storage.delete(stored.path)
        except Exception:
            pass
        raise HTTPException(
            status_code=503,
            detail={
                "code": "REFERENCE_IMAGE_PERSISTENCE_FAILED",
                "message": "Reference image could not be registered",
            },
        ) from None
    return success_response(service_data(record), request, status_code=201)


def service_data(record: AssetRecord) -> dict[str, object]:
    from creator.application.serializers import _asset_data

    return _asset_data(record)


@router.get("/api/v1/assets", tags=["Assets"], operation_id="listAssets")
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


@router.post("/api/v1/assets", tags=["Assets"], operation_id="createAsset")
def create_asset(
    payload: AssetCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if payload.asset_type == "REFERENCE_IMAGE":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "REFERENCE_IMAGE_UPLOAD_REQUIRED",
                "message": "Use the reference image upload endpoint",
            },
        )
    return success_response(
        service.create_asset(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/assets/{id}", tags=["Assets"], operation_id="getAsset")
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


@router.put("/api/v1/assets/{id}", tags=["Assets"], operation_id="updateAsset")
def update_asset(
    asset_id: Annotated[UUID, Path(alias="id")],
    payload: AssetUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if payload.asset_type == "REFERENCE_IMAGE":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "REFERENCE_IMAGE_TYPE_RESERVED",
                "message": "Reference image type is reserved",
            },
        )
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


@router.delete("/api/v1/assets/{id}", tags=["Assets"], operation_id="deleteAsset")
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
