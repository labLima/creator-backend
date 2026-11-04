from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.db import Base
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_default, uuid_pk


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (
        CheckConstraint("entity_type = 'brand'", name="ck_activity_events_entity_type"),
        CheckConstraint(
            "event_type IN ('brand.created', 'brand.updated', 'brand.deleted')",
            name="ck_activity_events_event_type",
        ),
        Index("ix_activity_events_workspace_created", "workspace_id", "created_at", "id"),
        Index("ix_activity_events_user", "user_id"),
        Index("ix_activity_events_brand", "brand_id"),
        Index("ix_activity_events_entity", "entity_type", "entity_id"),
    )
    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("users.id", ondelete="RESTRICT")
    )
    brand_id: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("brands.id", ondelete="RESTRICT")
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(uuid_pk)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", json_type, nullable=False, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
