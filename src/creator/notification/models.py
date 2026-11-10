"""SQLAlchemy tables owned by the notification capability.

Aligned to ``Creator_DB_final.sql`` (ADR-028, T24): the four tables have no
``deleted_at`` because the final modeling does not define soft delete for
notifications; deletes are physical. Enum columns render as VARCHAR plus CHECK
through the portable vocabulary.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.db import Base
from creator.infrastructure.database.types import (
    enum_column,
    json_type,
    timestamp_tz,
    uuid_default,
    uuid_pk,
)

timestamp = timestamp_tz


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "(resource_type IS NULL) = (resource_id IS NULL)",
            name="chk_notifications_resource_pair",
        ),
        Index(
            "uq_notifications_workspace_dedupe",
            "workspace_id",
            "dedupe_key",
            unique=True,
        ),
        Index("ix_notifications_type", "type"),
        Index("ix_notifications_created_at", "created_at"),
        Index(
            "idx_m8_notifications_created_by",
            "created_by",
            sqlite_where=text("created_by IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(enum_column("notification_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str | None] = mapped_column(String(2000))
    payload: Mapped[dict[str, object] | None] = mapped_column(json_type)
    resource_type: Mapped[str | None] = mapped_column(
        enum_column("notification_resource_type"), nullable=True
    )
    resource_id: Mapped[UUID | None] = mapped_column(uuid_pk)
    dedupe_key: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"
    __table_args__ = (
        Index("ix_notification_recipients_user_channel", "user_id", "channel"),
        Index("ix_notification_recipients_user_read_at", "user_id", "read_at"),
        Index("ix_notification_recipients_user_created_at", "user_id", "created_at"),
        Index(
            "uq_notification_recipients_notification_user_channel",
            "notification_id",
            "user_id",
            "channel",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    notification_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(enum_column("notification_channel"), nullable=False)
    status: Mapped[str] = mapped_column(
        enum_column("notification_delivery_status"),
        nullable=False,
        server_default=text("'PENDING'"),
    )
    external_message_id: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    sent_at: Mapped[datetime | None] = mapped_column(timestamp)
    read_at: Mapped[datetime | None] = mapped_column(timestamp)
    created_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserDevice(Base):
    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint("fcm_token", name="uq_user_devices_fcm_token"),
        Index("ix_user_devices_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    user_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(enum_column("device_platform"), nullable=False)
    fcm_token: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_seen_at: Mapped[datetime | None] = mapped_column(timestamp)
    created_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index(
            "uq_notification_preferences_user_type_channel",
            "user_id",
            "type",
            "channel",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    user_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(enum_column("notification_type"), nullable=False)
    channel: Mapped[str] = mapped_column(enum_column("notification_channel"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now(), onupdate=func.now()
    )
