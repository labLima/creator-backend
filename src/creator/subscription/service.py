"""Use cases for the subscription capability."""

from __future__ import annotations

from typing import Any

from creator.application.errors import not_found, require_workspace_write
from creator.application.serializers import _subscription_data, _subscription_history_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_subscription_history(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {
        "items": [
            _subscription_history_data(x)
            for x in uow.subscription.history.list_for_user(user_id=actor.id)
        ]
    }


def get_subscription_history(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    history_id: Any,
) -> Any:
    item = uow.subscription.history.get_for_user(user_id=actor.id, history_id=history_id)
    if item is None:
        raise not_found("Subscription history")

    return _subscription_history_data(item)


def list_subscriptions(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {
        "items": [
            _subscription_data(x)
            for x in uow.subscription.subscriptions.list_for_user(user_id=actor.id)
        ]
    }


def create_subscription(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    if (
        uow.billing_account.accounts.get_for_user(
            user_id=actor.id, account_id=payload.billing_account_id
        )
        is None
    ):
        raise not_found("Billing account")
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    if uow.plan.plans.get(plan_id=payload.plan_id) is None:
        raise not_found("Plan")
    item = uow.subscription.subscriptions.add(**payload.model_dump())
    uow.commit()

    return _subscription_data(item)


def get_subscription(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    subscription_id: Any,
) -> Any:
    item = uow.subscription.subscriptions.get_for_user(
        user_id=actor.id, subscription_id=subscription_id
    )
    if item is None:
        raise not_found("Subscription")

    return _subscription_data(item)


def update_subscription(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    subscription_id: Any,
    payload: Any,
) -> Any:
    if (
        uow.subscription.subscriptions.get_for_user(
            user_id=actor.id, subscription_id=subscription_id
        )
        is None
    ):
        raise not_found("Subscription")
    item = uow.subscription.subscriptions.update(
        subscription_id=subscription_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _subscription_data(item)


def delete_subscription(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    subscription_id: Any,
) -> Any:
    if (
        uow.subscription.subscriptions.get_for_user(
            user_id=actor.id, subscription_id=subscription_id
        )
        is None
    ):
        raise not_found("Subscription")
    uow.subscription.subscriptions.soft_delete(subscription_id=subscription_id)
    uow.commit()

    return {"deleted": True}
