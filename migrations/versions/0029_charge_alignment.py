"""Align charges to the final modeling (T15, B4g)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0029_charge_alignment"
down_revision = "0028_order_alignment"
branch_labels = None
depends_on = None

_STATUS = {
    "PENDING",
    "PAID",
    "CANCELED",
    "PROCESSING",
    "FAILED",
    "OVERPAID",
    "UNDERPAID",
    "CHARGEDBACK",
}


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("charges")
    if not columns or "provider" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, billing_account_id, invoice_id, provider_charge_id, "
                "amount_cents, currency, status, metadata, created_at, updated_at "
                "FROM charges WHERE deleted_at IS NULL"
            )
        )
    ]
    seen: set[str] = set()
    normalized = []
    for row in rows:
        status = str(row["status"] or "PENDING").upper()
        external_id = row["provider_charge_id"]
        if external_id is not None and external_id in seen:
            external_id = None
        elif external_id is not None:
            seen.add(external_id)
        normalized.append(
            {
                **row,
                "external_id": external_id,
                "code": str(external_id)[:52] if external_id else None,
                "status": status if status in _STATUS else "PENDING",
                "currency": str(row["currency"] or "BRL")[:3].upper(),
            }
        )
    op.create_table(
        "charges_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "billing_account_id",
            uuid_pk,
            sa.ForeignKey("billing_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("invoice_id", uuid_pk, sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("order_id", uuid_pk, sa.ForeignKey("orders.id", ondelete="SET NULL")),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column(
            "payment_method",
            enum_column("payment_method_type", create_constraint=False),
            nullable=False,
        ),
        sa.Column(
            "payment_method_id",
            uuid_pk,
            sa.ForeignKey("billing_payment_methods.id", ondelete="SET NULL"),
        ),
        sa.Column("code", sa.String(52)),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("paid_amount_cents", sa.BigInteger()),
        sa.Column("canceled_amount_cents", sa.BigInteger()),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("installments", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("funding_source", enum_column("funding_source", create_constraint=False)),
        sa.Column("status", enum_column("charge_status", create_constraint=False), nullable=False),
        sa.Column("gateway_id", sa.String(128)),
        sa.Column("metadata", json_type),
        sa.Column("provider_payload", json_type),
        sa.Column("due_at", timestamp_tz),
        sa.Column("paid_at", timestamp_tz),
        sa.Column("canceled_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "amount_cents >= 0 AND (paid_amount_cents IS NULL OR paid_amount_cents >= 0) "
            "AND (canceled_amount_cents IS NULL OR canceled_amount_cents >= 0)",
            name="chk_charges_cents_nonnegative",
        ),
        sa.CheckConstraint(
            "installments IS NULL OR installments >= 1", name="chk_charges_installments"
        ),
        sa.CheckConstraint(
            "currency IS NULL OR " + currency_code_check("currency"),
            name="chk_charges_currency_format",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO charges_old "
                "(id, billing_account_id, invoice_id, external_id, payment_method, code, "
                "amount_cents, currency, status, metadata, created_at, updated_at) "
                "VALUES (:id, :billing_account_id, :invoice_id, :external_id, "
                "'CREDIT_CARD', :code, :amount_cents, :currency, :status, :metadata, "
                ":created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("charges")
    op.rename_table("charges_old", "charges")
    op.create_index(
        "uq_charges_provider_external_id", "charges", ["provider", "external_id"], unique=True
    )
    op.create_index(
        "ix_charges_billing_account_status", "charges", ["billing_account_id", "status"]
    )
    op.create_index("ix_charges_code", "charges", ["code"])
    op.create_index("ix_charges_invoice_id", "charges", ["invoice_id"])
    op.create_index("ix_charges_order_id", "charges", ["order_id"])
    op.create_index("ix_charges_paid_at", "charges", ["paid_at"])
    op.create_index("ix_charges_status", "charges", ["status"])
    op.create_index(
        "idx_m8_charges_payment_method_id",
        "charges",
        ["payment_method_id"],
        sqlite_where=sa.text("payment_method_id IS NOT NULL"),
    )


def downgrade() -> None:
    if "provider_charge_id" in _columns("charges"):
        return
    op.create_table(
        "charges_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("invoice_id", uuid_pk),
        sa.Column("provider_charge_id", sa.String(64)),
        sa.Column("provider_card_id", sa.String(64)),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO charges_legacy "
        "(id, billing_account_id, invoice_id, provider_charge_id, amount_cents, currency, "
        "status, metadata, created_at, updated_at) "
        "SELECT id, billing_account_id, invoice_id, external_id, amount_cents, currency, "
        "lower(status), COALESCE(metadata, '{}'), created_at, updated_at FROM charges"
    )
    op.drop_table("charges")
    op.rename_table("charges_legacy", "charges")
