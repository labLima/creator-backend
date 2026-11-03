"""Use cases for the refund capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found
from creator.api.serializers import _refund_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_refunds(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {"items": [_refund_data(x) for x in uow.refunds.list_for_user(user_id=actor.id)]}


def create_refund(
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
    data = payload.model_dump()
    data["status"] = "pending"
    item = uow.refunds.add(fields=data)
    uow.commit()

    return _refund_data(item)


def get_refund(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    refund_id: Any,
) -> Any:
    item = uow.refunds.get_for_user(user_id=actor.id, refund_id=refund_id)
    if item is None:
        raise not_found("Refund")

    return _refund_data(item)


def update_refund(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    refund_id: Any,
    payload: Any,
) -> Any:
    if uow.refunds.get_for_user(user_id=actor.id, refund_id=refund_id) is None:
        raise not_found("Refund")
    item = uow.refunds.update(refund_id=refund_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _refund_data(item)


def delete_refund(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    refund_id: Any,
) -> Any:
    if uow.refunds.get_for_user(user_id=actor.id, refund_id=refund_id) is None:
        raise not_found("Refund")
    uow.refunds.soft_delete(refund_id=refund_id)
    uow.commit()

    return {"deleted": True}
