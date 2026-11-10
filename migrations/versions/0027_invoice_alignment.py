"""Align invoices to the final modeling (T15, B4e)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0027_invoice_alignment"
down_revision = "0026_refund_alignment"
branch_labels = None
depends_on = None

_STATUS = {"PENDING", "PAID", "CANCELED", "SCHEDULED", "FAILED"}
_PAYMENT = {"CREDIT_CARD", "DEBIT_CARD", "BOLETO", "PIX"}


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("invoices")
    if not columns or "external_id" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, billing_account_id, subscription_id, provider_invoice_id, url, "
                "amount_cents, total_discount_cents, total_increment_cents, currency, status, "
                "payment_method, installments, billing_at, seen_at, due_at, period_start, "
                "period_end, canceled_at, metadata, created_at, updated_at FROM invoices "
                "WHERE deleted_at IS NULL AND subscription_id IS NOT NULL"
            )
        )
    ]
    normalized = []
    for row in rows:
        status = str(row["status"] or "PENDING").upper()
        payment = str(row["payment_method"] or "").upper() or None
        normalized.append(
            {
                **row,
                "external_id": row["provider_invoice_id"],
                "status": status if status in _STATUS else "PENDING",
                "payment_method": payment if payment in _PAYMENT else None,
                "currency": str(row["currency"] or "BRL")[:3].upper(),
                "total_discount_cents": row["total_discount_cents"] or 0,
                "total_increment_cents": row["total_increment_cents"] or 0,
            }
        )
    op.create_table(
        "invoices_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "billing_account_id",
            uuid_pk,
            sa.ForeignKey("billing_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            uuid_pk,
            sa.ForeignKey("subscriptions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("url", sa.String()),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("total_discount_cents", sa.BigInteger()),
        sa.Column("total_increment_cents", sa.BigInteger()),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("status", enum_column("invoice_status", create_constraint=False), nullable=False),
        sa.Column("payment_method", enum_column("payment_method_type", create_constraint=False)),
        sa.Column("installments", sa.Integer()),
        sa.Column("billing_at", timestamp_tz),
        sa.Column("seen_at", timestamp_tz),
        sa.Column("due_at", timestamp_tz),
        sa.Column("period_start", timestamp_tz),
        sa.Column("period_end", timestamp_tz),
        sa.Column("canceled_at", timestamp_tz),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "amount_cents >= 0 AND (total_discount_cents IS NULL OR total_discount_cents >= 0) "
            "AND (total_increment_cents IS NULL OR total_increment_cents >= 0)",
            name="chk_invoices_cents_nonnegative",
        ),
        sa.CheckConstraint(
            "installments IS NULL OR installments >= 1", name="chk_invoices_installments"
        ),
        sa.CheckConstraint(
            "currency IS NULL OR " + currency_code_check("currency"),
            name="chk_invoices_currency_format",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO invoices_old "
                "(id, billing_account_id, subscription_id, external_id, url, amount_cents, "
                "total_discount_cents, total_increment_cents, currency, status, "
                "payment_method, installments, billing_at, seen_at, due_at, period_start, "
                "period_end, canceled_at, metadata, created_at, updated_at) "
                "VALUES (:id, :billing_account_id, :subscription_id, :external_id, :url, "
                ":amount_cents, :total_discount_cents, :total_increment_cents, :currency, "
                ":status, :payment_method, :installments, :billing_at, :seen_at, :due_at, "
                ":period_start, :period_end, :canceled_at, :metadata, :created_at, "
                ":updated_at)"
            ),
            normalized,
        )
    op.drop_table("invoices")
    op.rename_table("invoices_old", "invoices")
    op.create_index(
        "uq_invoices_provider_external_id", "invoices", ["provider", "external_id"], unique=True
    )
    op.create_index("ix_invoices_billing_account_id", "invoices", ["billing_account_id"])
    op.create_index("ix_invoices_status_due_at", "invoices", ["status", "due_at"])
    op.create_index("ix_invoices_subscription_id_due_at", "invoices", ["subscription_id", "due_at"])


def downgrade() -> None:
    if "provider_invoice_id" in _columns("invoices"):
        return
    op.create_table(
        "invoices_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("subscription_id", uuid_pk),
        sa.Column("provider_invoice_id", sa.String(64)),
        sa.Column("provider_charge_id", sa.String(64)),
        sa.Column("url", sa.String(2048)),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "total_discount_cents", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "total_increment_cents", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("payment_method", sa.String(20)),
        sa.Column("installments", sa.Integer()),
        sa.Column("billing_at", timestamp_tz),
        sa.Column("seen_at", timestamp_tz),
        sa.Column("due_at", timestamp_tz),
        sa.Column("period_start", timestamp_tz),
        sa.Column("period_end", timestamp_tz),
        sa.Column("canceled_at", timestamp_tz),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO invoices_legacy "
        "(id, billing_account_id, subscription_id, provider_invoice_id, url, amount_cents, "
        "total_discount_cents, total_increment_cents, currency, status, payment_method, "
        "installments, billing_at, seen_at, due_at, period_start, period_end, canceled_at, "
        "metadata, created_at, updated_at) "
        "SELECT id, billing_account_id, subscription_id, external_id, url, amount_cents, "
        "total_discount_cents, total_increment_cents, currency, lower(status), "
        "lower(payment_method), installments, billing_at, seen_at, due_at, period_start, "
        "period_end, canceled_at, metadata, created_at, updated_at FROM invoices"
    )
    op.drop_table("invoices")
    op.rename_table("invoices_legacy", "invoices")
