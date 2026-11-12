"""Add the provider micro-divergences of the final modeling (T27, issue #170).

The final modeling declares ``provider_webhook_events.updated_at`` and a
``'RECEIVED'`` default for its ``status``, plus a ``'PAGARME'`` default for
``provider_idempotency_keys.provider``. SQLite cannot add a NOT NULL column with
a non-constant default, so ``provider_webhook_events`` is rebuilt to gain
``updated_at`` and its new constant server defaults. ``provider_idempotency_keys``
is rebuilt only to add the ``'PAGARME'`` server default: SQLite cannot attach a
default to an existing column in place, even a constant one.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0033_provider_micro_alignment"
down_revision = "0032_coupon_redemption"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    _upgrade_webhook_events()
    _upgrade_idempotency_keys()


def _upgrade_webhook_events() -> None:
    columns = _columns("provider_webhook_events")
    if not columns or "updated_at" in columns:
        return
    op.create_table(
        "provider_webhook_events_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("payload", json_type, nullable=False),
        sa.Column(
            "signature_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "status",
            enum_column("webhook_processing_status", create_constraint=False),
            nullable=False,
            server_default=sa.text("'RECEIVED'"),
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text()),
        sa.Column("received_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", timestamp_tz),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dedupe_key", name="uq_provider_webhook_events_dedupe_key"),
    )
    # Backfill before the NOT NULL column is enforced: an event that was already
    # processed keeps its processing timestamp; the rest fall back to receipt.
    op.execute(
        "INSERT INTO provider_webhook_events_old "
        "(id, provider, external_id, dedupe_key, event_type, account_id, "
        "resource_type, resource_id, payload, signature_verified, status, "
        "attempts, last_error, received_at, processed_at, updated_at) "
        "SELECT id, provider, external_id, dedupe_key, event_type, account_id, "
        "resource_type, resource_id, payload, signature_verified, status, "
        "attempts, last_error, received_at, processed_at, "
        "COALESCE(processed_at, received_at, CURRENT_TIMESTAMP) "
        "FROM provider_webhook_events"
    )
    op.drop_table("provider_webhook_events")
    op.rename_table("provider_webhook_events_old", "provider_webhook_events")
    op.create_index(
        "uq_provider_webhook_events_provider_external_id",
        "provider_webhook_events",
        ["provider", "external_id"],
        unique=True,
    )
    op.create_index(
        "ix_provider_webhook_events_event_type", "provider_webhook_events", ["event_type"]
    )
    op.create_index(
        "ix_provider_webhook_events_resource_id", "provider_webhook_events", ["resource_id"]
    )
    op.create_index(
        "ix_provider_webhook_events_status_received_at",
        "provider_webhook_events",
        ["status", "received_at"],
    )


def _upgrade_idempotency_keys() -> None:
    columns = _columns("provider_idempotency_keys")
    if not columns:
        return
    defaults = {
        column["name"]: column["default"]
        for column in sa.inspect(op.get_bind()).get_columns("provider_idempotency_keys")
    }
    if defaults.get("provider") is not None:
        return
    op.create_table(
        "provider_idempotency_keys_old",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column(
            "status",
            enum_column("idempotency_status", create_constraint=False),
            nullable=False,
        ),
        sa.Column("expires_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "INSERT INTO provider_idempotency_keys_old "
        "(id, provider, idempotency_key, request_hash, resource_type, resource_id, "
        "status, expires_at, created_at, updated_at) "
        "SELECT id, provider, idempotency_key, request_hash, resource_type, resource_id, "
        "status, expires_at, created_at, updated_at FROM provider_idempotency_keys"
    )
    op.drop_table("provider_idempotency_keys")
    op.rename_table("provider_idempotency_keys_old", "provider_idempotency_keys")
    op.create_index(
        "uq_provider_idempotency_keys_provider_key",
        "provider_idempotency_keys",
        ["provider", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_provider_idempotency_keys_expires_at",
        "provider_idempotency_keys",
        ["expires_at"],
    )


def downgrade() -> None:
    _downgrade_idempotency_keys()
    _downgrade_webhook_events()


def _downgrade_webhook_events() -> None:
    columns = _columns("provider_webhook_events")
    if not columns or "updated_at" not in columns:
        return
    op.create_table(
        "provider_webhook_events_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
            server_default=sa.text("'PAGARME'"),
        ),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("payload", json_type, nullable=False),
        sa.Column(
            "signature_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "status",
            enum_column("webhook_processing_status", create_constraint=False),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text()),
        sa.Column("received_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", timestamp_tz),
        sa.UniqueConstraint("dedupe_key", name="uq_provider_webhook_events_dedupe_key"),
    )
    op.execute(
        "INSERT INTO provider_webhook_events_legacy "
        "(id, provider, external_id, dedupe_key, event_type, account_id, "
        "resource_type, resource_id, payload, signature_verified, status, "
        "attempts, last_error, received_at, processed_at) "
        "SELECT id, provider, external_id, dedupe_key, event_type, account_id, "
        "resource_type, resource_id, payload, signature_verified, status, "
        "attempts, last_error, received_at, processed_at FROM provider_webhook_events"
    )
    op.drop_table("provider_webhook_events")
    op.rename_table("provider_webhook_events_legacy", "provider_webhook_events")
    op.create_index(
        "uq_provider_webhook_events_provider_external_id",
        "provider_webhook_events",
        ["provider", "external_id"],
        unique=True,
    )
    op.create_index(
        "ix_provider_webhook_events_event_type", "provider_webhook_events", ["event_type"]
    )
    op.create_index(
        "ix_provider_webhook_events_resource_id", "provider_webhook_events", ["resource_id"]
    )
    op.create_index(
        "ix_provider_webhook_events_status_received_at",
        "provider_webhook_events",
        ["status", "received_at"],
    )


def _downgrade_idempotency_keys() -> None:
    columns = _columns("provider_idempotency_keys")
    if not columns:
        return
    defaults = {
        column["name"]: column["default"]
        for column in sa.inspect(op.get_bind()).get_columns("provider_idempotency_keys")
    }
    if defaults.get("provider") is None:
        return
    op.create_table(
        "provider_idempotency_keys_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "provider",
            enum_column("payment_provider", create_constraint=False),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column(
            "status",
            enum_column("idempotency_status", create_constraint=False),
            nullable=False,
        ),
        sa.Column("expires_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "INSERT INTO provider_idempotency_keys_legacy "
        "(id, provider, idempotency_key, request_hash, resource_type, resource_id, "
        "status, expires_at, created_at, updated_at) "
        "SELECT id, provider, idempotency_key, request_hash, resource_type, resource_id, "
        "status, expires_at, created_at, updated_at FROM provider_idempotency_keys"
    )
    op.drop_table("provider_idempotency_keys")
    op.rename_table("provider_idempotency_keys_legacy", "provider_idempotency_keys")
    op.create_index(
        "uq_provider_idempotency_keys_provider_key",
        "provider_idempotency_keys",
        ["provider", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_provider_idempotency_keys_expires_at",
        "provider_idempotency_keys",
        ["expires_at"],
    )
