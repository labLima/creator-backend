"""SQLAlchemy tables owned by the content plan capability.

Expand slice of the planning redesign: ``content_plans`` replaces the inline
persona and quantity columns of the legacy ``planning`` table, with items and
special dates in their own tables. The legacy table stays until the contract
step (T13).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
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


class ContentPlan(Base):
    __tablename__ = "content_plans"
    __table_args__ = (
        Index("ix_content_plans_brand_id", "brand_id"),
        Index("ix_content_plans_campaign_id", "campaign_id"),
        Index("ix_content_plans_persona_id", "persona_id"),
        Index("idx_m8_content_plans_campaign_id_brand_id", "campaign_id", "brand_id"),
        Index("idx_m8_content_plans_persona_id_brand_id", "persona_id", "brand_id"),
        Index(
            "idx_m8_content_plans_created_by",
            "created_by",
            sqlite_where=text("created_by IS NOT NULL"),
        ),
        ForeignKeyConstraint(
            ["campaign_id", "brand_id"],
            ["campaigns.id", "campaigns.brand_id"],
            ondelete="CASCADE",
            name="fk_content_plans_campaign",
        ),
        ForeignKeyConstraint(
            ["persona_id", "brand_id"],
            ["personas.id", "personas.brand_id"],
            ondelete="CASCADE",
            name="fk_content_plans_persona",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="chk_content_plans_period_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    brand_id: Mapped[UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[UUID] = mapped_column(uuid_pk, nullable=False)
    persona_id: Mapped[UUID] = mapped_column(uuid_pk, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    briefing: Mapped[str | None] = mapped_column(String(400))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(timestamp)


class ContentPlanItem(Base):
    __tablename__ = "content_plan_items"
    __table_args__ = (
        Index(
            "uq_content_plan_items_content_plan_id_format",
            "content_plan_id",
            "format",
            unique=True,
        ),
        CheckConstraint("quantity >= 0", name="ck_content_plan_items_quantity"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    content_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_plans.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(enum_column("content_format"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ContentPlanSpecialDate(Base):
    __tablename__ = "content_plan_special_dates"
    __table_args__ = (
        Index(
            "uq_content_plan_special_dates_plan_date_label",
            "content_plan_id",
            "special_date",
            "label",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    content_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_plans.id", ondelete="CASCADE"), nullable=False
    )
    special_date: Mapped[date] = mapped_column(Date, nullable=False)
    label: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
