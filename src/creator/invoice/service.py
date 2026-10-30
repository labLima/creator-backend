"""Use cases for the invoice capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found
from creator.api.serializers import _invoice_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_invoices(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {"items": [_invoice_data(x) for x in uow.invoices.list_for_user(user_id=actor.id)]}


def create_invoice(
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
    item = uow.invoices.add(**payload.model_dump())
    uow.commit()

    return _invoice_data(item)


def get_invoice(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    invoice_id: Any,
) -> Any:
    item = uow.invoices.get_for_user(user_id=actor.id, invoice_id=invoice_id)
    if item is None:
        raise not_found("Invoice")

    return _invoice_data(item)


def update_invoice(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    invoice_id: Any,
    payload: Any,
) -> Any:
    if uow.invoices.get_for_user(user_id=actor.id, invoice_id=invoice_id) is None:
        raise not_found("Invoice")
    item = uow.invoices.update(invoice_id=invoice_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _invoice_data(item)


def delete_invoice(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    invoice_id: Any,
) -> Any:
    if uow.invoices.get_for_user(user_id=actor.id, invoice_id=invoice_id) is None:
        raise not_found("Invoice")
    uow.invoices.soft_delete(invoice_id=invoice_id)
    uow.commit()

    return {"deleted": True}
