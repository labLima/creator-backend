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
from creator.api.responses import (
    success_response,
)
from creator.notification import service
from creator.notification.schemas import (
    NotificationCreateRequest,
    NotificationPreferenceRequest,
    NotificationUpdateRequest,
    UserDeviceCreateRequest,
    UserDeviceUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get(
    "/api/v1/notification-recipients",
    tags=["Notifications"],
    operation_id="list_notification_recipients_api_v1_notification_recipients_get",
)
def list_notification_recipients(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_notification_recipients(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post(
    "/api/v1/notification-recipients",
    tags=["Notifications"],
    operation_id="create_notification_recipient_api_v1_notification_recipients_post",
)
def create_notification_recipient(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_notification_recipient(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/notification-recipients/{id}",
    tags=["Notifications"],
    operation_id="get_notification_recipient_api_v1_notification_recipients__id__get",
)
def get_notification_recipient(
    recipient_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_notification_recipient(
            uow=unit_of_work, actor=current_user, recipient_id=recipient_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/notification-recipients/{id}",
    tags=["Notifications"],
    operation_id="update_notification_recipient_api_v1_notification_recipients__id__put",
)
def update_notification_recipient(
    recipient_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_notification_recipient(
            uow=unit_of_work,
            actor=current_user,
            recipient_id=recipient_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/notification-recipients/{id}",
    tags=["Notifications"],
    operation_id="delete_notification_recipient_api_v1_notification_recipients__id__delete",
)
def delete_notification_recipient(
    recipient_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_notification_recipient(
            uow=unit_of_work, actor=current_user, recipient_id=recipient_id, request=request
        ),
        request,
    )


@router.get("/api/v1/notifications", tags=["Notifications"], operation_id="listNotifications")
def list_notifications(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_notifications(
            uow=unit_of_work, actor=current_user, workspace_id=workspace_id, request=request
        ),
        request,
    )


@router.post("/api/v1/notifications", tags=["Notifications"], operation_id="createNotification")
def create_notification(
    payload: NotificationCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_notification(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/notifications/{id}", tags=["Notifications"], operation_id="getNotification")
def get_notification(
    notification_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_notification(
            uow=unit_of_work, actor=current_user, notification_id=notification_id, request=request
        ),
        request,
    )


@router.put("/api/v1/notifications/{id}", tags=["Notifications"], operation_id="updateNotification")
def update_notification(
    notification_id: Annotated[UUID, Path(alias="id")],
    payload: NotificationUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_notification(
            uow=unit_of_work,
            actor=current_user,
            notification_id=notification_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/notifications/{id}", tags=["Notifications"], operation_id="deleteNotification"
)
def delete_notification(
    notification_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_notification(
            uow=unit_of_work, actor=current_user, notification_id=notification_id, request=request
        ),
        request,
    )


@router.get("/api/v1/user-devices", tags=["Notifications"], operation_id="listUserDevices")
def list_user_devices(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_user_devices(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/user-devices", tags=["Notifications"], operation_id="createUserDevice")
def create_user_device(
    payload: UserDeviceCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_user_device(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/user-devices/{id}", tags=["Notifications"], operation_id="getUserDevice")
def get_user_device(
    device_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_user_device(
            uow=unit_of_work, actor=current_user, device_id=device_id, request=request
        ),
        request,
    )


@router.put("/api/v1/user-devices/{id}", tags=["Notifications"], operation_id="updateUserDevice")
def update_user_device(
    device_id: Annotated[UUID, Path(alias="id")],
    payload: UserDeviceUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_user_device(
            uow=unit_of_work,
            actor=current_user,
            device_id=device_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/user-devices/{id}", tags=["Notifications"], operation_id="deleteUserDevice")
def delete_user_device(
    device_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_user_device(
            uow=unit_of_work, actor=current_user, device_id=device_id, request=request
        ),
        request,
    )


@router.get(
    "/api/v1/notification-preferences",
    tags=["Notifications"],
    operation_id="listNotificationPreferences",
)
def list_notification_preferences(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_notification_preferences(
            uow=unit_of_work, actor=current_user, request=request
        ),
        request,
    )


@router.post(
    "/api/v1/notification-preferences",
    tags=["Notifications"],
    operation_id="createNotificationPreference",
)
def create_notification_preference(
    payload: NotificationPreferenceRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_notification_preference(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/notification-preferences/{id}",
    tags=["Notifications"],
    operation_id="getNotificationPreference",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_notification_preference(
    preference_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_notification_preference(
            uow=unit_of_work, actor=current_user, preference_id=preference_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/notification-preferences/{id}",
    tags=["Notifications"],
    operation_id="updateNotificationPreference",
)
def update_notification_preference(
    preference_id: Annotated[UUID, Path(alias="id")],
    payload: NotificationPreferenceRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_notification_preference(
            uow=unit_of_work,
            actor=current_user,
            preference_id=preference_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/notification-preferences/{id}",
    tags=["Notifications"],
    operation_id="deleteNotificationPreference",
)
def delete_notification_preference(
    preference_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_notification_preference(
            uow=unit_of_work, actor=current_user, preference_id=preference_id, request=request
        ),
        request,
    )
