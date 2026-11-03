"""Use cases for the notification capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.serializers import (
    _notification_data,
    _notification_preference_data,
    _notification_recipient_data,
    _user_device_data,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_notification_recipients(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {
        "items": [
            _notification_recipient_data(x)
            for x in uow.notification_recipients.list_for_user(user_id=actor.id)
        ]
    }


def create_notification_recipient(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    payload["user_id"] = actor.id
    item = uow.notification_recipients.add(fields=payload)
    uow.commit()

    return _notification_recipient_data(item)


def get_notification_recipient(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    recipient_id: Any,
) -> Any:
    item = uow.notification_recipients.get_for_user(user_id=actor.id, recipient_id=recipient_id)
    if item is None:
        raise not_found("Notification recipient")

    return _notification_recipient_data(item)


def update_notification_recipient(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    recipient_id: Any,
    payload: Any,
) -> Any:
    if (
        uow.notification_recipients.get_for_user(user_id=actor.id, recipient_id=recipient_id)
        is None
    ):
        raise not_found("Notification recipient")
    item = uow.notification_recipients.update(recipient_id=recipient_id, fields=payload)
    uow.commit()

    return _notification_recipient_data(item)


def delete_notification_recipient(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    recipient_id: Any,
) -> Any:
    if (
        uow.notification_recipients.get_for_user(user_id=actor.id, recipient_id=recipient_id)
        is None
    ):
        raise not_found("Notification recipient")
    uow.notification_recipients.soft_delete(recipient_id=recipient_id)
    uow.commit()

    return {"deleted": True}


def list_notifications(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
) -> Any:
    items = uow.notifications.list_for_user(user_id=actor.id, workspace_id=workspace_id)

    return {"items": [_notification_data(item) for item in items]}


def create_notification(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    item = uow.notifications.add(
        workspace_id=payload.workspace_id,
        created_by=actor.id,
        type=payload.type,
        title=payload.title,
        body=payload.body,
        payload=payload.payload,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    uow.commit()

    return _notification_data(item)


def get_notification(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    notification_id: Any,
) -> Any:
    item = uow.notifications.get_for_user(user_id=actor.id, notification_id=notification_id)
    if item is None:
        raise not_found("Notification")

    return _notification_data(item)


def update_notification(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    notification_id: Any,
    payload: Any,
) -> Any:
    existing = uow.notifications.get_for_user(user_id=actor.id, notification_id=notification_id)
    if existing is None:
        raise not_found("Notification")
    require_workspace_write(uow, user_id=actor.id, workspace_id=existing.workspace_id)
    item = uow.notifications.update(
        notification_id=notification_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _notification_data(item)


def delete_notification(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    notification_id: Any,
) -> Any:
    existing = uow.notifications.get_for_user(user_id=actor.id, notification_id=notification_id)
    if existing is None:
        raise not_found("Notification")
    require_workspace_write(uow, user_id=actor.id, workspace_id=existing.workspace_id)
    uow.notifications.soft_delete(notification_id=notification_id)
    uow.commit()

    return {"deleted": True}


def list_user_devices(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    items = uow.user_devices.list_for_user(user_id=actor.id)

    return {"items": [_user_device_data(item) for item in items]}


def create_user_device(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    item = uow.user_devices.add(
        user_id=actor.id, platform=payload.platform, fcm_token=payload.fcm_token
    )
    uow.commit()

    return _user_device_data(item)


def get_user_device(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    device_id: Any,
) -> Any:
    item = uow.user_devices.get_for_user(user_id=actor.id, device_id=device_id)
    if item is None:
        raise not_found("User device")

    return _user_device_data(item)


def update_user_device(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    device_id: Any,
    payload: Any,
) -> Any:
    if uow.user_devices.get_for_user(user_id=actor.id, device_id=device_id) is None:
        raise not_found("User device")
    item = uow.user_devices.update(
        user_id=actor.id,
        device_id=device_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    uow.commit()

    return _user_device_data(item)


def delete_user_device(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    device_id: Any,
) -> Any:
    if uow.user_devices.get_for_user(user_id=actor.id, device_id=device_id) is None:
        raise not_found("User device")
    uow.user_devices.soft_delete(user_id=actor.id, device_id=device_id)
    uow.commit()

    return {"deleted": True}


def list_notification_preferences(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    items = uow.notification_preferences.list_for_user(user_id=actor.id)

    return {"items": [_notification_preference_data(item) for item in items]}


def create_notification_preference(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    item = uow.notification_preferences.add(
        user_id=actor.id,
        type=payload.type,
        channel=payload.channel,
        is_enabled=payload.is_enabled,
    )
    uow.commit()

    return _notification_preference_data(item)


def get_notification_preference(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    preference_id: Any,
) -> Any:
    item = uow.notification_preferences.get_for_user(user_id=actor.id, preference_id=preference_id)
    if item is None:
        raise not_found("Notification preference")

    return _notification_preference_data(item)


def update_notification_preference(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    preference_id: Any,
    payload: Any,
) -> Any:
    if (
        uow.notification_preferences.get_for_user(user_id=actor.id, preference_id=preference_id)
        is None
    ):
        raise not_found("Notification preference")
    item = uow.notification_preferences.update(
        user_id=actor.id,
        preference_id=preference_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    uow.commit()

    return _notification_preference_data(item)


def delete_notification_preference(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    preference_id: Any,
) -> Any:
    if (
        uow.notification_preferences.get_for_user(user_id=actor.id, preference_id=preference_id)
        is None
    ):
        raise not_found("Notification preference")
    uow.notification_preferences.soft_delete(user_id=actor.id, preference_id=preference_id)
    uow.commit()

    return {"deleted": True}
