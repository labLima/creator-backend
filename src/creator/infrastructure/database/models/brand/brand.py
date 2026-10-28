from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_brands_id_workspace_id"),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_brands_deleted_after_created",
        ),
        Index("ix_brands_workspace_filter", "workspace_id", "deleted_at", "created_at"),
        Index("ix_brands_created_by_user_id", "created_by_user_id"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        uuid_pk,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    brand_voice: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata",
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
    deleted_at: Mapped[object | None] = mapped_column(timestamp_tz)
