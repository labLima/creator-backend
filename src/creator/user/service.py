"""Use cases for the user capability."""

from __future__ import annotations

from typing import Any

from creator.application.errors import not_found, require_admin
from creator.application.pagination import page_payload
from creator.application.serializers import _settings_data, _user_data
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
    settings = uow.user.settings.get_or_create_for_user(actor.id)
    uow.commit()

    return _settings_data(settings)


def update_my_settings(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    uow.user.settings.get_or_create_for_user(actor.id)
    changes = payload.model_dump(exclude_unset=True)
    settings = uow.user.settings.update_partial(actor.id, changes)
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
    users = uow.user.users.list(page=page_request(page, limit, sort))

    return page_payload(users, _user_data)


def create_user(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_admin(actor)
    user = uow.user.users.add(
        auth_provider_id=payload.auth_provider_id,
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
    user = uow.user.users.get_by_id(user_id)
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
        user = uow.user.users.update(
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
        uow.user.users.soft_delete(user_id)
    except EntityNotFoundError as error:
        raise not_found("User") from error
    uow.commit()

    return {"deleted": True}
