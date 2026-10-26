"""Add provider-neutral artifact contracts to Generation Jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0013_polymorphic_generation_jobs"
down_revision: str | Sequence[str] | None = "0012_pdf_column_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    artifact_type = sa.Enum(
        "IMAGE",
        "TEXT",
        "COPY",
        "CAPTION",
        name="generation_type",
        native_enum=False,
        create_constraint=True,
    )
    generation_job_columns = (
        sa.Column("artifact_type", artifact_type, nullable=True),
        sa.Column("operation", sa.String(20), nullable=False, server_default="CREATE"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column("failure_policy", sa.String(20), nullable=False, server_default="FAIL"),
        sa.Column("request_id", sa.Uuid(as_uuid=True)),
    )
    if is_sqlite:
        with op.batch_alter_table("generation_jobs", recreate="always") as batch:
            for column in generation_job_columns:
                batch.add_column(column)
    else:
        for column in generation_job_columns:
            op.add_column("generation_jobs", column)
    op.execute(
        sa.text(
            "UPDATE generation_jobs SET artifact_type = "
            "(SELECT type FROM generations WHERE generations.id = generation_jobs.generation_id "
            "AND generations.workspace_id = generation_jobs.workspace_id)"
        )
    )
    if is_sqlite:
        with op.batch_alter_table("generation_jobs", recreate="always") as batch:
            batch.alter_column("artifact_type", nullable=False, server_default=sa.text("'IMAGE'"))
    else:
        op.alter_column(
            "generation_jobs", "artifact_type", nullable=False, server_default=sa.text("'IMAGE'")
        )
    status_event_columns = (
        ("artifact_type", artifact_type, True, None),
        ("version", sa.Integer(), False, "1"),
        ("correlation_id", sa.String(255), True, None),
        ("sanitized_result", sa.JSON(), False, None),
        ("request_id", sa.Uuid(as_uuid=True), False, None),
    )
    if is_sqlite:
        with op.batch_alter_table("generation_job_status_events", recreate="always") as batch:
            for name, column, nullable, server_default in status_event_columns:
                batch.add_column(
                    sa.Column(
                        name,
                        column,
                        nullable=nullable,
                        server_default=server_default,
                    )
                )
    else:
        for name, column, nullable, server_default in status_event_columns:
            op.add_column(
                "generation_job_status_events",
                sa.Column(name, column, nullable=nullable, server_default=server_default),
            )
    op.execute(
        sa.text(
            "UPDATE generation_job_status_events SET artifact_type = 'IMAGE', "
            "correlation_id = CAST(generation_job_id AS TEXT) WHERE artifact_type IS NULL"
        )
    )
    if is_sqlite:
        with op.batch_alter_table("generation_job_status_events", recreate="always") as batch:
            batch.alter_column("artifact_type", nullable=False)
            batch.alter_column("correlation_id", nullable=False)
    else:
        op.alter_column("generation_job_status_events", "artifact_type", nullable=False)
        op.alter_column("generation_job_status_events", "correlation_id", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("generation_job_status_events", recreate="always") as batch:
            batch.drop_constraint("generation_type", type_="check")
            for column in (
                "request_id",
                "sanitized_result",
                "correlation_id",
                "version",
                "artifact_type",
            ):
                batch.drop_column(column)
        with op.batch_alter_table("generation_jobs", recreate="always") as batch:
            batch.drop_constraint("generation_type", type_="check")
            for column in (
                "request_id",
                "failure_policy",
                "idempotency_key",
                "timeout_seconds",
                "operation",
                "artifact_type",
            ):
                batch.drop_column(column)
        return

    for table, columns in (
        (
            "generation_job_status_events",
            ("request_id", "sanitized_result", "correlation_id", "version", "artifact_type"),
        ),
        (
            "generation_jobs",
            (
                "request_id",
                "failure_policy",
                "idempotency_key",
                "timeout_seconds",
                "operation",
                "artifact_type",
            ),
        ),
    ):
        for column in columns:
            op.drop_column(table, column)
