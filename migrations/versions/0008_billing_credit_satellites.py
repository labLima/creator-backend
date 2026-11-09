"""Create the billing and credit satellite tables (ADR-028, slice T7).

``workspace_credit_lots`` and ``workspace_credit_lot_consumptions`` use composite
foreign keys that include ``workspace_id``; the parent unique keys are
``uq_credit_tx_id_workspace`` (added to the existing transactions table) and
``uq_credit_lots_id_workspace`` (created here).
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import currency_code_check, exactly_one_of
from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0008_billing_credit_satellites"
down_revision = "0007_brand_campaign_satellites"
branch_labels = None
depends_on = None


def _missing(table: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("workspace_credit_transactions")
    }
    if "uq_credit_tx_id_workspace" not in existing_indexes:
        op.create_index(
            "uq_credit_tx_id_workspace",
            "workspace_credit_transactions",
            ["id", "workspace_id"],
            unique=True,
        )

    if _missing("plan_payment_methods"):
        op.create_table(
            "plan_payment_methods",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "plan_id",
                uuid_pk,
                sa.ForeignKey("plans.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("method", enum_column("payment_method_type"), nullable=False),
            sa.Column("max_installments", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "max_installments >= 1",
                name="chk_plan_payment_methods_max_installments",
            ),
        )
        op.create_index(
            "uq_plan_payment_methods_plan_id_method",
            "plan_payment_methods",
            ["plan_id", "method"],
            unique=True,
        )

    if _missing("charge_transactions"):
        op.create_table(
            "charge_transactions",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "charge_id",
                uuid_pk,
                sa.ForeignKey("charges.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "provider",
                enum_column("payment_provider"),
                nullable=False,
                server_default=sa.text("'PAGARME'"),
            ),
            sa.Column("external_id", sa.String(64)),
            sa.Column("status", enum_column("transaction_status"), nullable=False),
            sa.Column("amount_cents", sa.BigInteger, nullable=False),
            sa.Column("gateway_response", json_type),
            sa.Column("antifraud_response", json_type),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "amount_cents >= 0", name="chk_charge_transactions_amount_nonnegative"
            ),
        )
        op.create_index(
            "uq_charge_transactions_charge_provider_external",
            "charge_transactions",
            ["charge_id", "provider", "external_id"],
            unique=True,
        )
        op.create_index("ix_charge_transactions_status", "charge_transactions", ["status"])
        op.create_index("ix_charge_transactions_created_at", "charge_transactions", ["created_at"])
        op.create_index(
            "idx_charge_transactions_latest",
            "charge_transactions",
            ["charge_id", "created_at", "id"],
        )

    if _missing("fiscal_invoices"):
        op.create_table(
            "fiscal_invoices",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "billing_account_id",
                uuid_pk,
                sa.ForeignKey("billing_accounts.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("order_id", uuid_pk, sa.ForeignKey("orders.id", ondelete="RESTRICT")),
            sa.Column("invoice_id", uuid_pk, sa.ForeignKey("invoices.id", ondelete="RESTRICT")),
            sa.Column(
                "subscription_id",
                uuid_pk,
                sa.ForeignKey("subscriptions.id", ondelete="RESTRICT"),
            ),
            sa.Column("number", sa.String(30)),
            sa.Column("series", sa.String(10)),
            sa.Column("access_key", sa.String(50)),
            sa.Column("service_code", sa.String(20)),
            sa.Column("amount_cents", sa.BigInteger, nullable=False),
            sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'BRL'")),
            sa.Column(
                "status",
                enum_column("fiscal_invoice_status"),
                nullable=False,
                server_default=sa.text("'PENDING'"),
            ),
            sa.Column("pdf_storage_bucket", sa.String(63)),
            sa.Column("pdf_storage_key", sa.String(1024)),
            sa.Column("xml_storage_bucket", sa.String(63)),
            sa.Column("xml_storage_key", sa.String(1024)),
            sa.Column("error_message", sa.String),
            sa.Column("issued_at", timestamp_tz),
            sa.Column("canceled_at", timestamp_tz),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                exactly_one_of("order_id", "invoice_id", "subscription_id"),
                name="chk_fiscal_invoices_one_origin",
            ),
            sa.CheckConstraint("amount_cents >= 0", name="chk_fiscal_invoices_amount_nonnegative"),
            sa.CheckConstraint(
                currency_code_check("currency"), name="chk_fiscal_invoices_currency_format"
            ),
        )
        op.create_index(
            "uq_fiscal_invoices_access_key", "fiscal_invoices", ["access_key"], unique=True
        )
        op.create_index(
            "uq_fiscal_invoices_number_series_account",
            "fiscal_invoices",
            ["billing_account_id", "series", "number"],
            unique=True,
        )
        op.create_index(
            "ix_fiscal_invoices_billing_account_id", "fiscal_invoices", ["billing_account_id"]
        )
        op.create_index("ix_fiscal_invoices_status", "fiscal_invoices", ["status"])
        op.create_index("ix_fiscal_invoices_order_id", "fiscal_invoices", ["order_id"])
        op.create_index("ix_fiscal_invoices_invoice_id", "fiscal_invoices", ["invoice_id"])
        op.create_index(
            "ix_fiscal_invoices_subscription_id", "fiscal_invoices", ["subscription_id"]
        )

    if _missing("workspace_credit_lots"):
        op.create_table(
            "workspace_credit_lots",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column(
                "workspace_id",
                uuid_pk,
                sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("grant_transaction_id", uuid_pk, nullable=False, unique=True),
            sa.Column("original_amount", sa.Integer, nullable=False),
            sa.Column("remaining_amount", sa.Integer, nullable=False),
            sa.Column("expires_at", timestamp_tz),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["grant_transaction_id", "workspace_id"],
                [
                    "workspace_credit_transactions.id",
                    "workspace_credit_transactions.workspace_id",
                ],
                ondelete="RESTRICT",
                name="fk_credit_lots_grant_transaction",
            ),
            sa.CheckConstraint(
                "original_amount > 0 AND remaining_amount >= 0 "
                "AND remaining_amount <= original_amount",
                name="chk_credit_lots_amounts",
            ),
        )
        op.create_index(
            "uq_credit_lots_id_workspace",
            "workspace_credit_lots",
            ["id", "workspace_id"],
            unique=True,
        )
        op.create_index(
            "ix_workspace_credit_lots_workspace_id_expires_at",
            "workspace_credit_lots",
            ["workspace_id", "expires_at"],
        )
        op.create_index(
            "idx_m8_workspace_credit_lots_grant_transaction_id_workspace_id",
            "workspace_credit_lots",
            ["grant_transaction_id", "workspace_id"],
        )

    if _missing("workspace_credit_lot_consumptions"):
        op.create_table(
            "workspace_credit_lot_consumptions",
            sa.Column("id", uuid_pk, primary_key=True),
            sa.Column("workspace_id", uuid_pk, nullable=False),
            sa.Column("lot_id", uuid_pk, nullable=False),
            sa.Column("transaction_id", uuid_pk, nullable=False),
            sa.Column("amount", sa.Integer, nullable=False),
            sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["lot_id", "workspace_id"],
                ["workspace_credit_lots.id", "workspace_credit_lots.workspace_id"],
                ondelete="RESTRICT",
                name="fk_lot_consumptions_lot",
            ),
            sa.ForeignKeyConstraint(
                ["transaction_id", "workspace_id"],
                [
                    "workspace_credit_transactions.id",
                    "workspace_credit_transactions.workspace_id",
                ],
                ondelete="RESTRICT",
                name="fk_lot_consumptions_transaction",
            ),
            sa.CheckConstraint("amount > 0", name="chk_lot_consumptions_amount"),
        )
        op.create_index(
            "ix_workspace_credit_lot_consumptions_transaction_id",
            "workspace_credit_lot_consumptions",
            ["transaction_id"],
        )
        op.create_index(
            "uq_workspace_credit_lot_consumptions_lot_id_transaction_id",
            "workspace_credit_lot_consumptions",
            ["lot_id", "transaction_id"],
            unique=True,
        )
        op.create_index(
            "idx_m8_workspace_credit_lot_consumptions_lot_id_workspace_id",
            "workspace_credit_lot_consumptions",
            ["lot_id", "workspace_id"],
        )
        op.create_index(
            "idx_m8_lot_consumptions_transaction_workspace",
            "workspace_credit_lot_consumptions",
            ["transaction_id", "workspace_id"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in (
        "workspace_credit_lot_consumptions",
        "workspace_credit_lots",
        "fiscal_invoices",
        "charge_transactions",
        "plan_payment_methods",
    ):
        if inspector.has_table(table):
            op.drop_table(table)
