from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
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

from ..enums import (
    GenerationType,
    generation_type_enum,
)
from ..types import json_type, timestamp_tz, uuid_default, uuid_pk


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_generations_id_workspace_id"),
        UniqueConstraint(
            "id", "workspace_id", "content_id", name="uq_generations_id_workspace_content_id"
        ),
        ForeignKeyConstraint(
            ["content_id", "workspace_id"],
            ["contents.id", "contents.workspace_id"],
            name="fk_generations_content_workspace",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["brand_id", "workspace_id"],
            ["brands.id", "brands.workspace_id"],
            name="fk_generations_brand_workspace",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["projects.id", "projects.workspace_id"],
            name="fk_generations_project_workspace",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(prompt) BETWEEN 1 AND 20000", name="ck_generations_prompt_length"),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at >= created_at",
            name="ck_generations_deleted_after_created",
        ),
        Index("ix_generations_requested_by_user_id", "requested_by_user_id"),
        Index(
            "ix_generations_workspace_filter", "workspace_id", "type", "deleted_at", "created_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_id: Mapped[UUID] = mapped_column(uuid_pk, nullable=False)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        uuid_pk,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    brand_id: Mapped[UUID | None] = mapped_column(uuid_pk)
    project_id: Mapped[UUID | None] = mapped_column(uuid_pk)
    generation_type: Mapped[GenerationType] = mapped_column(
        "type",
        generation_type_enum,
        nullable=False,
        server_default=text("'IMAGE'"),
    )
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(
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
