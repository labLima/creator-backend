from __future__ import annotations

from typing import Protocol
from uuid import UUID

from creator.config import Settings, get_settings
from creator.domain.pipeline_events import PipelineEvent
from creator.uow import UnitOfWork


class PipelineEventTransport(Protocol):
    def enqueue_pipeline_event(self, *, event_id: UUID, event: PipelineEvent) -> object: ...


class OutboxPublisher:
    """Publishes committed events and leaves failed rows available for retry."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        transport: PipelineEventTransport,
        settings: Settings | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._transport = transport
        self._settings = settings or get_settings()

    def publish_once(self, *, limit: int = 50) -> int:
        events = self._unit_of_work.outbox.claim_batch(limit=limit)
        published = 0
        for record in events:
            try:
                event = PipelineEvent.model_validate(record.payload)
                self._transport.enqueue_pipeline_event(event_id=record.id, event=event)
            except Exception as error:
                self._unit_of_work.outbox.mark_failed(
                    record.id,
                    str(error),
                    max_attempts=self._settings.pipeline_event_max_attempts,
                    retry_intervals=tuple(self._settings.pipeline_event_retry_interval_seconds),
                )
                continue
            self._unit_of_work.outbox.mark_published(record.id)
            published += 1
        self._unit_of_work.commit()
        return published
