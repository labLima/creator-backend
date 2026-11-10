from __future__ import annotations

import hashlib
from io import BytesIO
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from creator.config import Settings
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.infrastructure.runtime.storage import create_storage_provider
from creator.services.ai.image_provider import ImageInput, ImageProviderInvalidResponseError


def resolve_reference_images(
    *, asset_ids: object, user_id: UUID, workspace_id: UUID, brand_id: UUID, settings: Settings
) -> tuple[ImageInput, ...]:
    if not isinstance(asset_ids, list) or not asset_ids:
        return ()
    if len(asset_ids) > 4 or len(set(asset_ids)) != len(asset_ids):
        raise ImageProviderInvalidResponseError("Reference image selection is invalid")
    records = []
    with SqlAlchemyUnitOfWork() as uow:
        for raw_id in asset_ids:
            try:
                asset_id = UUID(str(raw_id))
            except ValueError as error:
                raise ImageProviderInvalidResponseError(
                    "Reference image selection is invalid"
                ) from error
            asset = uow.assets.get_for_user(user_id=user_id, asset_id=asset_id)
            if (
                asset is None
                or asset.deleted_at is not None
                or asset.workspace_id != workspace_id
                or asset.brand_id != brand_id
                or asset.asset_type != "REFERENCE_IMAGE"
                or asset.metadata.get("reference_image_upload") is not True
            ):
                raise ImageProviderInvalidResponseError("Authorized reference image is unavailable")
            records.append(asset)
    storage = create_storage_provider(settings)
    result: list[ImageInput] = []
    for asset in records:
        try:
            content = storage.download(
                asset.storage_path,
                max_bytes=min(settings.storage_max_object_bytes, 10 * 1024 * 1024),
            )
        except Exception:
            raise ImageProviderInvalidResponseError("Reference image is unavailable") from None
        if len(content) != asset.byte_size or hashlib.sha256(content).hexdigest() != asset.checksum:
            raise ImageProviderInvalidResponseError("Reference image integrity check failed")
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
            with Image.open(BytesIO(content)) as image:
                actual_mime = Image.MIME.get(image.format or "")
                if actual_mime != asset.mime_type or image.size != (
                    asset.metadata.get("width"),
                    asset.metadata.get("height"),
                ):
                    raise ValueError("image metadata mismatch")
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise ImageProviderInvalidResponseError("Reference image is invalid") from error
        result.append(
            ImageInput(
                content=content,
                mime_type=asset.mime_type,
                asset_id=str(asset.id),
                checksum_sha256=asset.checksum,
            )
        )
    return tuple(result)
