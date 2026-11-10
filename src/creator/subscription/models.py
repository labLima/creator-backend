"""SQLAlchemy tables owned by the subscription capability."""

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


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "installments IS NULL OR installments >= 1",
            name="chk_subscriptions_installments",
        ),
        CheckConstraint(
            "contracted_price_cents >= 0 AND "
            "(minimum_price_cents IS NULL OR minimum_price_cents >= 0)",
            name="chk_subscriptions_cents_nonnegative",
        ),
        CheckConstraint(currency_code_check("currency"), name="chk_subscriptions_currency_format"),
        Index("uq_subscriptions_id_workspace_id", "id", "workspace_id", unique=True),
        Index(
            "uq_subscriptions_provider_external_id",
            "provider",
            "external_id",
            unique=True,
        ),
        Index("ix_subscriptions_billing_account_id", "billing_account_id"),
        Index("ix_subscriptions_next_billing_at", "next_billing_at"),
        Index("ix_subscriptions_workspace_id", "workspace_id"),
        Index(
            "uq_subscriptions_workspace_current",
            "workspace_id",
            unique=True,
            sqlite_where=text("status IN ('ACTIVE', 'TRIALING', 'PAST_DUE')"),
        ),
        Index("idx_m8_subscriptions_plan_id", "plan_id"),
        Index(
            "idx_m8_subscriptions_payment_method_id",
            "payment_method_id",
            sqlite_where=text("payment_method_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    billing_account_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("billing_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    contracted_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    status: Mapped[str] = mapped_column(
        enum_column("subscription_status", create_constraint=False), nullable=False
    )
    provider_status: Mapped[str | None] = mapped_column(
        enum_column("provider_subscription_status", create_constraint=False)
    )
    status_reason: Mapped[str | None] = mapped_column(
        enum_column("subscription_status_reason", create_constraint=False)
    )
    provider: Mapped[str] = mapped_column(
        enum_column("payment_provider", create_constraint=False),
        nullable=False,
        server_default=text("'PAGARME'"),
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    external_code: Mapped[str | None] = mapped_column(String(52))
    payment_method: Mapped[str | None] = mapped_column(
        enum_column("payment_method_type", create_constraint=False)
    )
    payment_method_id: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("billing_payment_methods.id", ondelete="SET NULL")
    )
    billing_type: Mapped[str | None] = mapped_column(
        enum_column("billing_type", create_constraint=False)
    )
    billing_interval: Mapped[str | None] = mapped_column(
        enum_column("billing_interval", create_constraint=False)
    )
    interval_count: Mapped[int | None] = mapped_column(Integer)
    installments: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    minimum_price_cents: Mapped[int | None] = mapped_column(BigInteger)
    statement_descriptor: Mapped[str | None] = mapped_column(String(22))
    trial_period_days: Mapped[int | None] = mapped_column(Integer)
    current_cycle_id: Mapped[str | None] = mapped_column(String(64))
    current_period_start: Mapped[datetime | None] = mapped_column(timestamp)
    current_period_end: Mapped[datetime | None] = mapped_column(timestamp)
    next_billing_at: Mapped[datetime | None] = mapped_column(timestamp)
    canceled_at: Mapped[datetime | None] = mapped_column(timestamp)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SubscriptionHistory(Base):
    __tablename__ = "subscription_history"
    __table_args__ = (
        Index("ix_subscription_history_subscription_created", "subscription_id", "created_at"),
        Index(
            "idx_m8_subscription_history_old_plan_id",
            "old_plan_id",
            sqlite_where=text("old_plan_id IS NOT NULL"),
        ),
        Index(
            "idx_m8_subscription_history_new_plan_id",
            "new_plan_id",
            sqlite_where=text("new_plan_id IS NOT NULL"),
        ),
        Index(
            "idx_m8_subscription_history_changed_by",
            "changed_by",
            sqlite_where=text("changed_by IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    subscription_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    change_type: Mapped[str] = mapped_column(
        enum_column("subscription_change_type", create_constraint=False), nullable=False
    )
    old_plan_id: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("plans.id", ondelete="SET NULL")
    )
    new_plan_id: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("plans.id", ondelete="SET NULL")
    )
    old_status: Mapped[str | None] = mapped_column(
        enum_column("subscription_status", create_constraint=False)
    )
    new_status: Mapped[str | None] = mapped_column(
        enum_column("subscription_status", create_constraint=False)
    )
    old_provider_status: Mapped[str | None] = mapped_column(
        enum_column("provider_subscription_status", create_constraint=False)
    )
    new_provider_status: Mapped[str | None] = mapped_column(
        enum_column("provider_subscription_status", create_constraint=False)
    )
    changed_by: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("users.id", ondelete="SET NULL")
    )
    reason_code: Mapped[str | None] = mapped_column(
        enum_column("subscription_status_reason", create_constraint=False)
    )
    reason_text: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
