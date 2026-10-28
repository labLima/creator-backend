from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database import schema_models as _schema_models  # noqa: F401
from creator.infrastructure.database.db import Base

from ..types import json_type, timestamp_tz, uuid_default, uuid_pk


class Settings(Base):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_settings_user_id"),
        Index("ix_settings_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    user_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    brand_name: Mapped[str | None] = mapped_column(String(255))
    segment: Mapped[str | None] = mapped_column(String(255))
    tone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'professional'"),
    )
    voice: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'Clear and useful'"),
    )
    visual_style: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'photographic'"),
    )
    default_preferences: Mapped[dict[str, object]] = mapped_column(
        json_type,
        nullable=False,
        server_default=text("'{}'"),
    )
    created_at: Mapped[object] = mapped_column(
        timestamp_tz,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        timestamp_tz,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
