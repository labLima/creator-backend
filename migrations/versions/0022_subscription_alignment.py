"""Align subscriptions and subscription_history to the final modeling (T15, B3)."""

import json

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0022_subscription_alignment"
down_revision = "0021_plan_alignment"
branch_labels = None
depends_on = None

_STATUS = {"ACTIVE", "TRIALING", "PAST_DUE", "CANCELED", "EXPIRED"}
_PROVIDER_STATUS = {"ACTIVE", "CANCELED", "FUTURE"}
_PAYMENT = {"CREDIT_CARD", "DEBIT_CARD", "BOLETO", "PIX"}
_CHANGE = {"CREATE", "UPGRADE", "DOWNGRADE", "CANCEL", "RENEW"}
_REASONS = {
    "PAYMENT_FAILED",
    "CARD_EXPIRED",
    "CUSTOMER_REQUEST",
    "PLAN_CHANGED",
    "FRAUD_SUSPECT",
    "DUNNING_EXHAUSTED",
    "TRIAL_ENDED",
}


def _columns(table: str) -> dict[str, dict[str, object]]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return {}
    return {column["name"]: column for column in inspector.get_columns(table)}


def _rebuild_subscriptions() -> None:
    columns = _columns("subscriptions")
    if not columns or "contracted_price_cents" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT s.id, s.billing_account_id, s.workspace_id, s.plan_id, s.status, "
                "s.provider_status, s.provider_subscription_id, s.provider_code, "
                "s.payment_method, s.billing_type, s.interval, s.interval_count, "
                "s.installments, s.minimum_price_cents, s.statement_descriptor, "
                "s.trial_period_days, s.current_period_start, s.current_period_end, "
                "s.next_billing_at, s.canceled_at, s.metadata, s.created_at, s.updated_at, "
                "p.price_cents AS plan_price_cents, p.currency AS plan_currency "
                "FROM subscriptions s LEFT JOIN plans p ON p.id = s.plan_id "
                "WHERE s.deleted_at IS NULL"
            )
        )
    ]
    normalized = []
    seen_workspaces: set[object] = set()
    seen_externals: set[str] = set()
    for row in rows:
        raw_metadata = row["metadata"]
        if isinstance(raw_metadata, str):
            raw_metadata = json.loads(raw_metadata)
        status = str(row["status"] or "ACTIVE").upper()
        provider_status = str(row["provider_status"] or "").upper() or None
        payment = str(row["payment_method"] or "").upper() or None
        if status not in _STATUS:
            status = "ACTIVE"
        if status in {"ACTIVE", "TRIALING", "PAST_DUE"}:
            if row["workspace_id"] in seen_workspaces:
                status = "CANCELED"
            else:
                seen_workspaces.add(row["workspace_id"])
        external_id = row["provider_subscription_id"]
        if external_id is not None and external_id in seen_externals:
            external_id = None
        elif external_id is not None:
            seen_externals.add(external_id)
        normalized.append(
            {
                **row,
                "provider_subscription_id": external_id,
                "status": status,
                "provider_status": (
                    provider_status if provider_status in _PROVIDER_STATUS else None
                ),
                "payment_method": payment if payment in _PAYMENT else None,
                "billing_interval": (str(row["interval"] or "").upper() or None),
                "contracted_price_cents": row["plan_price_cents"] or 0,
                "currency": row["plan_currency"] or "BRL",
                "installments": row["installments"] or 1,
                "metadata": (
                    raw_metadata
                    if raw_metadata is None or isinstance(raw_metadata, str)
                    else json.dumps(raw_metadata)
                ),
            }
        )
    op.create_table(
        "subscriptions_old",
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
            "plan_id", uuid_pk, sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("contracted_price_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
        sa.Column(
            "status", enum_column("subscription_status", create_constraint=False), nullable=False
        ),
        sa.Column(
            "provider_status",
            enum_column("provider_subscription_status", create_constraint=False),
        ),
        sa.Column(
            "status_reason", enum_column("subscription_status_reason", create_constraint=False)
        ),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64)),
        sa.Column("external_code", sa.String(52)),
        sa.Column("payment_method", enum_column("payment_method_type", create_constraint=False)),
        sa.Column(
            "payment_method_id",
            uuid_pk,
            sa.ForeignKey("billing_payment_methods.id", ondelete="SET NULL"),
        ),
        sa.Column("billing_type", enum_column("billing_type", create_constraint=False)),
        sa.Column("billing_interval", enum_column("billing_interval", create_constraint=False)),
        sa.Column("interval_count", sa.Integer()),
        sa.Column("installments", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("minimum_price_cents", sa.BigInteger()),
        sa.Column("statement_descriptor", sa.String(22)),
        sa.Column("trial_period_days", sa.Integer()),
        sa.Column("current_cycle_id", sa.String(64)),
        sa.Column("current_period_start", timestamp_tz),
        sa.Column("current_period_end", timestamp_tz),
        sa.Column("next_billing_at", timestamp_tz),
        sa.Column("canceled_at", timestamp_tz),
        sa.Column("metadata", json_type),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "installments IS NULL OR installments >= 1",
            name="chk_subscriptions_installments",
        ),
        sa.CheckConstraint(
            "contracted_price_cents >= 0 AND "
            "(minimum_price_cents IS NULL OR minimum_price_cents >= 0)",
            name="chk_subscriptions_cents_nonnegative",
        ),
        sa.CheckConstraint(
            currency_code_check("currency"), name="chk_subscriptions_currency_format"
        ),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO subscriptions_old "
                "(id, billing_account_id, workspace_id, plan_id, contracted_price_cents, "
                "currency, status, provider_status, provider, external_id, external_code, "
                "payment_method, billing_type, billing_interval, interval_count, "
                "installments, minimum_price_cents, statement_descriptor, "
                "trial_period_days, current_period_start, current_period_end, "
                "next_billing_at, canceled_at, metadata, created_at, updated_at) "
                "VALUES (:id, :billing_account_id, :workspace_id, :plan_id, "
                ":contracted_price_cents, :currency, :status, :provider_status, "
                "'PAGARME', :provider_subscription_id, :provider_code, :payment_method, "
                ":billing_type, :billing_interval, :interval_count, :installments, "
                ":minimum_price_cents, :statement_descriptor, :trial_period_days, "
                ":current_period_start, :current_period_end, :next_billing_at, "
                ":canceled_at, :metadata, :created_at, :updated_at)"
            ),
            normalized,
        )
    op.drop_table("subscriptions")
    op.rename_table("subscriptions_old", "subscriptions")
    op.create_index(
        "uq_subscriptions_id_workspace_id",
        "subscriptions",
        ["id", "workspace_id"],
        unique=True,
    )
    op.create_index(
        "uq_subscriptions_provider_external_id",
        "subscriptions",
        ["provider", "external_id"],
        unique=True,
    )
    op.create_index("ix_subscriptions_billing_account_id", "subscriptions", ["billing_account_id"])
    op.create_index("ix_subscriptions_next_billing_at", "subscriptions", ["next_billing_at"])
    op.create_index("ix_subscriptions_workspace_id", "subscriptions", ["workspace_id"])
    op.create_index(
        "uq_subscriptions_workspace_current",
        "subscriptions",
        ["workspace_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('ACTIVE', 'TRIALING', 'PAST_DUE')"),
    )
    op.create_index("idx_m8_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index(
        "idx_m8_subscriptions_payment_method_id",
        "subscriptions",
        ["payment_method_id"],
        sqlite_where=sa.text("payment_method_id IS NOT NULL"),
    )


def _rebuild_history() -> None:
    columns = _columns("subscription_history")
    if not columns or "old_plan_id" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, subscription_id, change_type, previous_plan_id, plan_id, "
                "previous_status, status, reason, created_at FROM subscription_history "
                "WHERE deleted_at IS NULL"
            )
        )
    ]
    normalized = []
    for row in rows:
        change_type = str(row["change_type"] or "CREATE").upper()
        normalized.append(
            {
                "id": row["id"],
                "subscription_id": row["subscription_id"],
                "change_type": change_type if change_type in _CHANGE else "CREATE",
                "old_plan_id": row["previous_plan_id"],
                "new_plan_id": row["plan_id"],
                "old_status": (
                    str(row["previous_status"]).upper() if row["previous_status"] else None
                ),
                "new_status": str(row["status"]).upper() if row["status"] else None,
                "reason_text": row["reason"],
                "created_at": row["created_at"],
            }
        )
    op.create_table(
        "subscription_history_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "subscription_id",
            uuid_pk,
            sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "change_type",
            enum_column("subscription_change_type", create_constraint=False),
            nullable=False,
        ),
        sa.Column("old_plan_id", uuid_pk, sa.ForeignKey("plans.id", ondelete="SET NULL")),
        sa.Column("new_plan_id", uuid_pk, sa.ForeignKey("plans.id", ondelete="SET NULL")),
        sa.Column("old_status", enum_column("subscription_status", create_constraint=False)),
        sa.Column("new_status", enum_column("subscription_status", create_constraint=False)),
        sa.Column(
            "old_provider_status",
            enum_column("provider_subscription_status", create_constraint=False),
        ),
        sa.Column(
            "new_provider_status",
            enum_column("provider_subscription_status", create_constraint=False),
        ),
        sa.Column("changed_by", uuid_pk, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "reason_code", enum_column("subscription_status_reason", create_constraint=False)
        ),
        sa.Column("reason_text", sa.String(500)),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    if normalized:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO subscription_history_old "
                "(id, subscription_id, change_type, old_plan_id, new_plan_id, old_status, "
                "new_status, reason_text, created_at) "
                "VALUES (:id, :subscription_id, :change_type, :old_plan_id, :new_plan_id, "
                ":old_status, :new_status, :reason_text, :created_at)"
            ),
            normalized,
        )
    op.drop_table("subscription_history")
    op.rename_table("subscription_history_old", "subscription_history")
    op.create_index(
        "ix_subscription_history_subscription_created",
        "subscription_history",
        ["subscription_id", "created_at"],
    )
    op.create_index(
        "idx_m8_subscription_history_old_plan_id",
        "subscription_history",
        ["old_plan_id"],
        sqlite_where=sa.text("old_plan_id IS NOT NULL"),
    )
    op.create_index(
        "idx_m8_subscription_history_new_plan_id",
        "subscription_history",
        ["new_plan_id"],
        sqlite_where=sa.text("new_plan_id IS NOT NULL"),
    )
    op.create_index(
        "idx_m8_subscription_history_changed_by",
        "subscription_history",
        ["changed_by"],
        sqlite_where=sa.text("changed_by IS NOT NULL"),
    )


def upgrade() -> None:
    _rebuild_subscriptions()
    _rebuild_history()


def downgrade() -> None:
    _downgrade_history()
    _downgrade_subscriptions()


def _downgrade_history() -> None:
    if "previous_plan_id" in _columns("subscription_history"):
        return
    op.create_table(
        "subscription_history_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("subscription_id", uuid_pk, nullable=False),
        sa.Column("change_type", sa.String(20), nullable=False),
        sa.Column("previous_plan_id", uuid_pk),
        sa.Column("plan_id", uuid_pk),
        sa.Column("previous_status", sa.String(20)),
        sa.Column("status", sa.String(20)),
        sa.Column("reason", sa.String()),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO subscription_history_legacy "
        "(id, subscription_id, change_type, previous_plan_id, plan_id, previous_status, "
        "status, reason, created_at, updated_at) "
        "SELECT id, subscription_id, lower(change_type), old_plan_id, new_plan_id, "
        "lower(old_status), lower(new_status), COALESCE(reason_text, reason_code), "
        "created_at, created_at FROM subscription_history"
    )
    op.drop_table("subscription_history")
    op.rename_table("subscription_history_legacy", "subscription_history")


def _downgrade_subscriptions() -> None:
    if "billing_day" in _columns("subscriptions"):
        return
    op.create_table(
        "subscriptions_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("billing_account_id", uuid_pk, nullable=False),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("plan_id", uuid_pk, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider_status", sa.String(20)),
        sa.Column("provider_subscription_id", sa.String(64)),
        sa.Column("provider_code", sa.String(52)),
        sa.Column("payment_method", sa.String(20)),
        sa.Column("provider_card_id", sa.String(64)),
        sa.Column("billing_type", sa.String(20)),
        sa.Column("billing_day", sa.Integer()),
        sa.Column("interval", sa.String(10)),
        sa.Column("interval_count", sa.Integer()),
        sa.Column("installments", sa.Integer()),
        sa.Column("minimum_price_cents", sa.BigInteger()),
        sa.Column("statement_descriptor", sa.String(22)),
        sa.Column("trial_period_days", sa.Integer()),
        sa.Column("current_period_start", timestamp_tz),
        sa.Column("current_period_end", timestamp_tz),
        sa.Column("next_billing_at", timestamp_tz),
        sa.Column("start_at", timestamp_tz),
        sa.Column("canceled_at", timestamp_tz),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO subscriptions_legacy "
        "(id, billing_account_id, workspace_id, plan_id, status, provider_status, "
        "provider_subscription_id, provider_code, payment_method, provider_card_id, "
        "billing_type, interval, interval_count, installments, minimum_price_cents, "
        "statement_descriptor, trial_period_days, current_period_start, "
        "current_period_end, next_billing_at, start_at, canceled_at, metadata, "
        "created_at, updated_at) "
        "SELECT id, billing_account_id, workspace_id, plan_id, lower(status), "
        "lower(provider_status), external_id, external_code, lower(payment_method), NULL, "
        "lower(billing_type), lower(billing_interval), interval_count, installments, "
        "minimum_price_cents, statement_descriptor, trial_period_days, "
        "current_period_start, current_period_end, next_billing_at, current_period_start, "
        "canceled_at, COALESCE(metadata, '{}'), created_at, updated_at FROM subscriptions"
    )
    op.drop_table("subscriptions")
    op.rename_table("subscriptions_legacy", "subscriptions")
