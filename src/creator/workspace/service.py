"""Use cases for the workspace capability."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

from creator.application.errors import not_found, require_workspace_write
from creator.application.pagination import page_payload
from creator.application.serializers import (
    _workspace_data,
    _workspace_invite_data,
    _workspace_invite_usage_data,
    _workspace_membership_data,
)
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_workspaces(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    workspaces = uow.workspace.workspaces.list_for_user(
        user_id=actor.id,
        page=page_request(page, limit, sort),
    )

    return page_payload(workspaces, _workspace_data)


def create_workspace(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    created = uow.workspace.workspaces.create_for_user(
        user_id=actor.id,
        name=payload.name,
    )
    uow.commit()

    return {
        "workspace": _workspace_data(created.workspace),
        "membership": _workspace_membership_data(created.membership),
    }


def get_workspace(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
) -> Any:
    workspace = uow.workspace.workspaces.get_for_user(
        user_id=actor.id,
        workspace_id=workspace_id,
    )
    if workspace is None:
        raise not_found("Workspace")

    return _workspace_data(workspace)


def update_workspace(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
    payload: Any,
) -> Any:
    try:
        workspace = uow.workspace.workspaces.update(
            user_id=actor.id,
            workspace_id=workspace_id,
            name=payload.name,
        )
    except EntityNotFoundError as error:
        raise not_found("Workspace") from error
    uow.commit()

    return _workspace_data(workspace)


def delete_workspace(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
) -> Any:
    try:
        workspace = uow.workspace.workspaces.soft_delete_for_user(
            user_id=actor.id,
            workspace_id=workspace_id,
        )
    except EntityNotFoundError as error:
        raise not_found("Workspace") from error
    uow.commit()

    return {"workspace": _workspace_data(workspace)}


def list_workspace_invites(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
) -> Any:
    return {
        "items": [
            _workspace_invite_data(x)
            for x in uow.workspace.invites.list_for_user(
                user_id=actor.id, workspace_id=workspace_id
            )
        ]
    }


def create_workspace_invite(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    item = uow.workspace.invites.add(
        **payload.model_dump(),
        created_by=actor.id,
        token_hash=hashlib.sha256(uuid4().hex.encode("utf-8")).hexdigest(),
    )
    uow.commit()

    return _workspace_invite_data(item)


def get_workspace_invite(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    invite_id: Any,
) -> Any:
    item = uow.workspace.invites.get_for_user(user_id=actor.id, invite_id=invite_id)
    if item is None:
        raise not_found("Workspace invite")

    return _workspace_invite_data(item)


def update_workspace_invite(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    invite_id: Any,
    payload: Any,
) -> Any:
    if uow.workspace.invites.get_for_user(user_id=actor.id, invite_id=invite_id) is None:
        raise not_found("Workspace invite")
    item = uow.workspace.invites.update(
        invite_id=invite_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _workspace_invite_data(item)


def delete_workspace_invite(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    invite_id: Any,
) -> Any:
    if uow.workspace.invites.get_for_user(user_id=actor.id, invite_id=invite_id) is None:
        raise not_found("Workspace invite")
    uow.workspace.invites.soft_delete(invite_id=invite_id)
    uow.commit()

    return {"deleted": True}


def list_workspace_invite_usages(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
) -> Any:
    return {
        "items": [
            _workspace_invite_usage_data(x)
            for x in uow.workspace.invite_usages.list_for_user(
                user_id=actor.id, workspace_id=workspace_id
            )
        ]
    }


def create_workspace_invite_usage(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    payload["user_id"] = actor.id
    item = uow.workspace.invite_usages.add(fields=payload)
    uow.commit()

    return _workspace_invite_usage_data(item)


def get_workspace_invite_usage(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    usage_id: Any,
) -> Any:
    item = uow.workspace.invite_usages.get_for_user(user_id=actor.id, usage_id=usage_id)
    if item is None:
        raise not_found("Workspace invite usage")

    return _workspace_invite_usage_data(item)


def update_workspace_invite_usage(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    usage_id: Any,
    payload: Any,
) -> Any:
    if uow.workspace.invite_usages.get_for_user(user_id=actor.id, usage_id=usage_id) is None:
        raise not_found("Workspace invite usage")
    item = uow.workspace.invite_usages.update(usage_id=usage_id, fields=payload)
    uow.commit()

    return _workspace_invite_usage_data(item)


def delete_workspace_invite_usage(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    usage_id: Any,
) -> Any:
    if uow.workspace.invite_usages.get_for_user(user_id=actor.id, usage_id=usage_id) is None:
        raise not_found("Workspace invite usage")
    uow.workspace.invite_usages.soft_delete(usage_id=usage_id)
    uow.commit()

    return {"deleted": True}
