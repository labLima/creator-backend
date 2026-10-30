"""Compatibility shim; implementations moved to capability repositories."""

from __future__ import annotations

from creator.notification.repository import (
    SqlAlchemyNotificationPreferenceRepository,
    SqlAlchemyNotificationRecipientRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyUserDeviceRepository,
)

__all__ = [
    "SqlAlchemyNotificationPreferenceRepository",
    "SqlAlchemyNotificationRecipientRepository",
    "SqlAlchemyNotificationRepository",
    "SqlAlchemyUserDeviceRepository",
]
