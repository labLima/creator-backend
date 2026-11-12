"""Align orders, image_resizes and coupon_redemptions micro-divergences (T27).

Issue #170 closes the remaining structural gaps of the final modeling for three
tables:

- ``orders.discount_cents`` becomes ``NOT NULL DEFAULT 0``; the existing rows are
  backfilled from the amount already recorded, so the ``amount_cents =
  subtotal_cents - discount_cents`` invariant keeps holding.
- ``image_resizes`` adopts the index names declared by the final modeling.
- ``coupon_redemptions`` drops the redundant simple ``workspace_id -> workspaces``
  foreign key and links ``credit_transaction_id`` to the credit ledger. A legacy
  ``credit_transaction_id`` the ledger cannot resolve is untrusted data and is
  neutralised to NULL while the table is rebuilt, matching the ``ON DELETE SET
  NULL`` shape of the new foreign key.

SQLite cannot alter constraints in place, so the two table changes follow the
explicit create/copy/drop/rename pattern already used by the alignment chain.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0034_billing_media_micro"
down_revision = "0033_provider_micro_alignment"
branch_labels = None
depends_on = None


def _columns(table: str) -> dict[str, dict[str, object]]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return {}
    return {column["name"]: dict(column) for column in inspector.get_columns(table)}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {index["name"] for index in inspector.get_indexes(table) if index["name"]}


def upgrade() -> None:
    _upgrade_orders()
    _upgrade_image_resize_indexes()
    _upgrade_coupon_redemptions()


def _upgrade_orders() -> None:
    columns = _columns("orders")
    if not columns or not columns["discount_cents"]["nullable"]:
        return
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
        sa.Column("discount_cents", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
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
    # The discount is the difference already withheld from the subtotal. When the
    # recorded amount exceeds the subtotal (legacy inconsistency) the discount is
    # clamped to zero and the amount is normalised instead, so both branches
    # satisfy `amount_cents = subtotal_cents - discount_cents`.
    op.execute(
        "INSERT INTO orders_old "
        "(id, billing_account_id, workspace_id, credit_package_id, provider, external_id, "
        "code, subtotal_cents, discount_cents, amount_cents, currency, status, metadata, "
        "created_at, updated_at) "
        "SELECT id, billing_account_id, workspace_id, credit_package_id, provider, "
        "external_id, code, subtotal_cents, "
        "CASE WHEN subtotal_cents - amount_cents >= 0 "
        "THEN subtotal_cents - amount_cents ELSE 0 END, "
        "CASE WHEN subtotal_cents - amount_cents >= 0 "
        "THEN amount_cents ELSE subtotal_cents END, "
        "currency, status, metadata, created_at, updated_at FROM orders"
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


def _upgrade_image_resize_indexes() -> None:
    indexes = _indexes("image_resizes")
    if not indexes:
        return
    if "ix_image_resizes_source_image_id" in indexes:
        op.drop_index("ix_image_resizes_source_image_id", table_name="image_resizes")
    if "idx_image_resizes_source_image" not in indexes:
        op.create_index("idx_image_resizes_source_image", "image_resizes", ["source_image_id"])
    if "uq_image_resizes_storage_bucket_storage_key" in indexes:
        op.drop_index("uq_image_resizes_storage_bucket_storage_key", table_name="image_resizes")
    if "uq_image_resizes_storage" not in indexes:
        op.create_index(
            "uq_image_resizes_storage",
            "image_resizes",
            ["storage_bucket", "storage_key"],
            unique=True,
        )


def _coupon_redemptions_table(name: str, *, workspace_foreign_key: bool) -> None:
    workspace_args: list[sa.SchemaItem] = []
    credit_args: list[sa.SchemaItem] = []
    if workspace_foreign_key:
        workspace_args.append(sa.ForeignKey("workspaces.id", ondelete="RESTRICT"))
    else:
        credit_args.append(sa.ForeignKey("workspace_credit_transactions.id", ondelete="SET NULL"))
    op.create_table(
        name,
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "coupon_id",
            uuid_pk,
            sa.ForeignKey("coupons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            uuid_pk,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("workspace_id", uuid_pk, *workspace_args, nullable=False),
        sa.Column("order_id", uuid_pk),
        sa.Column("subscription_id", uuid_pk),
        sa.Column("invoice_id", uuid_pk, sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("credit_transaction_id", uuid_pk, *credit_args),
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
            currency_code_check("currency"), name="chk_coupon_redemptions_currency_format"
        ),
    )


def _copy_coupon_redemptions(source: str, target: str) -> None:
    op.execute(
        f"INSERT INTO {target} "
        "(id, coupon_id, user_id, workspace_id, order_id, subscription_id, invoice_id, "
        "credit_transaction_id, provider, external_id, discount_percent_applied, "
        "discount_amount_cents, currency, credits_applied, status, once_per_workspace, "
        "redeemed_at, canceled_at, created_at, updated_at) "
        "SELECT id, coupon_id, user_id, workspace_id, order_id, subscription_id, invoice_id, "
        "credit_transaction_id, provider, external_id, discount_percent_applied, "
        "discount_amount_cents, currency, credits_applied, status, once_per_workspace, "
        f"redeemed_at, canceled_at, created_at, updated_at FROM {source}"
    )


def _neutralise_dangling_credit_transactions() -> None:
    """Null the ``credit_transaction_id`` values the credit ledger cannot resolve.

    ``migrations/env.py`` disables ``PRAGMA foreign_keys`` for the rebuild, so the new
    foreign key would accept a dangling reference and keep it invisible to SQLite
    forever. The value is untrusted data; neutralising it matches the
    ``ON DELETE SET NULL`` shape of the constraint and keeps the table reference-clean.
    Resolvable references are copied untouched.
    """
    op.execute(
        "UPDATE coupon_redemptions_old SET credit_transaction_id = NULL "
        "WHERE credit_transaction_id IS NOT NULL AND NOT EXISTS ("
        "SELECT 1 FROM workspace_credit_transactions t "
        "WHERE t.id = coupon_redemptions_old.credit_transaction_id)"
    )


def _create_coupon_redemption_indexes() -> None:
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


def _upgrade_coupon_redemptions() -> None:
    foreign_keys = {
        (foreign_key["referred_table"], tuple(foreign_key["constrained_columns"]))
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys("coupon_redemptions")
    }
    if ("workspaces", ("workspace_id",)) not in foreign_keys:
        return
    _coupon_redemptions_table("coupon_redemptions_old", workspace_foreign_key=False)
    _copy_coupon_redemptions("coupon_redemptions", "coupon_redemptions_old")
    _neutralise_dangling_credit_transactions()
    op.drop_table("coupon_redemptions")
    op.rename_table("coupon_redemptions_old", "coupon_redemptions")
    _create_coupon_redemption_indexes()


def downgrade() -> None:
    _downgrade_coupon_redemptions()
    _downgrade_image_resize_indexes()
    _downgrade_orders()


def _downgrade_orders() -> None:
    columns = _columns("orders")
    if not columns or columns["discount_cents"]["nullable"]:
        return
    op.create_table(
        "orders_legacy",
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
    op.execute(
        "INSERT INTO orders_legacy "
        "(id, billing_account_id, workspace_id, credit_package_id, provider, external_id, "
        "code, subtotal_cents, discount_cents, amount_cents, currency, status, metadata, "
        "created_at, updated_at) "
        "SELECT id, billing_account_id, workspace_id, credit_package_id, provider, "
        "external_id, code, subtotal_cents, discount_cents, amount_cents, currency, status, "
        "metadata, created_at, updated_at FROM orders"
    )
    op.drop_table("orders")
    op.rename_table("orders_legacy", "orders")
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


def _downgrade_image_resize_indexes() -> None:
    indexes = _indexes("image_resizes")
    if not indexes:
        return
    if "idx_image_resizes_source_image" in indexes:
        op.drop_index("idx_image_resizes_source_image", table_name="image_resizes")
    if "ix_image_resizes_source_image_id" not in indexes:
        op.create_index("ix_image_resizes_source_image_id", "image_resizes", ["source_image_id"])
    if "uq_image_resizes_storage" in indexes:
        op.drop_index("uq_image_resizes_storage", table_name="image_resizes")
    if "uq_image_resizes_storage_bucket_storage_key" not in indexes:
        op.create_index(
            "uq_image_resizes_storage_bucket_storage_key",
            "image_resizes",
            ["storage_bucket", "storage_key"],
            unique=True,
        )


def _downgrade_coupon_redemptions() -> None:
    foreign_keys = {
        (foreign_key["referred_table"], tuple(foreign_key["constrained_columns"]))
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys("coupon_redemptions")
    }
    if ("workspace_credit_transactions", ("credit_transaction_id",)) not in foreign_keys:
        return
    _coupon_redemptions_table("coupon_redemptions_legacy", workspace_foreign_key=True)
    _copy_coupon_redemptions("coupon_redemptions", "coupon_redemptions_legacy")
    op.drop_table("coupon_redemptions")
    op.rename_table("coupon_redemptions_legacy", "coupon_redemptions")
    _create_coupon_redemption_indexes()
