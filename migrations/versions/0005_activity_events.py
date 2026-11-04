"""Create the Activity Event audit history."""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.types import json_type, timestamp_tz, uuid_pk

revision = "0005_activity_events"
down_revision = "0004_drop_dead_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The historical baseline creates all current metadata on a fresh database.
    if sa.inspect(op.get_bind()).has_table("activity_events"):
        return
    op.create_table(
        "activity_events",
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column(
            "workspace_id",
            uuid_pk,
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("user_id", uuid_pk, sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("brand_id", uuid_pk, sa.ForeignKey("brands.id", ondelete="RESTRICT")),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", uuid_pk),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("entity_type = 'brand'", name="ck_activity_events_entity_type"),
        sa.CheckConstraint(
            "event_type IN ('brand.created', 'brand.updated', 'brand.deleted')",
            name="ck_activity_events_event_type",
        ),
    )
    op.create_index(
        "ix_activity_events_workspace_created",
        "activity_events",
        ["workspace_id", "created_at", "id"],
    )
    op.create_index("ix_activity_events_user", "activity_events", ["user_id"])
    op.create_index("ix_activity_events_brand", "activity_events", ["brand_id"])
    op.create_index("ix_activity_events_entity", "activity_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("activity_events")
