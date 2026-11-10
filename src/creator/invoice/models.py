"""SQLAlchemy tables owned by the invoice capability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(
            "amount_cents >= 0 AND (total_discount_cents IS NULL OR total_discount_cents >= 0) "
            "AND (total_increment_cents IS NULL OR total_increment_cents >= 0)",
            name="chk_invoices_cents_nonnegative",
        ),
        CheckConstraint(
            "installments IS NULL OR installments >= 1", name="chk_invoices_installments"
        ),
        CheckConstraint(
            "currency IS NULL OR " + currency_code_check("currency"),
            name="chk_invoices_currency_format",
        ),
        Index("uq_invoices_provider_external_id", "provider", "external_id", unique=True),
        Index("ix_invoices_billing_account_id", "billing_account_id"),
        Index("ix_invoices_status_due_at", "status", "due_at"),
        Index("ix_invoices_subscription_id_due_at", "subscription_id", "due_at"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    billing_account_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("billing_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    subscription_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        enum_column("payment_provider", create_constraint=False),
        nullable=False,
        server_default=text("'PAGARME'"),
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(String)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_discount_cents: Mapped[int | None] = mapped_column(BigInteger)
    total_increment_cents: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    status: Mapped[str] = mapped_column(
        enum_column("invoice_status", create_constraint=False), nullable=False
    )
    payment_method: Mapped[str | None] = mapped_column(
        enum_column("payment_method_type", create_constraint=False)
    )
    installments: Mapped[int | None] = mapped_column(Integer)
    billing_at: Mapped[datetime | None] = mapped_column(timestamp)
    seen_at: Mapped[datetime | None] = mapped_column(timestamp)
    due_at: Mapped[datetime | None] = mapped_column(timestamp)
    period_start: Mapped[datetime | None] = mapped_column(timestamp)
    period_end: Mapped[datetime | None] = mapped_column(timestamp)
    canceled_at: Mapped[datetime | None] = mapped_column(timestamp)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
