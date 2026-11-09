"""SQLAlchemy tables owned by the fiscal invoice capability.

The dump declares the currency CHECK with a lowercase pattern
(``^[a-z]{3}$``) while defaulting ``currency`` to ``'BRL'``; that pair is
unsatisfiable. The portable helper enforces uppercase, matching the default and
every other currency constraint in the modeling.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.constraints import currency_code_check, exactly_one_of
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.types import (
    enum_column,
    timestamp_tz,
    uuid_default,
    uuid_pk,
)

timestamp = timestamp_tz


class FiscalInvoice(Base):
    __tablename__ = "fiscal_invoices"
    __table_args__ = (
        Index("uq_fiscal_invoices_access_key", "access_key", unique=True),
        Index(
            "uq_fiscal_invoices_number_series_account",
            "billing_account_id",
            "series",
            "number",
            unique=True,
        ),
        Index("ix_fiscal_invoices_billing_account_id", "billing_account_id"),
        Index("ix_fiscal_invoices_status", "status"),
        Index("ix_fiscal_invoices_order_id", "order_id"),
        Index("ix_fiscal_invoices_invoice_id", "invoice_id"),
        Index("ix_fiscal_invoices_subscription_id", "subscription_id"),
        CheckConstraint(
            exactly_one_of("order_id", "invoice_id", "subscription_id"),
            name="chk_fiscal_invoices_one_origin",
        ),
        CheckConstraint("amount_cents >= 0", name="chk_fiscal_invoices_amount_nonnegative"),
        CheckConstraint(
            currency_code_check("currency"), name="chk_fiscal_invoices_currency_format"
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    billing_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("billing_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=True
    )
    invoice_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=True
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=True
    )
    number: Mapped[str | None] = mapped_column(String(30))
    series: Mapped[str | None] = mapped_column(String(10))
    access_key: Mapped[str | None] = mapped_column(String(50))
    service_code: Mapped[str | None] = mapped_column(String(20))
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'BRL'"))
    status: Mapped[str] = mapped_column(
        enum_column("fiscal_invoice_status"),
        nullable=False,
        server_default=text("'PENDING'"),
    )
    pdf_storage_bucket: Mapped[str | None] = mapped_column(String(63))
    pdf_storage_key: Mapped[str | None] = mapped_column(String(1024))
    xml_storage_bucket: Mapped[str | None] = mapped_column(String(63))
    xml_storage_key: Mapped[str | None] = mapped_column(String(1024))
    error_message: Mapped[str | None] = mapped_column(String)
    issued_at: Mapped[datetime | None] = mapped_column(timestamp)
    canceled_at: Mapped[datetime | None] = mapped_column(timestamp)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )
