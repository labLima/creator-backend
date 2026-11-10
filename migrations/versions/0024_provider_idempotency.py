"""Align provider_idempotency_keys to the final modeling (T15, B4b)."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.portable_enums import enum_column
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0024_provider_idempotency"
down_revision = "0023_provider_dispute_alignment"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _columns("provider_idempotency_keys")
    if not columns or "expires_at" in columns:
        return
    rows = [
        dict(row._mapping)
        for row in op.get_bind().execute(
            sa.text(
                "SELECT id, provider, idempotency_key, request_hash, resource_type, "
                "resource_id, status, created_at, updated_at FROM provider_idempotency_keys "
                "WHERE deleted_at IS NULL"
            )
        )
    ]
    for row in rows:
        row["provider"] = str(row["provider"] or "PAGARME").upper()
        row["status"] = str(row["status"] or "STARTED").upper()
        row["expires_at"] = row["created_at"]
    op.create_table(
        "provider_idempotency_keys_old",
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
    if rows:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO provider_idempotency_keys_old "
                "(id, provider, idempotency_key, request_hash, resource_type, resource_id, "
                "status, expires_at, created_at, updated_at) "
                "VALUES (:id, :provider, :idempotency_key, :request_hash, :resource_type, "
                ":resource_id, :status, :expires_at, :created_at, :updated_at)"
            ),
            rows,
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
    if "deleted_at" in _columns("provider_idempotency_keys"):
        return
    op.create_table(
        "provider_idempotency_keys_legacy",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(
        "INSERT INTO provider_idempotency_keys_legacy "
        "(id, provider, idempotency_key, request_hash, resource_type, resource_id, "
        "status, created_at, updated_at) "
        "SELECT id, provider, idempotency_key, request_hash, resource_type, resource_id, "
        "lower(status), created_at, updated_at FROM provider_idempotency_keys"
    )
    op.drop_table("provider_idempotency_keys")
    op.rename_table("provider_idempotency_keys_legacy", "provider_idempotency_keys")
