"""Use cases for the credit capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.serializers import _workspace_credit_transaction_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_workspace_credit_transactions(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
) -> Any:
    items = uow.workspace_credit_transactions.list_for_user(
        user_id=actor.id, workspace_id=workspace_id
    )

    return {"items": [_workspace_credit_transaction_data(x) for x in items]}


def create_workspace_credit_transaction(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    item = uow.workspace_credit_transactions.add(fields=payload.model_dump())
    uow.commit()

    return _workspace_credit_transaction_data(item)


def get_workspace_credit_transaction(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    transaction_id: Any,
) -> Any:
    item = uow.workspace_credit_transactions.get_for_user(
        user_id=actor.id, transaction_id=transaction_id
    )
    if item is None:
        raise not_found("Workspace credit transaction")

    return _workspace_credit_transaction_data(item)


def delete_workspace_credit_transaction(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    transaction_id: Any,
) -> Any:
    if (
        uow.workspace_credit_transactions.get_for_user(
            user_id=actor.id, transaction_id=transaction_id
        )
        is None
    ):
        raise not_found("Workspace credit transaction")
    uow.workspace_credit_transactions.soft_delete(transaction_id=transaction_id)
    uow.commit()

    return {"deleted": True}
