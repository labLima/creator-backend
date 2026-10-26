"""Persist versioned pipeline hand-off audit metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0014_agent_pipeline_audit"
down_revision: str | Sequence[str] | None = "0013_polymorphic_generation_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("agent_workflow_steps", recreate="always") as batch:
            for name, column in (
                ("output_hash", sa.String(64)),
                ("schema_name", sa.String(100)),
                ("schema_version", sa.String(32)),
                ("predecessor_step_id", sa.Uuid(as_uuid=True)),
                ("correlation_id", sa.Uuid(as_uuid=True)),
            ):
                batch.add_column(sa.Column(name, column, nullable=True))
        return

    for name, column in (
        ("output_hash", sa.String(64)),
        ("schema_name", sa.String(100)),
        ("schema_version", sa.String(32)),
        ("predecessor_step_id", sa.Uuid(as_uuid=True)),
        ("correlation_id", sa.Uuid(as_uuid=True)),
    ):
        op.add_column("agent_workflow_steps", sa.Column(name, column, nullable=True))


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("agent_workflow_steps", recreate="always") as batch:
            for name in (
                "correlation_id",
                "predecessor_step_id",
                "schema_version",
                "schema_name",
                "output_hash",
            ):
                batch.drop_column(name)
        return

    for name in (
        "correlation_id",
        "predecessor_step_id",
        "schema_version",
        "schema_name",
        "output_hash",
    ):
        op.drop_column("agent_workflow_steps", name)
