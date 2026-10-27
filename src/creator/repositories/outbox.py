from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.domain.pipeline_events import PipelineEvent


@dataclass(frozen=True, slots=True)
class OutboxEventRecord:
    id: UUID
    workspace_id: UUID
    aggregate_id: UUID
    event_type: str
    event_version: str
    payload: dict[str, object]
    available_at: datetime
    attempts: int = 0
    consumer_attempts: int = 0
    consumed_at: datetime | None = None
    dead_lettered_at: datetime | None = None


class OutboxRepository(Protocol):
    def add(self, *, workspace_id: UUID, aggregate_id: UUID, event: PipelineEvent) -> UUID: ...

    def claim_batch(self, *, limit: int = 50) -> list[OutboxEventRecord]: ...

    def mark_published(self, event_id: UUID) -> None: ...

    def mark_failed(
        self,
        event_id: UUID,
        error: str,
        *,
        max_attempts: int = 5,
        retry_intervals: tuple[int, ...] = (30, 60, 120, 300),
    ) -> bool: ...

    def claim_for_consumption(
        self, event_id: UUID, *, lease_seconds: int
    ) -> OutboxEventRecord | None: ...

    def mark_consumed(self, event_id: UUID) -> None: ...

    def mark_consumer_failed(
        self,
        event_id: UUID,
        error: str,
        *,
        max_attempts: int = 5,
        retry_intervals: tuple[int, ...] = (30, 60, 120, 300),
    ) -> bool: ...

    def dead_letter(self, event_id: UUID, *, phase: str, reason: str) -> None: ...

    def exists(self, event_id: UUID) -> bool: ...
