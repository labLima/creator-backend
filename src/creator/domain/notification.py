"""Notification vocabulary mirrored from the final modeling.

The values are the physical vocabulary of ``Creator_DB_final.sql``; the
database renders them as VARCHAR plus CHECK (SQLite has no native enum), while
the API validates payloads against these classes.
"""

from __future__ import annotations

from enum import StrEnum


class NotificationType(StrEnum):
    CONTENT_GENERATION = "CONTENT_GENERATION"
    CONTENT_APPROVAL = "CONTENT_APPROVAL"
    INVITE = "INVITE"
    BILLING = "BILLING"
    CREDITS = "CREDITS"
    COUPON = "COUPON"
    SYSTEM = "SYSTEM"


class NotificationResourceType(StrEnum):
    WORKSPACE_INVITE = "WORKSPACE_INVITE"
    WORKSPACE_MEMBER = "WORKSPACE_MEMBER"
    POST = "POST"
    GENERATED_IMAGE = "GENERATED_IMAGE"
    SUBSCRIPTION = "SUBSCRIPTION"
    ORDER = "ORDER"
    INVOICE = "INVOICE"
    CHARGE = "CHARGE"
    COUPON = "COUPON"


class NotificationChannel(StrEnum):
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"
    PUSH = "PUSH"


class NotificationDeliveryStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class DevicePlatform(StrEnum):
    IOS = "IOS"
    ANDROID = "ANDROID"
    WEB = "WEB"


__all__ = [
    "DevicePlatform",
    "NotificationChannel",
    "NotificationDeliveryStatus",
    "NotificationResourceType",
    "NotificationType",
]
