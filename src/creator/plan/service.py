"""Use cases for the plan capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_global_billing_admin
from creator.api.serializers import _plan_data, _plan_item_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_plans(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    require_global_billing_admin(actor)

    return {"items": [_plan_data(item) for item in uow.plans.list()]}


def create_plan(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.plans.add(**payload.model_dump())
    uow.commit()

    return _plan_data(item)


def get_plan(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    plan_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.plans.get(plan_id=plan_id)
    if item is None:
        raise not_found("Plan")

    return _plan_data(item)


def update_plan(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    plan_id: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.plans.get(plan_id=plan_id) is None:
        raise not_found("Plan")
    item = uow.plans.update(plan_id=plan_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _plan_data(item)


def delete_plan(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    plan_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.plans.get(plan_id=plan_id) is None:
        raise not_found("Plan")
    uow.plans.soft_delete(plan_id=plan_id)
    uow.commit()

    return {"deleted": True}


def list_plan_items(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    plan_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    items = uow.plan_items.list(plan_id=plan_id)

    return {"items": [_plan_item_data(item) for item in items]}


def create_plan_item(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.plans.get(plan_id=payload.plan_id) is None:
        raise not_found("Plan")
    item = uow.plan_items.add(**payload.model_dump())
    uow.commit()

    return _plan_item_data(item)


def get_plan_item(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    item_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.plan_items.get(item_id=item_id)
    if item is None:
        raise not_found("Plan item")

    return _plan_item_data(item)


def update_plan_item(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    item_id: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.plan_items.get(item_id=item_id) is None:
        raise not_found("Plan item")
    item = uow.plan_items.update(item_id=item_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _plan_item_data(item)


def delete_plan_item(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    item_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.plan_items.get(item_id=item_id) is None:
        raise not_found("Plan item")
    uow.plan_items.soft_delete(item_id=item_id)
    uow.commit()

    return {"deleted": True}
