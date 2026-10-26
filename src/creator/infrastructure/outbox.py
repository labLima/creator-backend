from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from creator.domain.pipeline_events import PipelineEvent
from creator.infrastructure import models
from creator.repositories.outbox import OutboxEventRecord


class SqlAlchemyOutboxRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, workspace_id: UUID, aggregate_id: UUID, event: PipelineEvent) -> UUID:
        row = models.OutboxEvent(
            workspace_id=workspace_id,
            aggregate_id=aggregate_id,
            event_type=event.event_type.value,
            event_version=event.event_version,
            payload=event.model_dump(mode="json"),
        )
        self._session.add(row)
        self._session.flush()
        return row.id

    def claim_batch(self, *, limit: int = 50) -> list[OutboxEventRecord]:
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=60)
        claim_token = uuid4().hex
        candidate_ids = (
            select(models.OutboxEvent.id)
            .where(
                models.OutboxEvent.published_at.is_(None),
                models.OutboxEvent.available_at <= now,
                (models.OutboxEvent.claimed_at.is_(None))
                | (models.OutboxEvent.claimed_at < stale_before),
            )
            .order_by(models.OutboxEvent.created_at.asc())
            .limit(limit)
        )
        self._session.execute(
            update(models.OutboxEvent)
            .where(models.OutboxEvent.id.in_(candidate_ids))
            .values(
                claimed_at=now,
                claimed_by=claim_token,
                attempts=models.OutboxEvent.attempts + 1,
            )
            .execution_options(synchronize_session=False)
        )
        rows = self._session.scalars(
            select(models.OutboxEvent)
            .where(
                models.OutboxEvent.claimed_by == claim_token,
                models.OutboxEvent.published_at.is_(None),
            )
            .order_by(models.OutboxEvent.created_at.asc())
        ).all()
        return [_record(row) for row in rows]

    def mark_published(self, event_id: UUID) -> None:
        row = self._session.get(models.OutboxEvent, event_id)
        if row is not None:
            row.published_at = datetime.now(UTC)
            row.claimed_at = None
            row.claimed_by = None

    def mark_failed(self, event_id: UUID, error: str) -> None:
        row = self._session.get(models.OutboxEvent, event_id)
        if row is not None:
            row.last_error = error[:2_000]
            row.claimed_at = None
            row.claimed_by = None
            row.available_at = datetime.now(UTC) + timedelta(seconds=60)


def _record(row: models.OutboxEvent) -> OutboxEventRecord:
    return OutboxEventRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        aggregate_id=row.aggregate_id,
        event_type=row.event_type,
        event_version=row.event_version,
        payload=dict(row.payload),
        available_at=cast(datetime, row.available_at),
    )
