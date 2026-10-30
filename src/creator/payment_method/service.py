"""Use cases for the payment_method capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found
from creator.api.serializers import _payment_method_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_payment_methods(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    billing_account_id: Any,
) -> Any:
    return {
        "items": [
            _payment_method_data(x)
            for x in uow.billing_payment_methods.list_for_user(
                user_id=actor.id, account_id=billing_account_id
            )
        ]
    }


def create_payment_method(
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
    account_id = data.pop("billing_account_id")
    item = uow.billing_payment_methods.add(billing_account_id=account_id, fields=data)
    uow.commit()

    return _payment_method_data(item)


def get_payment_method(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    method_id: Any,
) -> Any:
    item = uow.billing_payment_methods.get_for_user(user_id=actor.id, method_id=method_id)
    if item is None:
        raise not_found("Billing payment method")

    return _payment_method_data(item)


def update_payment_method(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    method_id: Any,
    payload: Any,
) -> Any:
    if uow.billing_payment_methods.get_for_user(user_id=actor.id, method_id=method_id) is None:
        raise not_found("Billing payment method")
    item = uow.billing_payment_methods.update(
        method_id=method_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _payment_method_data(item)


def delete_payment_method(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    method_id: Any,
) -> Any:
    if uow.billing_payment_methods.get_for_user(user_id=actor.id, method_id=method_id) is None:
        raise not_found("Billing payment method")
    uow.billing_payment_methods.soft_delete(method_id=method_id)
    uow.commit()

    return {"deleted": True}
