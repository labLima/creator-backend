"""Use cases for the design_structure capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found
from creator.api.serializers import _design_structure_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_design_structures(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {
        "items": [
            _design_structure_data(x) for x in uow.design_structures.list_for_user(user_id=actor.id)
        ]
    }


def create_design_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    item = uow.post_structures.get_for_user(
        user_id=actor.id, post_structure_id=payload.post_structure_id
    )
    if item is None:
        raise not_found("Post structure")
    result = uow.design_structures.add(post_structure_id=payload.post_structure_id)
    uow.commit()

    return _design_structure_data(result)


def get_design_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    design_id: Any,
) -> Any:
    item = uow.design_structures.get_for_user(user_id=actor.id, design_id=design_id)
    if item is None:
        raise not_found("Design structure")

    return _design_structure_data(item)


def update_design_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    design_id: Any,
    payload: Any,
) -> Any:
    if uow.design_structures.get_for_user(user_id=actor.id, design_id=design_id) is None:
        raise not_found("Design structure")
    item = uow.design_structures.update(design_id=design_id, fields=payload)
    uow.commit()

    return _design_structure_data(item)


def delete_design_structure(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    design_id: Any,
) -> Any:
    if uow.design_structures.get_for_user(user_id=actor.id, design_id=design_id) is None:
        raise not_found("Design structure")
    uow.design_structures.soft_delete(design_id=design_id)
    uow.commit()

    return {"deleted": True}
