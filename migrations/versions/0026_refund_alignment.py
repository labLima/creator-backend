"""Align refunds to the final modeling (T15, B4d)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0026_refund_alignment"
down_revision = "0025_provider_webhook"
branch_labels = None
depends_on = None

_REASONS = {
    "CUSTOMER_REQUEST",
    "CHARGEBACK",
    "FRAUD_SUSPECT",
    "DUPLICATE",
    "SERVICE_FAILURE",
    "OTHER",
}
_STATUS = {"PENDING", "SUCCEEDED", "FAILED"}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("refunds"):
        return
    columns = {column["name"] for column in inspector.get_columns("refunds")}
    if "charge_id" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, provider_charge_id, provider_refund_id, amount_cents, "
                "currency, reason, status, created_at, updated_at FROM refunds "
                "WHERE deleted_at IS NULL"
            )
        )
    ]
    charge_by_provider = {
        str(row[0]): row[1]
        for row in op.get_bind().execute(
            sa.text(
                "SELECT provider_charge_id, id FROM charges WHERE provider_charge_id IS NOT NULL"
            )
        )
    }
    normalized = []
    for row in rows:
        charge_id = charge_by_provider.get(str(row["provider_charge_id"]))
        if charge_id is None:
            continue
        status = str(row["status"] or "PENDING").upper()
        if status not in _STATUS:
            status = "PENDING"
        reason = str(row["reason"] or "").upper()
        normalized.append(
            {
                "id": row["id"],
                "charge_id": charge_id,
                "external_id": row["provider_refund_id"],
                "amount_cents": row["amount_cents"],
                "currency": str(row["currency"] or "BRL")[:3].upper(),
                "reason_code": reason if reason in _REASONS else None,
                "status": status,
                "processed_at": row["updated_at"] if status != "PENDING" else None,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "refunds_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "charge_id",
            uuid_pk,
            sa.ForeignKey("charges.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("reason_code", enum_column("refund_reason", create_constraint=False)),
        sa.Column("status", enum_column("refund_status", create_constraint=False), nullable=False),
        sa.Column("requested_by", uuid_pk, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("processed_at", timestamp_tz),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_cents >= 0", name="chk_refunds_amount_nonnegative"),
        sa.CheckConstraint(currency_code_check("currency"), name="chk_refunds_currency_format"),
        sa.CheckConstraint(
            "(status = 'PENDING') = (processed_at IS NULL)",
            name="chk_refunds_processed_by_status",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO refunds_old "
                "(id, charge_id, external_id, amount_cents, currency, reason_code, status, "
                "processed_at, created_at, updated_at) "
                "VALUES (:id, :charge_id, :external_id, :amount_cents, :currency, "
                ":reason_code, :status, :processed_at, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("refunds")
    op.rename_table("refunds_old", "refunds")
    op.create_index(
        "uq_refunds_provider_external_id", "refunds", ["provider", "external_id"], unique=True
    )
    op.create_index("ix_refunds_charge_id", "refunds", ["charge_id"])
    op.create_index("ix_refunds_status", "refunds", ["status"])
    op.create_index(
        "idx_m8_refunds_requested_by",
        "refunds",
        ["requested_by"],
        sqlite_where=sa.text("requested_by IS NOT NULL"),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("refunds"):
        return
    columns = {column["name"] for column in inspector.get_columns("refunds")}
    if "provider_refund_id" in columns:
        return
    op.create_table(
        "refunds_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("invoice_id", uuid_pk),
        sa.Column("provider_charge_id", sa.String(64)),
        sa.Column("provider_refund_id", sa.String(64)),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reason", sa.String()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO refunds_legacy "
        "(id, billing_account_id, invoice_id, provider_charge_id, provider_refund_id, "
        "amount_cents, currency, reason, status, created_at, updated_at) "
        "SELECT r.id, c.billing_account_id, c.invoice_id, c.provider_charge_id, "
        "r.external_id, r.amount_cents, r.currency, r.reason_code, lower(r.status), "
        "r.created_at, r.updated_at FROM refunds r "
        "JOIN charges c ON c.id = r.charge_id"
    )
    op.drop_table("refunds")
    op.rename_table("refunds_legacy", "refunds")
