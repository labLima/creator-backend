"""SQLAlchemy tables for the editorial redesign (expand step T10).

``posts`` replaces the flat ``post_structure`` row: publication and approval
status live on the post, captions are versioned, and art is split into
``post_designs`` and ``design_slides``. The legacy tables stay until T13.

The dump's ``uq_captions_current`` predicate references a ``deleted_at`` column
that ``captions`` does not have; the index here filters on ``is_current`` only,
which keeps the invariant enforceable instead of creating a failing index.
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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.db import Base
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index(
            "ix_posts_content_plan_id_publication_status", "content_plan_id", "publication_status"
        ),
        Index("ix_posts_content_plan_id_created_at", "content_plan_id", "created_at"),
        Index("ix_posts_publication_status", "publication_status"),
        Index("ix_posts_approval_status", "approval_status"),
        Index("ix_posts_scheduled_at", "scheduled_at"),
        Index("ix_posts_approved_by", "approved_by"),
        Index(
            "idx_m8_posts_created_by",
            "created_by",
            sqlite_where=text("created_by IS NOT NULL"),
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        CheckConstraint(
            "(approved_at IS NULL) = (approved_by IS NULL)",
            name="chk_posts_approval_pair",
        ),
        CheckConstraint(
            "approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL",
            name="chk_posts_rejected_reason",
        ),
        CheckConstraint(
            "approval_status <> 'APPROVED' "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="chk_posts_approved_metadata",
        ),
        CheckConstraint(
            "publication_status <> 'SCHEDULED' OR scheduled_at IS NOT NULL",
            name="chk_posts_scheduled_at",
        ),
        CheckConstraint(
            "publication_status <> 'PUBLISHED' OR published_at IS NOT NULL",
            name="chk_posts_published_at",
        ),
        CheckConstraint(
            "publication_status = 'DRAFT' OR approval_status = 'APPROVED'",
            name="chk_posts_publish_requires_approval",
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    content_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_plans.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(100))
    objective: Mapped[str | None] = mapped_column(String(300))
    big_idea: Mapped[str | None] = mapped_column(String(150))
    main_message: Mapped[str | None] = mapped_column(String(150))
    publication_status: Mapped[str] = mapped_column(
        enum_column("publication_status"), nullable=False, server_default=text("'DRAFT'")
    )
    approval_status: Mapped[str] = mapped_column(
        enum_column("approval_status"), nullable=False, server_default=text("'PENDING'")
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(timestamp)
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    scheduled_at: Mapped[datetime | None] = mapped_column(timestamp)
    published_at: Mapped[datetime | None] = mapped_column(timestamp)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(timestamp)


class Caption(Base):
    __tablename__ = "captions"
    __table_args__ = (
        Index("uq_captions_post_id_version", "post_id", "version", unique=True),
        Index(
            "uq_captions_current",
            "post_id",
            unique=True,
            sqlite_where=text("is_current"),
            postgresql_where=text("is_current"),
        ),
        Index(
            "idx_m8_captions_created_by",
            "created_by",
            sqlite_where=text("created_by IS NOT NULL"),
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        CheckConstraint("version >= 1", name="ck_captions_version"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PostDesign(Base):
    __tablename__ = "post_designs"
    __table_args__ = (
        Index("ix_post_designs_post_id", "post_id"),
        CheckConstraint(
            "format <> 'STORIES' OR ratio = 'RATIO_9_16'",
            name="chk_post_designs_stories_ratio",
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    post_id: Mapped[UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(enum_column("content_format"), nullable=False)
    ratio: Mapped[str] = mapped_column(enum_column("art_ratio"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DesignSlide(Base):
    __tablename__ = "design_slides"
    __table_args__ = (
        Index(
            "uq_design_slides_post_design_id_position",
            "post_design_id",
            "position",
            unique=True,
        ),
        CheckConstraint("position >= 0", name="ck_design_slides_position"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    post_design_id: Mapped[UUID] = mapped_column(
        ForeignKey("post_designs.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    headline: Mapped[str | None] = mapped_column(String(50))
    subtitle: Mapped[str | None] = mapped_column(String(40))
    cta: Mapped[str | None] = mapped_column(String(30))
    art_direction: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
