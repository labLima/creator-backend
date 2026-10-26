from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.db import Base

from ..types import json_type, timestamp_tz, uuid_default, uuid_pk


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_outbox_events_dispatch", "published_at", "available_at"),
        Index("ix_outbox_events_workspace", "workspace_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    aggregate_id: Mapped[UUID] = mapped_column(uuid_pk, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_version: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(json_type, nullable=False)
    attempts: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    available_at: Mapped[object] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
    published_at: Mapped[object | None] = mapped_column(timestamp_tz)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
