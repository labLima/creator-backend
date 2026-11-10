"""SQLAlchemy tables owned by the order capability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "amount_cents = subtotal_cents - discount_cents",
            name="chk_orders_amount_consistency",
        ),
        CheckConstraint(
            "subtotal_cents >= 0 AND amount_cents >= 0 AND "
            "(discount_cents IS NULL OR discount_cents >= 0)",
            name="chk_orders_cents_nonnegative",
        ),
        CheckConstraint(
            "currency IS NULL OR " + currency_code_check("currency"),
            name="chk_orders_currency_format",
        ),
        Index("uq_orders_id_workspace_id", "id", "workspace_id", unique=True),
        Index("uq_orders_provider_external_id", "provider", "external_id", unique=True),
        Index("ix_orders_billing_account_id", "billing_account_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_workspace_id", "workspace_id"),
        Index(
            "idx_m8_orders_credit_package_id",
            "credit_package_id",
            sqlite_where=text("credit_package_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    billing_account_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("billing_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    workspace_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    credit_package_id: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("credit_packages.id", ondelete="SET NULL")
    )
    provider: Mapped[str] = mapped_column(
        enum_column("payment_provider", create_constraint=False),
        nullable=False,
        server_default=text("'PAGARME'"),
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str | None] = mapped_column(String(52))
    subtotal_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_cents: Mapped[int | None] = mapped_column(BigInteger)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    status: Mapped[str] = mapped_column(
        enum_column("order_status", create_constraint=False), nullable=False
    )
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
