"""Add absolute session expiry and rotation metadata."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_auth_session_rotation"
down_revision = "0003_pipeline_delivery_state"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("auth_sessions")}


def upgrade() -> None:
    columns = _columns()
    if "previous_refresh_token_hash" not in columns:
        op.add_column("auth_sessions", sa.Column("previous_refresh_token_hash", sa.String(64)))
    if "absolute_expires_at" not in columns:
        op.add_column(
            "auth_sessions",
            sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.execute(sa.text("UPDATE auth_sessions SET absolute_expires_at = expires_at"))
        with op.batch_alter_table("auth_sessions") as batch:
            batch.alter_column("absolute_expires_at", nullable=False)
    if "rotated_at" not in columns:
        op.add_column("auth_sessions", sa.Column("rotated_at", sa.DateTime(timezone=True)))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("auth_sessions")}
    if "ix_auth_sessions_absolute_expires_at" not in indexes:
        op.create_index(
            "ix_auth_sessions_absolute_expires_at",
            "auth_sessions",
            ["absolute_expires_at"],
        )


def downgrade() -> None:
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("auth_sessions")}
    if "ix_auth_sessions_absolute_expires_at" in indexes:
        op.drop_index("ix_auth_sessions_absolute_expires_at", table_name="auth_sessions")
    columns = _columns()
    with op.batch_alter_table("auth_sessions") as batch:
        for name in ("rotated_at", "absolute_expires_at", "previous_refresh_token_hash"):
            if name in columns:
                batch.drop_column(name)
