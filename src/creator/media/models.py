"""SQLAlchemy tables for the media redesign (expand step T11).

``generated_images`` replaces the flat ``generated_image`` row with storage,
generation status, current-image and approval/feedback metadata;
``image_resizes`` holds the derived aspect-ratio variants.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.db import Base
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class GeneratedImage(Base):
    __tablename__ = "generated_images"
    __table_args__ = (
        Index(
            "uq_generated_images_current_per_slide",
            "design_slide_id",
            unique=True,
            sqlite_where=text("is_current AND deleted_at IS NULL"),
            postgresql_where=text("is_current AND deleted_at IS NULL"),
        ),
        Index("ix_generated_images_design_slide_id", "design_slide_id"),
        Index("ix_generated_images_generation_status", "generation_status"),
        Index("ix_generated_images_approval_status", "approval_status"),
        Index("ix_generated_images_approved_by", "approved_by"),
        Index(
            "uq_generated_images_storage_bucket_storage_key",
            "storage_bucket",
            "storage_key",
            unique=True,
        ),
        Index(
            "idx_m8_generated_images_created_by",
            "created_by",
            sqlite_where=text("created_by IS NOT NULL"),
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        CheckConstraint(
            "NOT is_current OR (generation_status = 'SUCCEEDED' AND deleted_at IS NULL)",
            name="chk_generated_images_current_complete",
        ),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0", name="chk_generated_images_size_bytes"
        ),
        CheckConstraint(
            "width IS NULL OR height IS NULL OR (width > 0 AND height > 0)",
            name="chk_generated_images_dimensions",
        ),
        CheckConstraint(
            "(approved_at IS NULL) = (approved_by IS NULL)",
            name="chk_generated_images_approval_pair",
        ),
        CheckConstraint(
            "approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL",
            name="chk_generated_images_rejected_reason",
        ),
        CheckConstraint(
            "approval_status <> 'APPROVED' "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="chk_generated_images_approved_metadata",
        ),
        CheckConstraint(
            "approval_status = 'PENDING' OR generation_status = 'SUCCEEDED'",
            name="chk_generated_images_approval_after_generation",
        ),
        CheckConstraint(
            "generation_status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL "
            "AND storage_key IS NOT NULL AND size_bytes IS NOT NULL "
            "AND width IS NOT NULL AND height IS NOT NULL)",
            name="chk_generated_images_file_by_status",
        ),
        CheckConstraint(
            "generation_status <> 'FAILED' OR error_message IS NOT NULL",
            name="chk_generated_images_failed_message",
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    design_slide_id: Mapped[UUID] = mapped_column(
        ForeignKey("design_slides.id", ondelete="CASCADE"), nullable=False
    )
    storage_bucket: Mapped[str | None] = mapped_column(String(63))
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str] = mapped_column(
        String(127), nullable=False, server_default=text("'image/png'")
    )
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    model: Mapped[str | None] = mapped_column(String(50))
    prompt: Mapped[str | None] = mapped_column(String)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String)
    generation_status: Mapped[str] = mapped_column(
        enum_column("generation_status"),
        nullable=False,
        server_default=text("'GENERATING'"),
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    approval_status: Mapped[str] = mapped_column(
        enum_column("approval_status"), nullable=False, server_default=text("'PENDING'")
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(timestamp)
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    feedback_type: Mapped[str | None] = mapped_column(
        enum_column("image_feedback_type"), nullable=True
    )
    feedback_text: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(timestamp)


class ImageResize(Base):
    __tablename__ = "image_resizes"
    __table_args__ = (
        Index("idx_image_resizes_source_image", "source_image_id"),
        Index(
            "uq_image_resizes_storage",
            "storage_bucket",
            "storage_key",
            unique=True,
        ),
        Index(
            "idx_image_resizes_created_by",
            "created_by",
            sqlite_where=text("created_by IS NOT NULL"),
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        CheckConstraint(
            "status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL "
            "AND storage_key IS NOT NULL AND size_bytes IS NOT NULL "
            "AND width IS NOT NULL AND height IS NOT NULL)",
            name="chk_image_resizes_file",
        ),
        CheckConstraint(
            "status <> 'FAILED' OR error_message IS NOT NULL",
            name="chk_image_resizes_failed",
        ),
        CheckConstraint("size_bytes IS NULL OR size_bytes > 0", name="chk_image_resizes_size"),
        CheckConstraint(
            "(width IS NULL OR width > 0) AND (height IS NULL OR height > 0)",
            name="chk_image_resizes_dimensions",
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    source_image_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_images.id", ondelete="CASCADE"), nullable=False
    )
    ratio: Mapped[str] = mapped_column(enum_column("art_ratio"), nullable=False)
    status: Mapped[str] = mapped_column(
        enum_column("resize_status"), nullable=False, server_default=text("'PENDING'")
    )
    storage_bucket: Mapped[str | None] = mapped_column(String(63))
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(127))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(String)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
