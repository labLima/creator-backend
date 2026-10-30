"""HTTP routes for the notification capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_uow,
)
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _notification_data,
    _notification_preference_data,
    _notification_recipient_data,
    _user_device_data,
)
from creator.application.unit_of_work import UnitOfWork
from creator.modules.notification.schemas import (
    NotificationCreateRequest,
    NotificationPreferenceRequest,
    NotificationUpdateRequest,
    UserDeviceCreateRequest,
    UserDeviceUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)

router = APIRouter()


@router.get("/api/v1/notification-recipients", tags=["Notifications"])
def list_notification_recipients(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _notification_recipient_data(x)
                for x in unit_of_work.notification_recipients.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/notification-recipients", tags=["Notifications"])
def create_notification_recipient(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    payload["user_id"] = current_user.id
    item = unit_of_work.notification_recipients.add(fields=payload)
    unit_of_work.commit()
    return success_response(_notification_recipient_data(item), request, status_code=201)


@router.get("/api/v1/notification-recipients/{id}", tags=["Notifications"])
def get_notification_recipient(
    recipient_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.notification_recipients.get_for_user(
        user_id=current_user.id, recipient_id=recipient_id
    )
    if item is None:
        raise not_found("Notification recipient")
    return success_response(_notification_recipient_data(item), request)


@router.put("/api/v1/notification-recipients/{id}", tags=["Notifications"])
def update_notification_recipient(
    recipient_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.notification_recipients.get_for_user(
            user_id=current_user.id, recipient_id=recipient_id
        )
        is None
    ):
        raise not_found("Notification recipient")
    item = unit_of_work.notification_recipients.update(recipient_id=recipient_id, fields=payload)
    unit_of_work.commit()
    return success_response(_notification_recipient_data(item), request)


@router.delete("/api/v1/notification-recipients/{id}", tags=["Notifications"])
def delete_notification_recipient(
    recipient_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.notification_recipients.get_for_user(
            user_id=current_user.id, recipient_id=recipient_id
        )
        is None
    ):
        raise not_found("Notification recipient")
    unit_of_work.notification_recipients.soft_delete(recipient_id=recipient_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/notifications", tags=["Notifications"])
def list_notifications(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    items = unit_of_work.notifications.list_for_user(
        user_id=current_user.id, workspace_id=workspace_id
    )
    return success_response({"items": [_notification_data(item) for item in items]}, request)


@router.post("/api/v1/notifications", tags=["Notifications"])
def create_notification(
    payload: NotificationCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    item = unit_of_work.notifications.add(
        workspace_id=payload.workspace_id,
        created_by=current_user.id,
        type=payload.type,
        title=payload.title,
        body=payload.body,
        payload=payload.payload,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    unit_of_work.commit()
    return success_response(_notification_data(item), request, status_code=201)


@router.get("/api/v1/notifications/{id}", tags=["Notifications"])
def get_notification(
    notification_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.notifications.get_for_user(
        user_id=current_user.id, notification_id=notification_id
    )
    if item is None:
        raise not_found("Notification")
    return success_response(_notification_data(item), request)


@router.put("/api/v1/notifications/{id}", tags=["Notifications"])
def update_notification(
    notification_id: Annotated[UUID, Path(alias="id")],
    payload: NotificationUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.notifications.get_for_user(
        user_id=current_user.id, notification_id=notification_id
    )
    if existing is None:
        raise not_found("Notification")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    item = unit_of_work.notifications.update(
        notification_id=notification_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_notification_data(item), request)


@router.delete("/api/v1/notifications/{id}", tags=["Notifications"])
def delete_notification(
    notification_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.notifications.get_for_user(
        user_id=current_user.id, notification_id=notification_id
    )
    if existing is None:
        raise not_found("Notification")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    unit_of_work.notifications.soft_delete(notification_id=notification_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/user-devices", tags=["Notifications"])
def list_user_devices(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    items = unit_of_work.user_devices.list_for_user(user_id=current_user.id)
    return success_response({"items": [_user_device_data(item) for item in items]}, request)


@router.post("/api/v1/user-devices", tags=["Notifications"])
def create_user_device(
    payload: UserDeviceCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.user_devices.add(
        user_id=current_user.id, platform=payload.platform, fcm_token=payload.fcm_token
    )
    unit_of_work.commit()
    return success_response(_user_device_data(item), request, status_code=201)


@router.get("/api/v1/user-devices/{id}", tags=["Notifications"])
def get_user_device(
    device_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.user_devices.get_for_user(user_id=current_user.id, device_id=device_id)
    if item is None:
        raise not_found("User device")
    return success_response(_user_device_data(item), request)


@router.put("/api/v1/user-devices/{id}", tags=["Notifications"])
def update_user_device(
    device_id: Annotated[UUID, Path(alias="id")],
    payload: UserDeviceUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.user_devices.get_for_user(user_id=current_user.id, device_id=device_id) is None:
        raise not_found("User device")
    item = unit_of_work.user_devices.update(
        user_id=current_user.id,
        device_id=device_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    unit_of_work.commit()
    return success_response(_user_device_data(item), request)


@router.delete("/api/v1/user-devices/{id}", tags=["Notifications"])
def delete_user_device(
    device_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.user_devices.get_for_user(user_id=current_user.id, device_id=device_id) is None:
        raise not_found("User device")
    unit_of_work.user_devices.soft_delete(user_id=current_user.id, device_id=device_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/notification-preferences", tags=["Notifications"])
def list_notification_preferences(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    items = unit_of_work.notification_preferences.list_for_user(user_id=current_user.id)
    return success_response(
        {"items": [_notification_preference_data(item) for item in items]}, request
    )


@router.post("/api/v1/notification-preferences", tags=["Notifications"])
def create_notification_preference(
    payload: NotificationPreferenceRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.notification_preferences.add(
        user_id=current_user.id,
        type=payload.type,
        channel=payload.channel,
        is_enabled=payload.is_enabled,
    )
    unit_of_work.commit()
    return success_response(_notification_preference_data(item), request, status_code=201)


@router.get("/api/v1/notification-preferences/{id}", tags=["Notifications"])
def get_notification_preference(
    preference_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.notification_preferences.get_for_user(
        user_id=current_user.id, preference_id=preference_id
    )
    if item is None:
        raise not_found("Notification preference")
    return success_response(_notification_preference_data(item), request)


@router.put("/api/v1/notification-preferences/{id}", tags=["Notifications"])
def update_notification_preference(
    preference_id: Annotated[UUID, Path(alias="id")],
    payload: NotificationPreferenceRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.notification_preferences.get_for_user(
            user_id=current_user.id, preference_id=preference_id
        )
        is None
    ):
        raise not_found("Notification preference")
    item = unit_of_work.notification_preferences.update(
        user_id=current_user.id,
        preference_id=preference_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    unit_of_work.commit()
    return success_response(_notification_preference_data(item), request)


@router.delete("/api/v1/notification-preferences/{id}", tags=["Notifications"])
def delete_notification_preference(
    preference_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.notification_preferences.get_for_user(
            user_id=current_user.id, preference_id=preference_id
        )
        is None
    ):
        raise not_found("Notification preference")
    unit_of_work.notification_preferences.soft_delete(
        user_id=current_user.id, preference_id=preference_id
    )
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
