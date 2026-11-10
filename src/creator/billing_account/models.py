"""SQLAlchemy tables owned by the billing_account capability."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.constraints import uf_check, zip_code_check
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_default, uuid_pk

timestamp = timestamp_tz


class BillingAccount(Base):
    __tablename__ = "billing_accounts"
    __table_args__ = (
        CheckConstraint(
            "(payer_type = 'COMPANY') = (company_name IS NOT NULL)",
            name="chk_billing_accounts_company_name",
        ),
        CheckConstraint(
            "(document IS NULL) = (document_hash IS NULL)",
            name="chk_billing_accounts_document_pair",
        ),
        Index("ix_billing_accounts_document_hash", "document_hash"),
        Index("ix_billing_accounts_user_id", "user_id"),
        Index(
            "uq_billing_accounts_provider_external_id",
            "provider",
            "external_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    user_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    payer_type: Mapped[str] = mapped_column(
        enum_column("billing_account_type", create_constraint=False), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    document: Mapped[bytes | None] = mapped_column(LargeBinary)
    document_hash: Mapped[str | None] = mapped_column(String(64))
    company_name: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(
        enum_column("payment_provider", create_constraint=False),
        nullable=False,
        server_default=text("'PAGARME'"),
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    external_code: Mapped[str | None] = mapped_column(String(52))
    delinquent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    metadata_json: Mapped[dict[str, object] | None] = mapped_column("metadata", json_type)
    created_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        timestamp, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BillingAddress(Base):
    __tablename__ = "billing_addresses"
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_billing_addresses_external_id"),
        CheckConstraint(
            f"country <> 'BR' OR {zip_code_check('zip_code')}",
            name="chk_billing_addresses_zip_code",
        ),
        CheckConstraint(
            f"country <> 'BR' OR {uf_check('state')}",
            name="chk_billing_addresses_state_uf",
        ),
        Index("ix_billing_addresses_billing_account_id", "billing_account_id"),
        Index(
            "uq_billing_addresses_default",
            "billing_account_id",
            unique=True,
            sqlite_where=text("is_default AND status = 'ACTIVE'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    billing_account_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("billing_accounts.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    line_1: Mapped[str] = mapped_column(String(256), nullable=False)
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    line_2: Mapped[str | None] = mapped_column(String(128))
    district: Mapped[str | None] = mapped_column(String(64))
    zip_code: Mapped[str] = mapped_column(String(8), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(
        enum_column("address_status", create_constraint=False),
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
