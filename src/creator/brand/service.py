"""Use cases for the brand capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.responses import page_payload
from creator.api.serializers import (
    _brand_asset_data,
    _brand_color_data,
    _brand_data,
    _brand_settings_data,
)
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_brands(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    brands = uow.brands.list_for_user(
        user_id=actor.id,
        workspace_id=workspace_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(brands, _brand_data)


def create_brand(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    brand = uow.brands.add(
        workspace_id=payload.workspace_id,
        created_by_user_id=actor.id,
        name=payload.name,
        description=payload.description,
        brand_voice=payload.brand_voice,
        metadata=payload.metadata,
    )
    uow.commit()

    return _brand_data(brand)


def get_brand(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
) -> Any:
    brand = uow.brands.get_for_user(user_id=actor.id, brand_id=brand_id)
    if brand is None:
        raise not_found("Brand")

    return _brand_data(brand)


def update_brand(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
    payload: Any,
) -> Any:
    try:
        brand = uow.brands.update(
            user_id=actor.id,
            brand_id=brand_id,
            name=payload.name,
            description=payload.description,
            brand_voice=payload.brand_voice,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Brand") from error
    uow.commit()

    return _brand_data(brand)


def delete_brand(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
) -> Any:
    try:
        uow.brands.soft_delete(user_id=actor.id, brand_id=brand_id)
    except EntityNotFoundError as error:
        raise not_found("Brand") from error
    uow.commit()

    return {"deleted": True}


def get_brand_settings(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
) -> Any:
    settings = uow.brand_settings.get_for_user(
        user_id=actor.id,
        brand_id=brand_id,
    )
    if settings is None:
        raise not_found("Brand settings")

    return _brand_settings_data(settings)


def upsert_brand_settings(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    settings = uow.brand_settings.upsert(
        user_id=actor.id,
        workspace_id=payload.workspace_id,
        brand_id=brand_id,
        voice_settings=payload.voice_settings,
        visual_settings=payload.visual_settings,
        generation_defaults=payload.generation_defaults,
        metadata=payload.metadata,
    )
    uow.commit()

    return _brand_settings_data(settings)


def update_brand_settings(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
    payload: Any,
) -> Any:
    try:
        settings = uow.brand_settings.update(
            user_id=actor.id,
            brand_id=brand_id,
            voice_settings=payload.voice_settings,
            visual_settings=payload.visual_settings,
            generation_defaults=payload.generation_defaults,
            metadata=payload.metadata,
        )
    except EntityNotFoundError as error:
        raise not_found("Brand settings") from error
    uow.commit()

    return _brand_settings_data(settings)


def delete_brand_settings(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
) -> Any:
    try:
        uow.brand_settings.soft_delete(user_id=actor.id, brand_id=brand_id)
    except EntityNotFoundError as error:
        raise not_found("Brand settings") from error
    uow.commit()

    return {"deleted": True}


def list_brand_assets(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    result = uow.brand_assets.list_for_user(
        user_id=actor.id,
        brand_id=brand_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(result, _brand_asset_data)


def create_brand_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    brand = uow.brands.get_for_user(user_id=actor.id, brand_id=payload.brand_id)
    if brand is None:
        raise not_found("Brand")
    require_workspace_write(uow, user_id=actor.id, workspace_id=brand.workspace_id)
    asset = uow.brand_assets.add(
        brand_id=payload.brand_id,
        type=payload.type,
        file_url=payload.file_url,
        file_name=payload.file_name,
        description=payload.description,
    )
    uow.commit()

    return _brand_asset_data(asset)


def get_brand_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    asset_id: Any,
) -> Any:
    asset = uow.brand_assets.get_for_user(user_id=actor.id, asset_id=asset_id)
    if asset is None:
        raise not_found("Brand asset")

    return _brand_asset_data(asset)


def update_brand_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    asset_id: Any,
    payload: Any,
) -> Any:
    existing = uow.brand_assets.get_for_user(user_id=actor.id, asset_id=asset_id)
    if existing is None:
        raise not_found("Brand asset")
    brand = uow.brands.get_for_user(user_id=actor.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Brand asset")
    require_workspace_write(uow, user_id=actor.id, workspace_id=brand.workspace_id)
    updated = uow.brand_assets.update(
        asset_id=asset_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _brand_asset_data(updated)


def delete_brand_asset(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    asset_id: Any,
) -> Any:
    existing = uow.brand_assets.get_for_user(user_id=actor.id, asset_id=asset_id)
    if existing is None:
        raise not_found("Brand asset")
    brand = uow.brands.get_for_user(user_id=actor.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Brand asset")
    require_workspace_write(uow, user_id=actor.id, workspace_id=brand.workspace_id)
    uow.brand_assets.soft_delete(asset_id=asset_id)
    uow.commit()

    return {"deleted": True}


def list_brand_colors(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
) -> Any:
    return {
        "items": [
            _brand_color_data(x)
            for x in uow.brand_colors.list_for_user(user_id=actor.id, brand_id=brand_id)
        ]
    }


def create_brand_color(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    data = payload.model_dump()
    data["created_by"] = actor.id
    item = uow.brand_colors.add(fields=data)
    uow.commit()

    return _brand_color_data(item)


def get_brand_color(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    color_id: Any,
) -> Any:
    item = uow.brand_colors.get_for_user(user_id=actor.id, color_id=color_id)
    if item is None:
        raise not_found("Brand color")

    return _brand_color_data(item)


def update_brand_color(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    color_id: Any,
    payload: Any,
) -> Any:
    if uow.brand_colors.get_for_user(user_id=actor.id, color_id=color_id) is None:
        raise not_found("Brand color")
    item = uow.brand_colors.update(color_id=color_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _brand_color_data(item)


def delete_brand_color(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    color_id: Any,
) -> Any:
    if uow.brand_colors.get_for_user(user_id=actor.id, color_id=color_id) is None:
        raise not_found("Brand color")
    uow.brand_colors.soft_delete(color_id=color_id)
    uow.commit()

    return {"deleted": True}
