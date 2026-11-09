"""SQLAlchemy tables owned by the audit capability.

``audit_logs`` is append-only: it has no ``updated_at`` and no ``deleted_at``,
matching ``Creator_DB_final.sql``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.db import Base
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index(
            "ix_audit_logs_entity_type_entity_id_created_at",
            "entity_type",
            "entity_id",
            "created_at",
        ),
        Index("ix_audit_logs_actor_id_created_at", "actor_id", "created_at"),
        Index("ix_audit_logs_workspace_id_created_at", "workspace_id", "created_at"),
        Index("ix_audit_logs_action_created_at", "action", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    workspace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(uuid_pk, nullable=False)
    before: Mapped[dict[str, object] | None] = mapped_column(json_type)
    after: Mapped[dict[str, object] | None] = mapped_column(json_type)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
