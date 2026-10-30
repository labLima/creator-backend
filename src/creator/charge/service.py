"""Use cases for the charge capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found
from creator.api.serializers import _charge_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_charges(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {"items": [_charge_data(x) for x in uow.charges.list_for_user(user_id=actor.id)]}


def create_charge(
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
    item = uow.charges.add(**payload.model_dump())
    uow.commit()

    return _charge_data(item)


def get_charge(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    charge_id: Any,
) -> Any:
    item = uow.charges.get_for_user(user_id=actor.id, charge_id=charge_id)
    if item is None:
        raise not_found("Charge")

    return _charge_data(item)


def update_charge(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    charge_id: Any,
    payload: Any,
) -> Any:
    if uow.charges.get_for_user(user_id=actor.id, charge_id=charge_id) is None:
        raise not_found("Charge")
    item = uow.charges.update(charge_id=charge_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _charge_data(item)


def delete_charge(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    charge_id: Any,
) -> Any:
    if uow.charges.get_for_user(user_id=actor.id, charge_id=charge_id) is None:
        raise not_found("Charge")
    uow.charges.soft_delete(charge_id=charge_id)
    uow.commit()

    return {"deleted": True}
