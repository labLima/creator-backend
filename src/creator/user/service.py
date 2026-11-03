"""Use cases for the user capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_admin
from creator.api.responses import page_payload
from creator.api.serializers import _settings_data, _user_data
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def get_my_profile(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return _user_data(actor)


def get_my_settings(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    settings = uow.settings.get_or_create_for_user(actor.id)
    uow.commit()

    return _settings_data(settings)


def update_my_settings(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    uow.settings.get_or_create_for_user(actor.id)
    changes = payload.model_dump(exclude_unset=True)
    settings = uow.settings.update_partial(actor.id, changes)
    uow.commit()

    return _settings_data(settings)


def list_users(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    require_admin(actor)
    users = uow.users.list(page=page_request(page, limit, sort))

    return page_payload(users, _user_data)


def create_user(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_admin(actor)
    user = uow.users.add(
        external_id=payload.external_id,
        email=payload.email,
        display_name=payload.display_name,
        global_role=payload.global_role,
    )
    uow.commit()

    return _user_data(user)


def get_user(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    user_id: Any,
) -> Any:
    require_admin(actor)
    user = uow.users.get_by_id(user_id)
    if user is None:
        raise not_found("User")

    return _user_data(user)


def update_user(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    user_id: Any,
    payload: Any,
) -> Any:
    require_admin(actor)
    try:
        user = uow.users.update(
            user_id,
            email=payload.email,
            display_name=payload.display_name,
            global_role=payload.global_role,
        )
    except EntityNotFoundError as error:
        raise not_found("User") from error
    uow.commit()

    return _user_data(user)


def delete_user(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    user_id: Any,
) -> Any:
    require_admin(actor)
    try:
        uow.users.soft_delete(user_id)
    except EntityNotFoundError as error:
        raise not_found("User") from error
    uow.commit()

    return {"deleted": True}
