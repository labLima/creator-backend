"""Use cases for the asset capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.responses import page_payload, success_response
from creator.api.serializers import _asset_data, _brand_asset_data
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_assets(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
    brand_id: Any,
    project_id: Any,
    content_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    assets = uow.assets.list_for_user(
        user_id=actor.id,
        workspace_id=workspace_id,
        brand_id=brand_id,
        project_id=project_id,
        content_id=content_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(assets, _asset_data)


def create_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    asset = uow.assets.add(
        workspace_id=payload.workspace_id,
        brand_id=payload.brand_id,
        project_id=payload.project_id,
        content_id=payload.content_id,
        uploaded_by_user_id=actor.id,
        asset_type=payload.asset_type,
        storage_path=payload.storage_path,
        public_url=payload.public_url,
        mime_type=payload.mime_type,
        byte_size=payload.byte_size,
        checksum=payload.checksum,
        metadata=payload.metadata,
    )
    uow.commit()

    return _asset_data(asset)


def get_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    asset_id: Any,
) -> Any:
    brand_assets = getattr(uow, "brand_assets", None)
    brand_asset = (
        brand_assets.get_for_user(user_id=actor.id, asset_id=asset_id)
        if brand_assets is not None
        else None
    )
    if brand_asset is not None:
        return success_response(_brand_asset_data(brand_asset), request)
    asset = uow.assets.get_for_user(user_id=actor.id, asset_id=asset_id)
    if asset is None:
        raise not_found("Asset")

    return _asset_data(asset)


def update_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    asset_id: Any,
    payload: Any,
) -> Any:
    try:
        asset = uow.assets.update(
            user_id=actor.id,
            asset_id=asset_id,
            asset_type=payload.asset_type,
            public_url=payload.public_url,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Asset") from error
    uow.commit()

    return _asset_data(asset)


def delete_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    asset_id: Any,
) -> Any:
    try:
        uow.assets.soft_delete(user_id=actor.id, asset_id=asset_id)
    except EntityNotFoundError as error:
        raise not_found("Asset") from error
    uow.commit()

    return {"deleted": True}
