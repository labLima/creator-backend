from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database import schema_models as _schema_models  # noqa: F401
from creator.infrastructure.database.db import Base

from ..types import json_type, timestamp_tz, uuid_default, uuid_pk


class BrandSettings(Base):
    __tablename__ = "brand_settings"
    __table_args__ = (
        UniqueConstraint("brand_id", name="uq_brand_settings_brand_id"),
        ForeignKeyConstraint(
            ["brand_id", "workspace_id"],
            ["brands.id", "brands.workspace_id"],
            name="fk_brand_settings_brand_workspace",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_brand_settings_deleted_after_created",
        ),
        Index("ix_brand_settings_workspace_id", "workspace_id"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    brand_id: Mapped[UUID] = mapped_column(uuid_pk, nullable=False)
    voice_settings: Mapped[dict[str, object]] = mapped_column(
        json_type,
        nullable=False,
        server_default=text("'{}'"),
    )
    visual_settings: Mapped[dict[str, object]] = mapped_column(
        json_type,
        nullable=False,
        server_default=text("'{}'"),
    )
    generation_defaults: Mapped[dict[str, object]] = mapped_column(
        json_type,
        nullable=False,
        server_default=text("'{}'"),
    )
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
