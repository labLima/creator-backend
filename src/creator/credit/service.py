"""Use cases for the credit capability.

The Credit Transaction ledger is append-only (ADR-019): this capability only
reads it. A correction is written as a new transaction by the capability that
consumes Credits, never by a client.
"""

from __future__ import annotations

from typing import Any

from creator.application.errors import not_found
from creator.application.serializers import _workspace_credit_transaction_data
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
