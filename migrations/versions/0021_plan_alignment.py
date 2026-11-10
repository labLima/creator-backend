"""Align plans and plan_items to the final modeling (T15, B2)."""

import json

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0021_plan_alignment"
down_revision = "0020_billing_account_alignment"
branch_labels = None
depends_on = None

_CATALOG = {"ACTIVE", "INACTIVE", "ARCHIVED"}
_PLAN_TYPES = {"FREE", "STARTER", "PRO", "STUDIO", "ENTERPRISE"}


def _columns(table: str) -> dict[str, dict[str, object]]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return {}
    return {column["name"]: column for column in inspector.get_columns(table)}


def _rebuild_plans() -> None:
    columns = _columns("plans")
    if not columns or "credits_per_month" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, code, type, name, description, metadata, is_active, "
                "created_at, updated_at, deleted_at FROM plans"
            )
        )
    ]
    normalized = []
    for row in rows:
        raw_metadata = row["metadata"]
        if isinstance(raw_metadata, str):
            raw_metadata = json.loads(raw_metadata)
        metadata = dict(raw_metadata or {})
        metadata["code"] = row["code"]
        if row["description"] is not None:
            metadata["description"] = row["description"]
        plan_type = str(row["type"] or "FREE").upper()
        normalized.append(
            {
                "id": row["id"],
                "name": str(row["name"])[:64],
                "type": plan_type if plan_type in _PLAN_TYPES else "FREE",
                "metadata": json.dumps(metadata),
                "status": "ACTIVE" if row["is_active"] else "INACTIVE",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "deleted_at": row["deleted_at"],
            }
        )
    op.create_table(
        "plans_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("type", enum_column("plan_type", create_constraint=False), nullable=False),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("price_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("credits_per_month", sa.Integer(), nullable=False),
        sa.Column(
            "credits_validity_days", sa.Integer(), nullable=False, server_default=sa.text("30")
        ),
        sa.Column(
            "billing_interval",
            enum_column("billing_interval", create_constraint=False),
            nullable=False,
            server_default=sa.text("'MONTH'"),
        ),
        sa.Column("interval_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "billing_type",
            enum_column("billing_type", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PREPAID'"),
        ),
        sa.Column("minimum_price_cents", sa.BigInteger()),
        sa.Column("trial_period_days", sa.Integer()),
        sa.Column("statement_descriptor", sa.String(22)),
        sa.Column(
            "status",
            enum_column("catalog_status", create_constraint=False),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
        sa.CheckConstraint(
            "price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0)",
            name="chk_plans_cents_nonnegative",
        ),
        sa.CheckConstraint(currency_code_check("currency"), name="chk_plans_currency_format"),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO plans_old "
                "(id, name, type, provider, external_id, price_cents, currency, "
                "credits_per_month, status, metadata, created_at, updated_at, deleted_at) "
                "VALUES (:id, :name, :type, 'PAGARME', NULL, 0, 'BRL', 0, :status, "
                ":metadata, :created_at, :updated_at, :deleted_at)"
            ),
            normalized,
        )
    op.drop_table("plans")
    op.rename_table("plans_old", "plans")
    op.create_index(
        "uq_plans_provider_external_id", "plans", ["provider", "external_id"], unique=True
    )


def _rebuild_plan_items() -> None:
    columns = _columns("plan_items")
    if not columns or "currency" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, plan_id, gateway_id, provider_plan_item_id, name, description, "
                "quantity, cycles, pricing_scheme_type, price_cents, price_brackets, status, "
                "created_at, updated_at FROM plan_items WHERE deleted_at IS NULL"
            )
        )
    ]
    seen: set[str] = set()
    normalized = []
    for row in rows:
        external_id = row["gateway_id"] or row["provider_plan_item_id"]
        if external_id is not None and external_id in seen:
            external_id = None
        elif external_id is not None:
            seen.add(external_id)
        status = str(row["status"] or "ACTIVE").upper()
        normalized.append(
            {
                "id": row["id"],
                "plan_id": row["plan_id"],
                "external_id": external_id,
                "name": str(row["name"])[:64],
                "description": row["description"],
                "quantity": row["quantity"],
                "cycles": row["cycles"],
                "pricing_scheme_type": row["pricing_scheme_type"],
                "price_cents": row["price_cents"] or 0,
                "price_brackets": (
                    json.dumps(row["price_brackets"])
                    if isinstance(row["price_brackets"], (dict, list))
                    else row["price_brackets"]
                ),
                "status": status if status in _CATALOG else "ACTIVE",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "plan_items_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "plan_id",
            uuid_pk,
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("cycles", sa.Integer()),
        sa.Column(
            "pricing_scheme_type", enum_column("pricing_scheme_type", create_constraint=False)
        ),
        sa.Column("price_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("price_brackets", json_type),
        sa.Column(
            "status",
            enum_column("catalog_status", create_constraint=False),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "price_cents IS NULL OR price_cents >= 0",
            name="chk_plan_items_price_nonnegative",
        ),
        sa.CheckConstraint(currency_code_check("currency"), name="chk_plan_items_currency_format"),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO plan_items_old "
                "(id, plan_id, external_id, name, description, quantity, cycles, "
                "pricing_scheme_type, price_cents, price_brackets, status, created_at, "
                "updated_at) VALUES (:id, :plan_id, :external_id, :name, :description, "
                ":quantity, :cycles, :pricing_scheme_type, :price_cents, :price_brackets, "
                ":status, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("plan_items")
    op.rename_table("plan_items_old", "plan_items")
    op.create_index("idx_m8_plan_items_plan_id", "plan_items", ["plan_id"])
    op.create_index(
        "uq_plan_items_provider_external_id",
        "plan_items",
        ["provider", "external_id"],
        unique=True,
    )


def upgrade() -> None:
    _rebuild_plans()
    _rebuild_plan_items()


def downgrade() -> None:
    _downgrade_plan_items()
    _downgrade_plans()


def _downgrade_plan_items() -> None:
    if "gateway_id" in _columns("plan_items"):
        return
    op.create_table(
        "plan_items_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("plan_id", uuid_pk, nullable=False),
        sa.Column("gateway_id", sa.String(128)),
        sa.Column("provider_plan_item_id", sa.String(64)),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("cycles", sa.Integer()),
        sa.Column("pricing_scheme_type", sa.String(20)),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("price_brackets", json_type),
        sa.Column("status", sa.String(20)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO plan_items_legacy "
        "(id, plan_id, gateway_id, name, description, quantity, cycles, "
        "pricing_scheme_type, price_cents, price_brackets, status, created_at, updated_at) "
        "SELECT id, plan_id, external_id, name, description, quantity, cycles, "
        "pricing_scheme_type, price_cents, price_brackets, lower(status), created_at, "
        "updated_at FROM plan_items"
    )
    op.drop_table("plan_items")
    op.rename_table("plan_items_legacy", "plan_items")


def _downgrade_plans() -> None:
    if "code" in _columns("plans"):
        return
    op.create_table(
        "plans_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO plans_legacy "
        "(id, code, type, name, description, metadata, is_active, created_at, updated_at, "
        "deleted_at) SELECT id, COALESCE(json_extract(metadata, '$.code'), substr(id, 1, 32)), "
        "lower(type), name, json_extract(metadata, '$.description'), "
        "COALESCE(metadata, '{}'), CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END, "
        "created_at, updated_at, deleted_at FROM plans"
    )
    op.drop_table("plans")
    op.rename_table("plans_legacy", "plans")
