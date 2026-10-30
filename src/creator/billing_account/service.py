"""Use cases for the billing_account capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import HTTPException, not_found
from creator.api.serializers import _billing_account_data, _billing_address_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_billing_addresses(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    billing_account_id: Any,
) -> Any:
    return {
        "items": [
            _billing_address_data(x)
            for x in uow.billing_addresses.list_for_user(
                user_id=actor.id, account_id=billing_account_id
            )
        ]
    }


def create_billing_address(
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
    item = uow.billing_addresses.add(billing_account_id=account_id, fields=data)
    uow.commit()

    return _billing_address_data(item)


def get_billing_address(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    address_id: Any,
) -> Any:
    item = uow.billing_addresses.get_for_user(user_id=actor.id, address_id=address_id)
    if item is None:
        raise not_found("Billing address")

    return _billing_address_data(item)


def update_billing_address(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    address_id: Any,
    payload: Any,
) -> Any:
    if uow.billing_addresses.get_for_user(user_id=actor.id, address_id=address_id) is None:
        raise not_found("Billing address")
    item = uow.billing_addresses.update(
        address_id=address_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _billing_address_data(item)


def delete_billing_address(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    address_id: Any,
) -> Any:
    if uow.billing_addresses.get_for_user(user_id=actor.id, address_id=address_id) is None:
        raise not_found("Billing address")
    uow.billing_addresses.soft_delete(address_id=address_id)
    uow.commit()

    return {"deleted": True}


def list_billing_accounts(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    items = uow.billing_accounts.list_for_user(user_id=actor.id)

    return {"items": [_billing_account_data(item) for item in items]}


def create_billing_account(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    if payload.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Billing account belongs to another Principal")
    item = uow.billing_accounts.add(
        user_id=actor.id,
        payer_type=payload.payer_type,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        document=payload.document,
        document_type=payload.document_type,
    )
    uow.commit()

    return _billing_account_data(item)


def get_billing_account(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    account_id: Any,
) -> Any:
    item = uow.billing_accounts.get_for_user(user_id=actor.id, account_id=account_id)
    if item is None:
        raise not_found("Billing account")

    return _billing_account_data(item)


def update_billing_account(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    account_id: Any,
    payload: Any,
) -> Any:
    if uow.billing_accounts.get_for_user(user_id=actor.id, account_id=account_id) is None:
        raise not_found("Billing account")
    item = uow.billing_accounts.update(
        user_id=actor.id,
        account_id=account_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    uow.commit()

    return _billing_account_data(item)


def delete_billing_account(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    account_id: Any,
) -> Any:
    if uow.billing_accounts.get_for_user(user_id=actor.id, account_id=account_id) is None:
        raise not_found("Billing account")
    uow.billing_accounts.soft_delete(user_id=actor.id, account_id=account_id)
    uow.commit()

    return {"deleted": True}
