"""Align coupon_redemptions to the final modeling (T15, B5c)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0032_coupon_redemption"
down_revision = "0031_coupon_alignment"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("coupon_redemptions")
    if not columns or "workspace_id" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, coupon_id, billing_account_id, order_id, subscription_id, "
                "provider_discount_id, discount_percent_applied, discount_amount_cents, "
                "credits_applied, status, created_at, updated_at FROM coupon_redemptions "
                "WHERE deleted_at IS NULL"
            )
        )
    ]
    accounts = {
        row[0]: row[1]
        for row in op.get_bind().execute(sa.text("SELECT id, user_id FROM billing_accounts"))
    }
    orders = {
        row[0]: (row[1], row[2])
        for row in op.get_bind().execute(
            sa.text("SELECT id, workspace_id, billing_account_id FROM orders")
        )
    }
    subscriptions = {
        row[0]: (row[1], row[2])
        for row in op.get_bind().execute(
            sa.text("SELECT id, workspace_id, billing_account_id FROM subscriptions")
        )
    }
    seen: set[str] = set()
    normalized = []
    for row in rows:
        order_id = row["order_id"]
        subscription_id = row["subscription_id"]
        if order_id is not None and subscription_id is not None:
            subscription_id = None
        if order_id is None and subscription_id is None:
            continue
        if order_id is not None and order_id in orders:
            workspace_id, billing_account_id = orders[order_id]
        elif subscription_id is not None and subscription_id in subscriptions:
            workspace_id, billing_account_id = subscriptions[subscription_id]
        else:
            continue
        user_id = accounts.get(billing_account_id or row["billing_account_id"])
        if user_id is None:
            continue
        external_id = row["provider_discount_id"]
        if external_id is not None and external_id in seen:
            external_id = None
        elif external_id is not None:
            seen.add(external_id)
        status = str(row["status"] or "APPLIED").upper()
        normalized.append(
            {
                **row,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "order_id": order_id,
                "subscription_id": subscription_id,
                "external_id": external_id,
                "status": status if status in {"APPLIED", "CANCELED"} else "APPLIED",
                "redeemed_at": row["created_at"],
            }
        )
    op.create_table(
        "coupon_redemptions_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "coupon_id", uuid_pk, sa.ForeignKey("coupons.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "user_id", uuid_pk, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("order_id", uuid_pk),
        sa.Column("subscription_id", uuid_pk),
        sa.Column("invoice_id", uuid_pk, sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("credit_transaction_id", uuid_pk),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("discount_percent_applied", sa.Numeric(5, 2)),
        sa.Column("discount_amount_cents", sa.BigInteger()),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("credits_applied", sa.Integer()),
        sa.Column(
            "status",
            enum_column("coupon_redemption_status", create_constraint=False),
            nullable=False,
            server_default=sa.text("'APPLIED'"),
        ),
        sa.Column(
            "once_per_workspace", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("redeemed_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("canceled_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["order_id", "workspace_id"],
            ["orders.id", "orders.workspace_id"],
            name="fk_coupon_redemptions_order",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id", "workspace_id"],
            ["subscriptions.id", "subscriptions.workspace_id"],
            name="fk_coupon_redemptions_subscription",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "(order_id IS NULL) <> (subscription_id IS NULL)",
            name="chk_coupon_redemptions_single_target",
        ),
        sa.CheckConstraint(
            "discount_percent_applied IS NULL OR "
            "(discount_percent_applied > 0 AND discount_percent_applied <= 100)",
            name="chk_coupon_redemptions_discount_percent",
        ),
        sa.CheckConstraint(
            "discount_amount_cents IS NULL OR discount_amount_cents >= 0",
            name="chk_coupon_redemptions_amount_nonnegative",
        ),
        sa.CheckConstraint(
            currency_code_check("currency"),
            name="chk_coupon_redemptions_currency_format",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO coupon_redemptions_old "
                "(id, coupon_id, user_id, workspace_id, order_id, subscription_id, "
                "external_id, discount_percent_applied, discount_amount_cents, "
                "credits_applied, status, redeemed_at, created_at, updated_at) "
                "VALUES (:id, :coupon_id, :user_id, :workspace_id, :order_id, "
                ":subscription_id, :external_id, :discount_percent_applied, "
                ":discount_amount_cents, :credits_applied, :status, :redeemed_at, "
                ":created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("coupon_redemptions")
    op.rename_table("coupon_redemptions_old", "coupon_redemptions")
    op.create_index(
        "ix_coupon_redemptions_coupon_workspace",
        "coupon_redemptions",
        ["coupon_id", "workspace_id"],
    )
    op.create_index("ix_coupon_redemptions_user_id", "coupon_redemptions", ["user_id"])
    op.create_index("ix_coupon_redemptions_workspace_id", "coupon_redemptions", ["workspace_id"])
    op.create_index(
        "ix_coupon_redemptions_order_workspace",
        "coupon_redemptions",
        ["order_id", "workspace_id"],
    )
    op.create_index(
        "ix_coupon_redemptions_subscription_workspace",
        "coupon_redemptions",
        ["subscription_id", "workspace_id"],
    )
    op.create_index(
        "uq_coupon_redemptions_provider_external_id",
        "coupon_redemptions",
        ["provider", "external_id"],
        unique=True,
    )
    op.create_index(
        "uq_coupon_redemptions_once_per_workspace",
        "coupon_redemptions",
        ["coupon_id", "workspace_id"],
        unique=True,
        sqlite_where=sa.text("once_per_workspace AND status = 'APPLIED'"),
    )
    op.create_index(
        "idx_m8_coupon_redemptions_invoice_id",
        "coupon_redemptions",
        ["invoice_id"],
        sqlite_where=sa.text("invoice_id IS NOT NULL"),
    )
    op.create_index(
        "idx_m8_coupon_redemptions_credit_transaction_id",
        "coupon_redemptions",
        ["credit_transaction_id"],
        sqlite_where=sa.text("credit_transaction_id IS NOT NULL"),
    )


def downgrade() -> None:
    if "billing_account_id" in _columns("coupon_redemptions"):
        return
    op.create_table(
        "coupon_redemptions_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("coupon_id", uuid_pk, nullable=False),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("order_id", uuid_pk),
        sa.Column("subscription_id", uuid_pk),
        sa.Column("provider_discount_id", sa.String(64)),
        sa.Column("discount_percent_applied", sa.Numeric(5, 2)),
        sa.Column("discount_amount_cents", sa.Integer()),
        sa.Column("credits_applied", sa.Integer()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO coupon_redemptions_legacy "
        "(id, coupon_id, billing_account_id, order_id, subscription_id, "
        "provider_discount_id, discount_percent_applied, discount_amount_cents, "
        "credits_applied, status, created_at, updated_at) "
        "SELECT r.id, r.coupon_id, COALESCE(o.billing_account_id, s.billing_account_id, r.id), "
        "r.order_id, r.subscription_id, r.external_id, r.discount_percent_applied, "
        "r.discount_amount_cents, r.credits_applied, lower(r.status), r.created_at, "
        "r.updated_at FROM coupon_redemptions r "
        "LEFT JOIN orders o ON o.id = r.order_id "
        "LEFT JOIN subscriptions s ON s.id = r.subscription_id"
    )
    op.drop_table("coupon_redemptions")
    op.rename_table("coupon_redemptions_legacy", "coupon_redemptions")
