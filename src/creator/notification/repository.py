"""SQLAlchemy implementation of the notification persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.notification.models as notification_models
import creator.workspace.models as workspace_models
from creator.infrastructure.persistence.sql import now
from creator.notification.ports import (
    NotificationPreferenceRecord,
    NotificationRecipientRecord,
    NotificationRecipientRepository,
    NotificationRecord,
    UserDeviceRecord,
)


def _device(row: notification_models.UserDevice) -> UserDeviceRecord:
    return UserDeviceRecord(
        id=row.id,
        user_id=row.user_id,
        platform=row.platform,
        fcm_token=row.fcm_token,
        is_active=row.is_active,
        last_seen_at=row.last_seen_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyUserDeviceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, *, user_id: UUID) -> list[UserDeviceRecord]:
        rows = self._session.scalars(
            select(notification_models.UserDevice)
            .where(
                notification_models.UserDevice.user_id == user_id,
                notification_models.UserDevice.deleted_at.is_(None),
            )
            .order_by(notification_models.UserDevice.created_at.desc())
        ).all()
        return [_device(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, device_id: UUID) -> UserDeviceRecord | None:
        row = self._session.scalars(
            select(notification_models.UserDevice).where(
                notification_models.UserDevice.id == device_id,
                notification_models.UserDevice.user_id == user_id,
                notification_models.UserDevice.deleted_at.is_(None),
            )
        ).one_or_none()
        return _device(row) if row else None

    def add(self, *, user_id: UUID, platform: str, fcm_token: str) -> UserDeviceRecord:
        row = notification_models.UserDevice(
            user_id=user_id, platform=platform, fcm_token=fcm_token, is_active=True
        )
        self._session.add(row)
        self._session.flush()
        return _device(row)

    def update(
        self, *, user_id: UUID, device_id: UUID, fields: dict[str, object]
    ) -> UserDeviceRecord:
        row = self._get_row(user_id=user_id, device_id=device_id)
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = now()
        self._session.flush()
        return _device(row)

    def soft_delete(self, *, user_id: UUID, device_id: UUID) -> None:
        row = self._get_row(user_id=user_id, device_id=device_id)
        timestamp = now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()

    def _get_row(self, *, user_id: UUID, device_id: UUID) -> notification_models.UserDevice:
        row = self._session.scalars(
            select(notification_models.UserDevice).where(
                notification_models.UserDevice.id == device_id,
                notification_models.UserDevice.user_id == user_id,
                notification_models.UserDevice.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise ValueError("User device not found")
        return row


def _preference(row: notification_models.NotificationPreference) -> NotificationPreferenceRecord:
    return NotificationPreferenceRecord(
        id=row.id,
        user_id=row.user_id,
        type=row.type,
        channel=row.channel,
        is_enabled=row.is_enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyNotificationPreferenceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, *, user_id: UUID) -> list[NotificationPreferenceRecord]:
        rows = self._session.scalars(
            select(notification_models.NotificationPreference)
            .where(
                notification_models.NotificationPreference.user_id == user_id,
                notification_models.NotificationPreference.deleted_at.is_(None),
            )
            .order_by(notification_models.NotificationPreference.created_at.desc())
        ).all()
        return [_preference(row) for row in rows]

    def get_for_user(
        self, *, user_id: UUID, preference_id: UUID
    ) -> NotificationPreferenceRecord | None:
        row = self._session.scalars(
            select(notification_models.NotificationPreference).where(
                notification_models.NotificationPreference.id == preference_id,
                notification_models.NotificationPreference.user_id == user_id,
                notification_models.NotificationPreference.deleted_at.is_(None),
            )
        ).one_or_none()
        return _preference(row) if row else None

    def add(
        self, *, user_id: UUID, type: str, channel: str, is_enabled: bool
    ) -> NotificationPreferenceRecord:
        row = notification_models.NotificationPreference(
            user_id=user_id, type=type, channel=channel, is_enabled=is_enabled
        )
        self._session.add(row)
        self._session.flush()
        return _preference(row)

    def update(
        self, *, user_id: UUID, preference_id: UUID, fields: dict[str, object]
    ) -> NotificationPreferenceRecord:
        row = self._get_row(user_id=user_id, preference_id=preference_id)
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = now()
        self._session.flush()
        return _preference(row)

    def soft_delete(self, *, user_id: UUID, preference_id: UUID) -> None:
        row = self._get_row(user_id=user_id, preference_id=preference_id)
        timestamp = now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()

    def _get_row(
        self, *, user_id: UUID, preference_id: UUID
    ) -> notification_models.NotificationPreference:
        row = self._session.scalars(
            select(notification_models.NotificationPreference).where(
                notification_models.NotificationPreference.id == preference_id,
                notification_models.NotificationPreference.user_id == user_id,
                notification_models.NotificationPreference.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise ValueError("Notification preference not found")
        return row


def _notification(row: notification_models.Notification) -> NotificationRecord:
    return NotificationRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        type=row.type,
        title=row.title,
        body=row.body,
        payload=dict(row.payload or {}),
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyNotificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(
        self, *, user_id: UUID, workspace_id: UUID | None = None
    ) -> list[NotificationRecord]:
        statement = (
            select(notification_models.Notification)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == notification_models.Notification.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                notification_models.Notification.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            statement = statement.where(
                notification_models.Notification.workspace_id == workspace_id
            )
        rows = self._session.scalars(
            statement.order_by(notification_models.Notification.created_at.desc())
        ).all()
        return [_notification(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, notification_id: UUID) -> NotificationRecord | None:
        row = self._session.scalars(
            select(notification_models.Notification)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == notification_models.Notification.workspace_id,
            )
            .where(
                notification_models.Notification.id == notification_id,
                notification_models.Notification.deleted_at.is_(None),
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
            )
        ).one_or_none()
        return _notification(row) if row else None

    def add(
        self,
        *,
        workspace_id: UUID,
        created_by: UUID,
        type: str,
        title: str,
        body: str,
        payload: dict[str, object],
        resource_type: str | None,
        resource_id: UUID | None,
    ) -> NotificationRecord:
        row = notification_models.Notification(
            workspace_id=workspace_id,
            created_by=created_by,
            type=type,
            title=title,
            body=body,
            payload=payload,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self._session.add(row)
        self._session.flush()
        return _notification(row)

    def update(self, *, notification_id: UUID, fields: dict[str, object]) -> NotificationRecord:
        row = self._session.get(notification_models.Notification, notification_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Notification not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = now()
        self._session.flush()
        return _notification(row)

    def soft_delete(self, *, notification_id: UUID) -> None:
        row = self._session.get(notification_models.Notification, notification_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Notification not found")
        timestamp = now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()


class SqlAlchemyNotificationRecipientRepository(NotificationRecipientRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _r(self, x: notification_models.NotificationRecipient) -> NotificationRecipientRecord:
        return NotificationRecipientRecord(
            x.id,
            x.notification_id,
            x.user_id,
            x.workspace_member_id,
            x.channel,
            x.status,
            x.attempts,
            x.sent_at,
            x.read_at,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def list_for_user(self, *, user_id: UUID):
        rows = self._session.scalars(
            select(notification_models.NotificationRecipient).where(
                notification_models.NotificationRecipient.user_id == user_id,
                notification_models.NotificationRecipient.deleted_at.is_(None),
            )
        ).all()
        return [self._r(x) for x in rows]

    def get_for_user(self, *, user_id: UUID, recipient_id: UUID):
        x = self._session.scalar(
            select(notification_models.NotificationRecipient).where(
                notification_models.NotificationRecipient.id == recipient_id,
                notification_models.NotificationRecipient.user_id == user_id,
                notification_models.NotificationRecipient.deleted_at.is_(None),
            )
        )
        return self._r(x) if x else None

    def add(self, *, fields):
        x = notification_models.NotificationRecipient(**fields)
        self._session.add(x)
        self._session.flush()
        return self._r(x)

    def update(self, *, recipient_id, fields):
        x = self._session.get(notification_models.NotificationRecipient, recipient_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Notification recipient not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = now()
        self._session.flush()
        return self._r(x)

    def soft_delete(self, *, recipient_id):
        x = self._session.get(notification_models.NotificationRecipient, recipient_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Notification recipient not found")
        x.deleted_at = now()
        x.updated_at = x.deleted_at
        self._session.flush()
