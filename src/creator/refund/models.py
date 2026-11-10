"""SQLAlchemy tables owned by the refund capability."""

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


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint("amount_cents >= 0", name="chk_refunds_amount_nonnegative"),
        CheckConstraint(currency_code_check("currency"), name="chk_refunds_currency_format"),
        CheckConstraint(
            "(status = 'PENDING') = (processed_at IS NULL)",
            name="chk_refunds_processed_by_status",
        ),
        Index(
            "uq_refunds_provider_external_id",
            "provider",
            "external_id",
            unique=True,
        ),
        Index("ix_refunds_charge_id", "charge_id"),
        Index("ix_refunds_status", "status"),
        Index(
            "idx_m8_refunds_requested_by",
            "requested_by",
            sqlite_where=text("requested_by IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    charge_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("charges.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        enum_column("payment_provider", create_constraint=False),
        nullable=False,
        server_default=text("'PAGARME'"),
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    reason_code: Mapped[str | None] = mapped_column(
        enum_column("refund_reason", create_constraint=False)
    )
    status: Mapped[str] = mapped_column(
        enum_column("refund_status", create_constraint=False), nullable=False
    )
    requested_by: Mapped[UUID | None] = mapped_column(
        uuid_pk, ForeignKey("users.id", ondelete="SET NULL")
    )
    processed_at: Mapped[datetime | None] = mapped_column(timestamp)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
