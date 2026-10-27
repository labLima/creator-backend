"""Add durable consumer, retry and dead-letter state to pipeline events."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0003_pipeline_delivery_state"
down_revision: str | Sequence[str] | None = "0002_outbox_and_auth_columns"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    outbox_columns = _columns("outbox_events")
    additions = (
        (
            "consumer_attempts",
            sa.Column("consumer_attempts", sa.Integer(), nullable=False, server_default="0"),
        ),
        (
            "consumer_available_at",
            sa.Column(
                "consumer_available_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        ),
        ("consumer_claimed_at", sa.Column("consumer_claimed_at", sa.DateTime(timezone=True))),
        ("consumer_claimed_by", sa.Column("consumer_claimed_by", sa.String(length=64))),
        ("consumed_at", sa.Column("consumed_at", sa.DateTime(timezone=True))),
        ("last_consumer_error", sa.Column("last_consumer_error", sa.Text())),
        ("dead_lettered_at", sa.Column("dead_lettered_at", sa.DateTime(timezone=True))),
        ("dead_letter_phase", sa.Column("dead_letter_phase", sa.String(length=32))),
        ("dead_letter_reason", sa.Column("dead_letter_reason", sa.Text())),
    )
    for name, column in additions:
        if name not in outbox_columns:
            op.add_column("outbox_events", column)
    if "ix_outbox_events_consume" not in _indexes("outbox_events"):
        op.create_index(
            "ix_outbox_events_consume",
            "outbox_events",
            ["consumed_at", "consumer_available_at", "dead_lettered_at"],
        )

    step_columns = _columns("agent_workflow_steps")
    if "source_event_id" not in step_columns:
        op.add_column("agent_workflow_steps", sa.Column("source_event_id", sa.Uuid()))
    if "stage_item" not in step_columns:
        op.add_column(
            "agent_workflow_steps",
            sa.Column("stage_item", sa.Integer(), nullable=False, server_default="0"),
        )
    step_indexes = _indexes("agent_workflow_steps")
    if "ix_agent_workflow_steps_source_event" not in step_indexes:
        op.create_index(
            "ix_agent_workflow_steps_source_event",
            "agent_workflow_steps",
            ["source_event_id"],
        )
    if "uq_agent_workflow_steps_completed_source_role_item" not in step_indexes:
        op.create_index(
            "uq_agent_workflow_steps_completed_source_role_item",
            "agent_workflow_steps",
            ["source_event_id", "role", "stage_item"],
            unique=True,
            sqlite_where=sa.text("status = 'COMPLETED' AND source_event_id IS NOT NULL"),
            postgresql_where=sa.text("status = 'COMPLETED' AND source_event_id IS NOT NULL"),
        )


def downgrade() -> None:
    step_indexes = _indexes("agent_workflow_steps")
    if "uq_agent_workflow_steps_completed_source_role_item" in step_indexes:
        op.drop_index(
            "uq_agent_workflow_steps_completed_source_role_item",
            table_name="agent_workflow_steps",
        )
    if "ix_agent_workflow_steps_source_event" in step_indexes:
        op.drop_index("ix_agent_workflow_steps_source_event", table_name="agent_workflow_steps")
    step_columns = _columns("agent_workflow_steps")
    if "stage_item" in step_columns:
        op.drop_column("agent_workflow_steps", "stage_item")
    if "source_event_id" in step_columns:
        op.drop_column("agent_workflow_steps", "source_event_id")

    if "ix_outbox_events_consume" in _indexes("outbox_events"):
        op.drop_index("ix_outbox_events_consume", table_name="outbox_events")
    outbox_columns = _columns("outbox_events")
    for name in (
        "dead_letter_reason",
        "dead_letter_phase",
        "dead_lettered_at",
        "last_consumer_error",
        "consumed_at",
        "consumer_claimed_by",
        "consumer_claimed_at",
        "consumer_available_at",
        "consumer_attempts",
    ):
        if name in outbox_columns:
            op.drop_column("outbox_events", name)
