"""SQLAlchemy tables owned by the plan capability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint(
            "price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0)",
            name="chk_plans_cents_nonnegative",
        ),
        CheckConstraint(currency_code_check("currency"), name="chk_plans_currency_format"),
        Index(
            "uq_plans_provider_external_id",
            "provider",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(
        enum_column("plan_type", create_constraint=False), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        enum_column("payment_provider", create_constraint=False),
        nullable=False,
        server_default=text("'PAGARME'"),
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    credits_per_month: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_validity_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("30")
    )
    billing_interval: Mapped[str] = mapped_column(
        enum_column("billing_interval", create_constraint=False),
        nullable=False,
        server_default=text("'MONTH'"),
    )
    interval_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    billing_type: Mapped[str] = mapped_column(
        enum_column("billing_type", create_constraint=False),
        nullable=False,
        server_default=text("'PREPAID'"),
    )
    minimum_price_cents: Mapped[int | None] = mapped_column(BigInteger)
    trial_period_days: Mapped[int | None] = mapped_column(Integer)
    statement_descriptor: Mapped[str | None] = mapped_column(String(22))
    status: Mapped[str] = mapped_column(
        enum_column("catalog_status", create_constraint=False),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(timestamp)


class PlanItem(Base):
    __tablename__ = "plan_items"
    __table_args__ = (
        CheckConstraint(
            "price_cents IS NULL OR price_cents >= 0",
            name="chk_plan_items_price_nonnegative",
        ),
        CheckConstraint(currency_code_check("currency"), name="chk_plan_items_currency_format"),
        Index("idx_m8_plan_items_plan_id", "plan_id"),
        Index(
            "uq_plan_items_provider_external_id",
            "provider",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        enum_column("payment_provider", create_constraint=False),
        nullable=False,
        server_default=text("'PAGARME'"),
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    cycles: Mapped[int | None] = mapped_column(Integer)
    pricing_scheme_type: Mapped[str | None] = mapped_column(
        enum_column("pricing_scheme_type", create_constraint=False), nullable=True
    )
    price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    price_brackets: Mapped[dict[str, object] | None] = mapped_column(json_type)
    status: Mapped[str] = mapped_column(
        enum_column("catalog_status", create_constraint=False),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlanPaymentMethod(Base):
    __tablename__ = "plan_payment_methods"
    __table_args__ = (
        Index("uq_plan_payment_methods_plan_id_method", "plan_id", "method", unique=True),
        CheckConstraint("max_installments >= 1", name="chk_plan_payment_methods_max_installments"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    method: Mapped[str] = mapped_column(enum_column("payment_method_type"), nullable=False)
    max_installments: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
