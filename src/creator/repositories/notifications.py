"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.notification.ports import (
    NotificationPreferenceRecord,
    NotificationPreferenceRepository,
    NotificationRecipientRecord,
    NotificationRecipientRepository,
    NotificationRecord,
    NotificationRepository,
    UserDeviceRecord,
    UserDeviceRepository,
)

__all__ = [
    "NotificationPreferenceRecord",
    "NotificationPreferenceRepository",
    "NotificationRecipientRecord",
    "NotificationRecipientRepository",
    "NotificationRecord",
    "NotificationRepository",
    "UserDeviceRecord",
    "UserDeviceRepository",
]
