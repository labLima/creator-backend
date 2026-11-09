"""Import untrusted image bytes as the first immutable Content Version."""

from __future__ import annotations

import hashlib
import logging
from io import BytesIO
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from creator.application.errors import ApplicationError, require_workspace_write
from creator.content.ports import ContentDetailRecord, ImportedImageMetadata
from creator.services.storage.provider import (
    StorageError,
    StorageProvider,
    UploadObjectRequest,
    immutable_image_path,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}
_MAX_PIXELS = 40_000_000
logger = logging.getLogger(__name__)


def authorize_import(uow: UnitOfWork, user: UserRecord, brand_id: UUID) -> UUID:
    brand = uow.brand.brands.get_for_user(user_id=user.id, brand_id=brand_id)
    if brand is None:
        raise ApplicationError(404, {"code": "BRAND_NOT_FOUND", "message": "Brand not found"})
    require_workspace_write(uow, user_id=user.id, workspace_id=brand.workspace_id)
    return brand.workspace_id


def import_image(
    *,
    uow: UnitOfWork,
    storage: StorageProvider,
    user: UserRecord,
    brand_id: UUID,
    workspace_id: UUID,
    content: bytes,
    mime_type: str | None,
    title: str | None,
) -> ContentDetailRecord:
    expected_format = _FORMATS.get(mime_type or "")
    try:
        if not expected_format:
            raise ValueError("Unsupported image type")
        with Image.open(BytesIO(content)) as decoded:
            if decoded.format != expected_format or decoded.width * decoded.height > _MAX_PIXELS:
                raise ValueError("Invalid image")
            width, height = decoded.size
            decoded.verify()
        if width <= 0 or height <= 0:
            raise ValueError("Invalid image dimensions")
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ApplicationError(
            422, {"code": "IMAGE_INVALID", "message": "Invalid or unsupported image"}
        ) from error

    record = uow.contents.add(
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        content_type="IMAGE",
        brand_id=brand_id,
        title=title,
        payload={"origin": "upload"},
    )
    assert mime_type is not None
    path = immutable_image_path(
        user_external_id=user.external_id,
        content_id=record.id,
        version_number=1,
        mime_type=mime_type,
    )
    checksum = hashlib.sha256(content).hexdigest()
    upload_attempted = False
    try:
        upload_attempted = True
        stored = storage.upload(
            UploadObjectRequest(
                path=path,
                content=content,
                mime_type=mime_type,
                checksum_sha256=checksum,
                metadata={"workspace_id": str(workspace_id), "content_id": str(record.id)},
            )
        )
        image = uow.contents.add_imported_image(
            workspace_id=workspace_id,
            content_id=record.id,
            image=ImportedImageMetadata(
                storage_path=stored.path,
                public_url=stored.url,
                mime_type=mime_type,
                width=width,
                height=height,
                metadata={
                    "origin": "upload",
                    "storage_checksum_sha256": checksum,
                    "storage_size_bytes": len(content),
                },
            ),
        )
        uow.commit()
        return ContentDetailRecord(content=record, images=[image])
    except Exception:
        uow.rollback()
        if upload_attempted:
            try:
                storage.delete(path)
            except StorageError:
                logger.warning("imported_image_cleanup_failed")
        raise
