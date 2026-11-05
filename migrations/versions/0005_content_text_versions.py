"""Persist immutable text Content Versions produced by Generation Jobs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0005_content_text_versions"
down_revision = "0005_activity_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The SQLite baseline derives its first schema from current metadata. A
    # fresh database may therefore already contain this table at revision 0001.
    if sa.inspect(op.get_bind()).has_table("content_text_versions"):
        return
    op.create_table(
        "content_text_versions",
        sa.Column("id", uuid_pk, nullable=False),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("content_id", uuid_pk, nullable=False),
        sa.Column("generation_id", uuid_pk, nullable=False),
        sa.Column("artifact_type", sa.String(16), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("version_number > 0", name="ck_content_text_versions_positive"),
        sa.CheckConstraint(
            "artifact_type IN ('COPY', 'CAPTION')",
            name="ck_content_text_versions_artifact_type",
        ),
        sa.CheckConstraint(
            "length(text) BETWEEN 1 AND 20000", name="ck_content_text_versions_text"
        ),
        sa.ForeignKeyConstraint(
            ["content_id", "workspace_id"],
            ["contents.id", "contents.workspace_id"],
            name="fk_content_text_versions_content_workspace",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["generation_id"], ["generations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id", "version_number", name="uq_content_text_versions_number"),
        sa.UniqueConstraint("generation_id", name="uq_content_text_versions_generation"),
    )
    op.create_index(
        "ix_content_text_versions_content_version",
        "content_text_versions",
        ["content_id", "version_number"],
    )


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("content_text_versions"):
        return
    op.drop_index("ix_content_text_versions_content_version", table_name="content_text_versions")
    op.drop_table("content_text_versions")
