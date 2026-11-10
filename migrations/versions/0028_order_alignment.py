"""Align orders to the final modeling (T15, B4f)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0028_order_alignment"
down_revision = "0027_invoice_alignment"
branch_labels = None
depends_on = None

_STATUS = {"PENDING", "PAID", "CANCELED", "FAILED"}


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("orders")
    if not columns or "provider" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, billing_account_id, workspace_id, credit_package_id, "
                "provider_order_id, subtotal_cents, discount_cents, amount_cents, currency, "
                "status, metadata, created_at, updated_at FROM orders "
                "WHERE deleted_at IS NULL"
            )
        )
    ]
    for row in rows:
        status = str(row["status"] or "PENDING").upper()
        row["status"] = status if status in _STATUS else "PENDING"
        discount = row["discount_cents"] or 0
        row["discount_cents"] = discount
        row["amount_cents"] = (row["subtotal_cents"] or 0) - discount
        row["external_id"] = row["provider_order_id"]
        row["code"] = str(row["provider_order_id"])[:52] if row["provider_order_id"] else None
    op.create_table(
        "orders_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "billing_account_id",
            uuid_pk,
            sa.ForeignKey("billing_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "credit_package_id",
            uuid_pk,
            sa.ForeignKey("credit_packages.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("code", sa.String(52)),
        sa.Column("subtotal_cents", sa.BigInteger(), nullable=False),
        sa.Column("discount_cents", sa.BigInteger()),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("status", enum_column("order_status", create_constraint=False), nullable=False),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "amount_cents = subtotal_cents - discount_cents",
            name="chk_orders_amount_consistency",
        ),
        sa.CheckConstraint(
            "subtotal_cents >= 0 AND amount_cents >= 0 AND "
            "(discount_cents IS NULL OR discount_cents >= 0)",
            name="chk_orders_cents_nonnegative",
        ),
        sa.CheckConstraint(
            "currency IS NULL OR " + currency_code_check("currency"),
            name="chk_orders_currency_format",
        ),
    )
    if rows:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO orders_old "
                "(id, billing_account_id, workspace_id, credit_package_id, external_id, "
                "code, subtotal_cents, discount_cents, amount_cents, currency, status, "
                "metadata, created_at, updated_at) "
                "VALUES (:id, :billing_account_id, :workspace_id, :credit_package_id, "
                ":external_id, :code, :subtotal_cents, :discount_cents, :amount_cents, "
                ":currency, :status, :metadata, :created_at, :updated_at)"
            ),
            rows,
        )
    op.drop_table("orders")
    op.rename_table("orders_old", "orders")
    op.create_index("uq_orders_id_workspace_id", "orders", ["id", "workspace_id"], unique=True)
    op.create_index(
        "uq_orders_provider_external_id", "orders", ["provider", "external_id"], unique=True
    )
    op.create_index("ix_orders_billing_account_id", "orders", ["billing_account_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_workspace_id", "orders", ["workspace_id"])
    op.create_index(
        "idx_m8_orders_credit_package_id",
        "orders",
        ["credit_package_id"],
        sqlite_where=sa.text("credit_package_id IS NOT NULL"),
    )


def downgrade() -> None:
    if "provider_order_id" in _columns("orders"):
        return
    op.create_table(
        "orders_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("credit_package_id", uuid_pk),
        sa.Column("provider_order_id", sa.String(64)),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column("discount_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO orders_legacy "
        "(id, billing_account_id, workspace_id, credit_package_id, provider_order_id, "
        "subtotal_cents, discount_cents, amount_cents, currency, status, metadata, "
        "created_at, updated_at) "
        "SELECT id, billing_account_id, workspace_id, credit_package_id, external_id, "
        "subtotal_cents, discount_cents, amount_cents, currency, lower(status), "
        "COALESCE(metadata, '{}'), created_at, updated_at FROM orders"
    )
    op.drop_table("orders")
    op.rename_table("orders_legacy", "orders")
