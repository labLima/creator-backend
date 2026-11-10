"""Align credit_packages to the final modeling (T15, B5)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0030_credit_package"
down_revision = "0029_charge_alignment"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("credit_packages")
    if not columns or "credits" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, name, credits_amount, price_cents, currency, is_active, "
                "created_at, updated_at FROM credit_packages WHERE deleted_at IS NULL"
            )
        )
    ]
    op.create_table(
        "credit_packages_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("name", sa.String()),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.BigInteger(), nullable=False),
        sa.Column(
            "credits_validity_days", sa.Integer(), nullable=False, server_default=sa.text("30")
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("price_cents >= 0", name="chk_credit_packages_price_nonnegative"),
        sa.CheckConstraint(
            "currency IS NULL OR " + currency_code_check("currency"),
            name="chk_credit_packages_currency_format",
        ),
    )
    if rows:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO credit_packages_old "
                "(id, name, credits, price_cents, currency, is_active, created_at, updated_at) "
                "VALUES (:id, :name, :credits_amount, :price_cents, :currency, :is_active, "
                ":created_at, :updated_at)"
            ),
            rows,
        )
    op.drop_table("credit_packages")
    op.rename_table("credit_packages_old", "credit_packages")


def downgrade() -> None:
    if "credits_amount" in _columns("credit_packages"):
        return
    op.create_table(
        "credit_packages_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("credits_amount", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO credit_packages_legacy "
        "(id, code, name, credits_amount, price_cents, currency, is_active, created_at, "
        "updated_at) SELECT id, substr(COALESCE(name, id), 1, 32), COALESCE(name, ''), "
        "credits, price_cents, currency, is_active, created_at, updated_at "
        "FROM credit_packages"
    )
    op.drop_table("credit_packages")
    op.rename_table("credit_packages_legacy", "credit_packages")
