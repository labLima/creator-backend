"""Use cases for the billing_provider capability."""

from __future__ import annotations

from typing import Any

from creator.application.errors import not_found, require_global_billing_admin
from creator.application.serializers import (
    _provider_dispute_data,
    _provider_idempotency_key_data,
    _provider_webhook_event_data,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_provider_webhook_events(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    require_global_billing_admin(actor)

    return {
        "items": [
            _provider_webhook_event_data(x) for x in uow.billing_provider.webhook_events.list()
        ]
    }


def create_provider_webhook_event(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.billing_provider.webhook_events.add(fields=payload)
    uow.commit()

    return _provider_webhook_event_data(item)


def get_provider_webhook_event(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    event_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.billing_provider.webhook_events.get(event_id=event_id)
    if item is None:
        raise not_found("Provider webhook event")

    return _provider_webhook_event_data(item)


def update_provider_webhook_event(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    event_id: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.billing_provider.webhook_events.get(event_id=event_id) is None:
        raise not_found("Provider webhook event")
    item = uow.billing_provider.webhook_events.update(event_id=event_id, fields=payload)
    uow.commit()

    return _provider_webhook_event_data(item)


def delete_provider_webhook_event(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    event_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.billing_provider.webhook_events.get(event_id=event_id)
    if item is None:
        raise not_found("Provider webhook event")
    updated = uow.billing_provider.webhook_events.update(
        event_id=event_id, fields={"status": "deleted"}
    )
    uow.commit()

    return _provider_webhook_event_data(updated)


def list_provider_idempotency_keys(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    require_global_billing_admin(actor)

    return {
        "items": [
            _provider_idempotency_key_data(x) for x in uow.billing_provider.idempotency_keys.list()
        ]
    }


def create_provider_idempotency_key(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.billing_provider.idempotency_keys.add(fields=payload)
    uow.commit()

    return _provider_idempotency_key_data(item)


def get_provider_idempotency_key(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    key_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.billing_provider.idempotency_keys.get(key_id=key_id)
    if item is None:
        raise not_found("Provider idempotency key")

    return _provider_idempotency_key_data(item)


def update_provider_idempotency_key(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    key_id: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.billing_provider.idempotency_keys.get(key_id=key_id) is None:
        raise not_found("Provider idempotency key")
    item = uow.billing_provider.idempotency_keys.update(key_id=key_id, fields=payload)
    uow.commit()

    return _provider_idempotency_key_data(item)


def delete_provider_idempotency_key(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    key_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.billing_provider.idempotency_keys.get(key_id=key_id) is None:
        raise not_found("Provider idempotency key")
    item = uow.billing_provider.idempotency_keys.update(key_id=key_id, fields={"status": "deleted"})
    uow.commit()

    return _provider_idempotency_key_data(item)


def list_provider_disputes(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {
        "items": [
            _provider_dispute_data(x)
            for x in uow.billing_provider.disputes.list_for_user(user_id=actor.id)
        ]
    }


def create_provider_dispute(
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
    data = payload.model_dump()
    data["status"] = "open"
    data["payload"] = {}
    item = uow.billing_provider.disputes.add(fields=data)
    uow.commit()

    return _provider_dispute_data(item)


def get_provider_dispute(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    dispute_id: Any,
) -> Any:
    item = uow.billing_provider.disputes.get_for_user(user_id=actor.id, dispute_id=dispute_id)
    if item is None:
        raise not_found("Provider dispute")

    return _provider_dispute_data(item)


def update_provider_dispute(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    dispute_id: Any,
    payload: Any,
) -> Any:
    if uow.billing_provider.disputes.get_for_user(user_id=actor.id, dispute_id=dispute_id) is None:
        raise not_found("Provider dispute")
    item = uow.billing_provider.disputes.update(
        dispute_id=dispute_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _provider_dispute_data(item)


def delete_provider_dispute(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    dispute_id: Any,
) -> Any:
    if uow.billing_provider.disputes.get_for_user(user_id=actor.id, dispute_id=dispute_id) is None:
        raise not_found("Provider dispute")
    uow.billing_provider.disputes.soft_delete(dispute_id=dispute_id)
    uow.commit()

    return {"deleted": True}
