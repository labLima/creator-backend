"""Align provider_webhook_events to the final modeling (T15, B4c)."""

import json

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0025_provider_webhook"
down_revision = "0024_provider_idempotency"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("provider_webhook_events")
    if not columns or "external_id" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, provider, provider_event_id, dedupe_key, event_type, "
                "account_id, resource_type, resource_id, payload, signature_verified, "
                "status, attempts, last_error, received_at, processed_at "
                "FROM provider_webhook_events WHERE deleted_at IS NULL"
            )
        )
    ]
    seen_external: set[tuple[str, str]] = set()
    seen_dedupe: set[str] = set()
    for row in rows:
        provider = str(row["provider"] or "PAGARME").upper()
        external = str(row["provider_event_id"]) or str(row["id"])
        if (provider, external) in seen_external:
            external = f"{external}~{row['id']}"
        seen_external.add((provider, external))
        dedupe = str(row["dedupe_key"])
        if dedupe in seen_dedupe:
            dedupe = f"{dedupe}~{row['id']}"
        seen_dedupe.add(dedupe)
        row.update(
            {
                "provider": provider,
                "external_id": external,
                "dedupe_key": dedupe,
                "status": str(row["status"] or "RECEIVED").upper(),
                "payload": (
                    json.dumps(row["payload"])
                    if isinstance(row["payload"], (dict, list))
                    else row["payload"]
                ),
            }
        )
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
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text()),
        sa.Column("received_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", timestamp_tz),
        sa.UniqueConstraint("dedupe_key", name="uq_provider_webhook_events_dedupe_key"),
    )
    if rows:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO provider_webhook_events_old "
                "(id, provider, external_id, dedupe_key, event_type, account_id, "
                "resource_type, resource_id, payload, signature_verified, status, "
                "attempts, last_error, received_at, processed_at) "
                "VALUES (:id, :provider, :external_id, :dedupe_key, :event_type, "
                ":account_id, :resource_type, :resource_id, :payload, "
                ":signature_verified, :status, :attempts, :last_error, :received_at, "
                ":processed_at)"
            ),
            rows,
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


def downgrade() -> None:
    if "provider_event_id" in _columns("provider_webhook_events"):
        return
    op.create_table(
        "provider_webhook_events_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_event_id", sa.String(64), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("account_id", sa.String(64)),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("payload", json_type, nullable=False),
        sa.Column(
            "signature_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text()),
        sa.Column("received_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", timestamp_tz),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO provider_webhook_events_legacy "
        "(id, provider, provider_event_id, dedupe_key, event_type, account_id, "
        "resource_type, resource_id, payload, signature_verified, status, attempts, "
        "last_error, received_at, processed_at, created_at, updated_at) "
        "SELECT id, provider, external_id, dedupe_key, event_type, account_id, "
        "resource_type, resource_id, payload, signature_verified, lower(status), "
        "attempts, last_error, received_at, processed_at, received_at, received_at "
        "FROM provider_webhook_events"
    )
    op.drop_table("provider_webhook_events")
    op.rename_table("provider_webhook_events_legacy", "provider_webhook_events")
