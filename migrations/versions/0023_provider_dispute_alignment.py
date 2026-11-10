"""Align provider disputes to the final modeling (T15, B4a)."""

import json

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0023_provider_dispute_alignment"
down_revision = "0022_subscription_alignment"
branch_labels = None
depends_on = None

_STATUS = {"OPEN", "UNDER_REVIEW", "RESOLVED"}


def _rebuild_disputes() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("provider_disputes"):
        return
    columns = {column["name"] for column in inspector.get_columns("provider_disputes")}
    if "external_id" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, billing_account_id, charge_id, provider_dispute_id, code, "
                "reason, status, opened_at, deadline_at, payload, created_at, updated_at "
                "FROM provider_disputes WHERE deleted_at IS NULL"
            )
        )
    ]
    seen: set[str] = set()
    normalized = []
    for row in rows:
        external_id = row["provider_dispute_id"] or row["code"]
        if external_id is not None and external_id in seen:
            external_id = None
        elif external_id is not None:
            seen.add(external_id)
        status = str(row["status"] or "OPEN").upper()
        if status not in _STATUS:
            status = "OPEN"
        payload = row["payload"]
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        normalized.append(
            {
                "id": row["id"],
                "billing_account_id": row["billing_account_id"],
                "charge_id": row["charge_id"],
                "external_id": external_id,
                "status": status,
                "result": "WON" if status == "RESOLVED" else None,
                "resolved_at": row["updated_at"] if status == "RESOLVED" else None,
                "reason": row["reason"],
                "opened_at": row["opened_at"],
                "deadline_at": row["deadline_at"],
                "payload": payload,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    op.create_table(
        "provider_disputes_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "billing_account_id",
            uuid_pk,
            sa.ForeignKey("billing_accounts.id", ondelete="RESTRICT"),
        ),
        sa.Column("charge_id", uuid_pk, sa.ForeignKey("charges.id", ondelete="RESTRICT")),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column(
            "status",
            enum_column("dispute_status", create_constraint=False),
            nullable=False,
            server_default=sa.text("'OPEN'"),
        ),
        sa.Column("result", enum_column("dispute_result", create_constraint=False)),
        sa.Column("amount_cents", sa.BigInteger()),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column("reason", sa.String()),
        sa.Column("opened_at", timestamp_tz),
        sa.Column("deadline_at", timestamp_tz),
        sa.Column("resolved_at", timestamp_tz),
        sa.Column("payload", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "amount_cents IS NULL OR amount_cents >= 0",
            name="chk_provider_disputes_amount_nonnegative",
        ),
        sa.CheckConstraint(
            currency_code_check("currency"),
            name="chk_provider_disputes_currency_format",
        ),
        sa.CheckConstraint(
            "(status = 'RESOLVED') = (result IS NOT NULL)",
            name="chk_provider_disputes_result",
        ),
        sa.CheckConstraint(
            "(status = 'RESOLVED') = (resolved_at IS NOT NULL)",
            name="chk_provider_disputes_resolved_at",
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO provider_disputes_old "
                "(id, billing_account_id, charge_id, external_id, status, result, "
                "resolved_at, reason, opened_at, deadline_at, payload, created_at, "
                "updated_at) VALUES (:id, :billing_account_id, :charge_id, :external_id, "
                ":status, :result, :resolved_at, :reason, :opened_at, :deadline_at, "
                ":payload, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("provider_disputes")
    op.rename_table("provider_disputes_old", "provider_disputes")
    op.create_index(
        "uq_provider_disputes_provider_external_id",
        "provider_disputes",
        ["provider", "external_id"],
        unique=True,
    )
    op.create_index("ix_provider_disputes_charge_id", "provider_disputes", ["charge_id"])
    op.create_index(
        "ix_provider_disputes_status_resolved_at",
        "provider_disputes",
        ["status", "resolved_at"],
    )
    op.create_index(
        "idx_m8_provider_disputes_billing_account_id",
        "provider_disputes",
        ["billing_account_id"],
        sqlite_where=sa.text("billing_account_id IS NOT NULL"),
    )


def upgrade() -> None:
    _rebuild_disputes()


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("provider_disputes"):
        return
    columns = {column["name"] for column in inspector.get_columns("provider_disputes")}
    if "provider_dispute_id" in columns:
        return
    op.create_table(
        "provider_disputes_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("charge_id", uuid_pk),
        sa.Column("provider_dispute_id", sa.String(64)),
        sa.Column("code", sa.String(52)),
        sa.Column("reason", sa.String()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("opened_at", timestamp_tz),
        sa.Column("deadline_at", timestamp_tz),
        sa.Column("payload", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO provider_disputes_legacy "
        "(id, billing_account_id, charge_id, provider_dispute_id, reason, status, "
        "opened_at, deadline_at, payload, created_at, updated_at) "
        "SELECT id, COALESCE(billing_account_id, id), charge_id, external_id, reason, "
        "lower(status), opened_at, deadline_at, COALESCE(payload, '{}'), created_at, "
        "updated_at FROM provider_disputes"
    )
    op.drop_table("provider_disputes")
    op.rename_table("provider_disputes_legacy", "provider_disputes")
