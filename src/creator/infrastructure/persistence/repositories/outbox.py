from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from creator.domain.pipeline_events import PipelineEvent
from creator.workflow import models as workflow_tables
from creator.workflow.ports import OutboxEventRecord


class SqlAlchemyOutboxRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, workspace_id: UUID, aggregate_id: UUID, event: PipelineEvent) -> UUID:
        row = workflow_tables.OutboxEvent(
            id=event.event_id,
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
            select(workflow_tables.OutboxEvent.id)
            .where(
                workflow_tables.OutboxEvent.published_at.is_(None),
                workflow_tables.OutboxEvent.dead_lettered_at.is_(None),
                workflow_tables.OutboxEvent.available_at <= now,
                (workflow_tables.OutboxEvent.claimed_at.is_(None))
                | (workflow_tables.OutboxEvent.claimed_at < stale_before),
            )
            .order_by(workflow_tables.OutboxEvent.created_at.asc())
            .limit(limit)
        )
        self._session.execute(
            update(workflow_tables.OutboxEvent)
            .where(workflow_tables.OutboxEvent.id.in_(candidate_ids))
            .values(
                claimed_at=now,
                claimed_by=claim_token,
                attempts=workflow_tables.OutboxEvent.attempts + 1,
            )
            .execution_options(synchronize_session=False)
        )
        rows = self._session.scalars(
            select(workflow_tables.OutboxEvent)
            .where(
                workflow_tables.OutboxEvent.claimed_by == claim_token,
                workflow_tables.OutboxEvent.published_at.is_(None),
            )
            .order_by(workflow_tables.OutboxEvent.created_at.asc())
        ).all()
        return [_record(row) for row in rows]

    def mark_published(self, event_id: UUID) -> None:
        row = self._session.get(workflow_tables.OutboxEvent, event_id)
        if row is not None:
            row.published_at = datetime.now(UTC)
            row.claimed_at = None
            row.claimed_by = None

    def mark_failed(
        self,
        event_id: UUID,
        error: str,
        *,
        max_attempts: int = 5,
        retry_intervals: tuple[int, ...] = (30, 60, 120, 300),
    ) -> bool:
        row = self._session.get(workflow_tables.OutboxEvent, event_id)
        if row is None:
            return False
        row.last_error = error[:2_000]
        row.claimed_at = None
        row.claimed_by = None
        if row.attempts >= max_attempts:
            self._set_dead_letter(row, phase="PUBLISH", reason=error)
            return True
        delay = retry_intervals[min(max(row.attempts - 1, 0), len(retry_intervals) - 1)]
        row.available_at = datetime.now(UTC) + timedelta(seconds=delay)
        return False

    def claim_for_consumption(
        self, event_id: UUID, *, lease_seconds: int
    ) -> OutboxEventRecord | None:
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=lease_seconds)
        claim_token = uuid4().hex
        self._session.execute(
            update(workflow_tables.OutboxEvent)
            .where(
                workflow_tables.OutboxEvent.id == event_id,
                workflow_tables.OutboxEvent.consumed_at.is_(None),
                workflow_tables.OutboxEvent.dead_lettered_at.is_(None),
                (workflow_tables.OutboxEvent.consumer_claimed_at.is_(None))
                | (workflow_tables.OutboxEvent.consumer_claimed_at < stale_before),
            )
            .values(
                consumer_claimed_at=now,
                consumer_claimed_by=claim_token,
                consumer_attempts=workflow_tables.OutboxEvent.consumer_attempts + 1,
            )
            .execution_options(synchronize_session=False)
        )
        row = self._session.scalars(
            select(workflow_tables.OutboxEvent).where(
                workflow_tables.OutboxEvent.id == event_id,
                workflow_tables.OutboxEvent.consumer_claimed_by == claim_token,
            )
        ).one_or_none()
        return _record(row) if row is not None else None

    def mark_consumed(self, event_id: UUID) -> None:
        row = self._session.get(workflow_tables.OutboxEvent, event_id)
        if row is None or row.dead_lettered_at is not None:
            return
        row.consumed_at = datetime.now(UTC)
        row.consumer_claimed_at = None
        row.consumer_claimed_by = None
        row.last_consumer_error = None

    def mark_consumer_failed(
        self,
        event_id: UUID,
        error: str,
        *,
        max_attempts: int = 5,
        retry_intervals: tuple[int, ...] = (30, 60, 120, 300),
    ) -> bool:
        row = self._session.get(workflow_tables.OutboxEvent, event_id)
        if row is None:
            return False
        row.last_consumer_error = error[:2_000]
        row.consumer_claimed_at = None
        row.consumer_claimed_by = None
        if row.consumer_attempts >= max_attempts:
            self._set_dead_letter(row, phase="CONSUME", reason=error)
            return True
        delay = retry_intervals[min(max(row.consumer_attempts - 1, 0), len(retry_intervals) - 1)]
        row.consumer_available_at = datetime.now(UTC) + timedelta(seconds=delay)
        return False

    def dead_letter(self, event_id: UUID, *, phase: str, reason: str) -> None:
        row = self._session.get(workflow_tables.OutboxEvent, event_id)
        if row is not None:
            self._set_dead_letter(row, phase=phase, reason=reason)

    def exists(self, event_id: UUID) -> bool:
        return self._session.get(workflow_tables.OutboxEvent, event_id) is not None

    @staticmethod
    def _set_dead_letter(row: workflow_tables.OutboxEvent, *, phase: str, reason: str) -> None:
        row.dead_lettered_at = datetime.now(UTC)
        row.dead_letter_phase = phase[:32]
        row.dead_letter_reason = reason[:2_000]
        row.claimed_at = None
        row.claimed_by = None
        row.consumer_claimed_at = None
        row.consumer_claimed_by = None


def _record(row: workflow_tables.OutboxEvent) -> OutboxEventRecord:
    return OutboxEventRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        aggregate_id=row.aggregate_id,
        event_type=row.event_type,
        event_version=row.event_version,
        payload=dict(row.payload),
        available_at=cast(datetime, row.available_at),
        attempts=row.attempts,
        consumer_attempts=row.consumer_attempts,
        consumed_at=cast(datetime | None, row.consumed_at),
        dead_lettered_at=cast(datetime | None, row.dead_lettered_at),
    )
