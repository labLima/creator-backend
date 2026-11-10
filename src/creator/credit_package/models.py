"""SQLAlchemy tables owned by the credit_package capability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.types import timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class CreditPackage(Base):
    __tablename__ = "credit_packages"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="chk_credit_packages_price_nonnegative"),
        CheckConstraint(
            "currency IS NULL OR " + currency_code_check("currency"),
            name="chk_credit_packages_currency_format",
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    name: Mapped[str | None] = mapped_column(String)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    credits_validity_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("30")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
