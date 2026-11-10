"""Align coupons to the final modeling (T15, B5b)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0031_coupon_alignment"
down_revision = "0030_credit_package"
branch_labels = None
depends_on = None

_TYPES = {"DISCOUNT", "CREDIT"}
_APPLIES = {"SUBSCRIPTION_AND_CREDITS", "SUBSCRIPTION_ONLY", "CREDITS_ONLY"}


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("coupons")
    if not columns or "credits_validity_days" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, code, type, discount_percent, credits_amount, applies_to, "
                "min_purchase_cents, max_redemptions, once_per_workspace, expires_at, "
                "is_active, internal_note, created_by, created_at, updated_at, deleted_at "
                "FROM coupons"
            )
        )
    ]
    for row in rows:
        coupon_type = str(row["type"] or "DISCOUNT").upper()
        applies = str(row["applies_to"] or "SUBSCRIPTION_AND_CREDITS").upper()
        row["type"] = coupon_type if coupon_type in _TYPES else "DISCOUNT"
        row["applies_to"] = applies if applies in _APPLIES else "SUBSCRIPTION_AND_CREDITS"
        row["code"] = str(row["code"] or "")[:32].upper()
        if row["type"] == "DISCOUNT":
            row["credits_amount"] = None
        elif row["discount_percent"] is not None:
            row["discount_percent"] = None
    op.create_table(
        "coupons_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("type", enum_column("coupon_type", create_constraint=False), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2)),
        sa.Column("credits", sa.Integer()),
        sa.Column(
            "credits_validity_days", sa.Integer(), nullable=False, server_default=sa.text("30")
        ),
        sa.Column(
            "applies_to",
            enum_column("coupon_applies_to", create_constraint=False),
            nullable=False,
            server_default=sa.text("'SUBSCRIPTION_AND_CREDITS'"),
        ),
        sa.Column("min_purchase_cents", sa.BigInteger()),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("max_redemptions", sa.Integer()),
        sa.Column(
            "once_per_workspace", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("expires_at", timestamp_tz),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("internal_note", sa.String(255)),
        sa.Column("created_by", uuid_pk, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.CheckConstraint(
            "(type = 'DISCOUNT' AND discount_percent IS NOT NULL AND credits IS NULL) "
            "OR (type = 'CREDIT' AND credits IS NOT NULL AND discount_percent IS NULL)",
            name="chk_coupons_type_exclusive_fields",
        ),
        sa.CheckConstraint(
            "discount_percent IS NULL OR (discount_percent > 0 AND discount_percent <= 100)",
            name="chk_coupons_discount_percent",
        ),
        sa.CheckConstraint(
            "min_purchase_cents IS NULL OR min_purchase_cents >= 0",
            name="chk_coupons_min_purchase_nonnegative",
        ),
        sa.CheckConstraint(currency_code_check("currency"), name="chk_coupons_currency_format"),
        sa.CheckConstraint("code = upper(code)", name="chk_coupons_code_upper"),
    )
    if rows:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO coupons_old "
                "(id, code, type, discount_percent, credits, applies_to, min_purchase_cents, "
                "max_redemptions, once_per_workspace, expires_at, is_active, internal_note, "
                "created_by, created_at, updated_at, deleted_at) "
                "VALUES (:id, :code, :type, :discount_percent, :credits_amount, :applies_to, "
                ":min_purchase_cents, :max_redemptions, :once_per_workspace, :expires_at, "
                ":is_active, :internal_note, :created_by, :created_at, :updated_at, "
                ":deleted_at)"
            ),
            rows,
        )
    op.drop_table("coupons")
    op.rename_table("coupons_old", "coupons")
    op.create_index("ix_coupons_type", "coupons", ["type"])
    op.create_index("ix_coupons_is_active", "coupons", ["is_active"])
    op.create_index(
        "idx_m8_coupons_created_by",
        "coupons",
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )
    op.create_index(
        "uq_coupons_code_active",
        "coupons",
        ["code"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    if "credits_amount" in _columns("coupons"):
        return
    op.create_table(
        "coupons_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2)),
        sa.Column("credits_amount", sa.Integer()),
        sa.Column("applies_to", sa.String(30), nullable=False),
        sa.Column("min_purchase_cents", sa.Integer()),
        sa.Column("max_redemptions", sa.Integer()),
        sa.Column(
            "once_per_workspace", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("redemptions_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("expires_at", timestamp_tz),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("internal_note", sa.String(255)),
        sa.Column("created_by", uuid_pk),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO coupons_legacy "
        "(id, code, type, discount_percent, credits_amount, applies_to, min_purchase_cents, "
        "max_redemptions, once_per_workspace, expires_at, is_active, internal_note, created_by, "
        "created_at, updated_at, deleted_at) "
        "SELECT id, code, lower(type), discount_percent, credits, applies_to, "
        "min_purchase_cents, max_redemptions, once_per_workspace, expires_at, is_active, "
        "internal_note, created_by, created_at, updated_at, deleted_at FROM coupons"
    )
    op.drop_table("coupons")
    op.rename_table("coupons_legacy", "coupons")
