"""Use cases for the order capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.serializers import _order_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_orders(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {"items": [_order_data(x) for x in uow.orders.list_for_user(user_id=actor.id)]}


def create_order(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    if (
        uow.billing_accounts.get_for_user(user_id=actor.id, account_id=payload.billing_account_id)
        is None
    ):
        raise not_found("Billing account")
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    data = payload.model_dump()
    data["status"] = "pending"
    item = uow.orders.add(fields=data)
    uow.commit()

    return _order_data(item)


def get_order(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    order_id: Any,
) -> Any:
    item = uow.orders.get_for_user(user_id=actor.id, order_id=order_id)
    if item is None:
        raise not_found("Order")

    return _order_data(item)


def update_order(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    order_id: Any,
    payload: Any,
) -> Any:
    if uow.orders.get_for_user(user_id=actor.id, order_id=order_id) is None:
        raise not_found("Order")
    item = uow.orders.update(order_id=order_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _order_data(item)


def delete_order(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    order_id: Any,
) -> Any:
    if uow.orders.get_for_user(user_id=actor.id, order_id=order_id) is None:
        raise not_found("Order")
    uow.orders.soft_delete(order_id=order_id)
    uow.commit()

    return {"deleted": True}
