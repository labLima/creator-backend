"""Bring pre-baseline SQLite databases up to the local-auth/outbox schema.

The SQLite baseline already contains these objects for a fresh database. This
migration is intentionally conditional so a database created before the auth
and outbox claim work can be upgraded without dropping data.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0002_outbox_and_auth_columns"
down_revision: str | Sequence[str] | None = "0001_sqlite_baseline"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()

    if "auth_sessions" not in tables:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("family_id", sa.Uuid(), nullable=False),
            sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
            sa.Column("replaced_by_id", sa.Uuid()),
            sa.Column("user_agent", sa.String(length=500)),
            sa.Column("ip_address", sa.String(length=45)),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("last_used_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("refresh_token_hash", name="uq_auth_sessions_refresh_token_hash"),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_family_id", "auth_sessions", ["family_id"])
        op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    if "password_hash" not in _columns("users"):
        op.add_column("users", sa.Column("password_hash", sa.String(length=255)))

    outbox_columns = _columns("outbox_events")
    if "claimed_at" not in outbox_columns:
        op.add_column("outbox_events", sa.Column("claimed_at", sa.DateTime(timezone=True)))
    if "claimed_by" not in outbox_columns:
        op.add_column("outbox_events", sa.Column("claimed_by", sa.String(length=64)))


def downgrade() -> None:
    outbox_columns = _columns("outbox_events")
    if "claimed_by" in outbox_columns:
        op.drop_column("outbox_events", "claimed_by")
    if "claimed_at" in outbox_columns:
        op.drop_column("outbox_events", "claimed_at")

    if "password_hash" in _columns("users"):
        op.drop_column("users", "password_hash")

    if "auth_sessions" in _tables():
        op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
        op.drop_index("ix_auth_sessions_family_id", table_name="auth_sessions")
        op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
        op.drop_table("auth_sessions")
