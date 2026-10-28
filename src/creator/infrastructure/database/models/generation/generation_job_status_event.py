from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from creator.domain.generation import GenerationJobStatus
from creator.infrastructure.database import schema_models as _schema_models  # noqa: F401
from creator.infrastructure.database.db import Base

from ..enums import (
    GenerationType,
    generation_job_status_enum,
    generation_type_enum,
)
from ..types import json_type, timestamp_tz, uuid_default, uuid_pk


class GenerationJobStatusEvent(Base):
    __tablename__ = "generation_job_status_events"
    __table_args__ = (
        CheckConstraint(
            "previous_status IS NULL OR previous_status <> status",
            name="ck_generation_job_status_events_status_changed",
        ),
        Index(
            "ix_generation_job_status_events_job_occurred_at", "generation_job_id", "occurred_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    generation_job_id: Mapped[UUID] = mapped_column(
        uuid_pk,
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[GenerationJobStatus | None] = mapped_column(generation_job_status_enum)
    status: Mapped[GenerationJobStatus] = mapped_column(generation_job_status_enum, nullable=False)
    artifact_type: Mapped[GenerationType] = mapped_column(
        generation_type_enum, nullable=False, server_default=text("'IMAGE'")
    )
    version: Mapped[int] = mapped_column(nullable=False, server_default=text("1"))
    correlation_id: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=text("''")
    )
    sanitized_result: Mapped[dict[str, object] | None] = mapped_column(json_type)
    request_id: Mapped[UUID | None] = mapped_column(uuid_pk)
    occurred_at: Mapped[object] = mapped_column(
        timestamp_tz,
        nullable=False,
        server_default=func.now(),
    )
