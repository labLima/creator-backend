"""SQLAlchemy tables owned by the payment_method capability."""

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
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class BillingPaymentMethod(Base):
    __tablename__ = "billing_payment_methods"
    __table_args__ = (
        CheckConstraint(
            "exp_month IS NULL OR exp_month BETWEEN 1 AND 12",
            name="chk_billing_payment_methods_exp_month",
        ),
        CheckConstraint(
            "exp_year IS NULL OR exp_year BETWEEN 2000 AND 2100",
            name="chk_billing_payment_methods_exp_year",
        ),
        Index("ix_billing_payment_methods_account_default", "billing_account_id", "is_default"),
        Index(
            "idx_m8_billing_payment_methods_billing_address_id",
            "billing_address_id",
            sqlite_where=text("billing_address_id IS NOT NULL"),
        ),
        Index(
            "uq_billing_payment_methods_default",
            "billing_account_id",
            unique=True,
            sqlite_where=text("is_default AND status = 'ACTIVE'"),
        ),
        Index(
            "uq_billing_payment_methods_account_external_id",
            "billing_account_id",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    billing_account_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("billing_accounts.id", ondelete="CASCADE"), nullable=False
    )
    billing_address_id: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("billing_addresses.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    external_network_token_id: Mapped[str | None] = mapped_column(String(64))
    first_six_digits: Mapped[str | None] = mapped_column(String(6))
    brand: Mapped[str | None] = mapped_column(
        enum_column("card_brand", create_constraint=False), nullable=True
    )
    card_last_four: Mapped[str | None] = mapped_column(String(4))
    holder_name: Mapped[str | None] = mapped_column(String(64))
    holder_document: Mapped[str | None] = mapped_column(String(16))
    exp_month: Mapped[int | None] = mapped_column(Integer)
    exp_year: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[str | None] = mapped_column(
        enum_column("funding_source", create_constraint=False), nullable=True
    )
    status: Mapped[str] = mapped_column(
        enum_column("card_status", create_constraint=False),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
