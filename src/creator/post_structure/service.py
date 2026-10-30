"""Use cases for the post_structure capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.responses import page_payload
from creator.api.serializers import _post_structure_data
from creator.core.pagination import page_request
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_post_structures(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    result = uow.post_structures.list_for_user(
        user_id=actor.id,
        workspace_id=workspace_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(result, _post_structure_data)


def create_post_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    fields = payload.model_dump(exclude={"workspace_id", "planning_id"})
    post_structure = uow.post_structures.add(
        workspace_id=payload.workspace_id,
        planning_id=payload.planning_id,
        created_by=actor.id,
        **fields,
    )
    uow.commit()

    return _post_structure_data(post_structure)


def get_post_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    post_structure_id: Any,
) -> Any:
    post_structure = uow.post_structures.get_for_user(
        user_id=actor.id, post_structure_id=post_structure_id
    )
    if post_structure is None:
        raise not_found("Post structure")

    return _post_structure_data(post_structure)


def update_post_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    post_structure_id: Any,
    payload: Any,
) -> Any:
    existing = uow.post_structures.get_for_user(
        user_id=actor.id, post_structure_id=post_structure_id
    )
    if existing is None:
        raise not_found("Post structure")
    require_workspace_write(uow, user_id=actor.id, workspace_id=existing.workspace_id)
    updated = uow.post_structures.update(
        post_structure_id=post_structure_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    uow.commit()

    return _post_structure_data(updated)


def delete_post_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    post_structure_id: Any,
) -> Any:
    existing = uow.post_structures.get_for_user(
        user_id=actor.id, post_structure_id=post_structure_id
    )
    if existing is None:
        raise not_found("Post structure")
    require_workspace_write(uow, user_id=actor.id, workspace_id=existing.workspace_id)
    uow.post_structures.soft_delete(post_structure_id=post_structure_id)
    uow.commit()

    return {"deleted": True}
