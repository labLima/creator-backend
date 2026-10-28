from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from creator.config import Settings
from creator.domain.pipeline_events import PipelineEvent, PipelineEventType
from creator.infrastructure.runtime import queue


class FakeRedis:
    @classmethod
    def from_url(cls, url: str) -> str:
        return f"connection:{url}"


class FakeQueue:
    def __init__(self, name: str, *, connection: object, default_timeout: int) -> None:
        self.name = name
        self.connection = connection
        self.default_timeout = default_timeout
        self.calls: list[dict[str, object]] = []

    def enqueue(self, f: str, *args: object, **kwargs: object) -> object:
        self.calls.append({"f": f, "args": args, **kwargs})
        return object()


class FakeRetry:
    def __init__(self, *, max: int, interval: list[int]) -> None:
        self.max = max
        self.interval = interval


def test_rq_generation_queue_enqueues_image_job_with_retry_policy(
    monkeypatch,
) -> None:
    queues: list[FakeQueue] = []

    def fake_queue(name: str, *, connection: object, default_timeout: int) -> FakeQueue:
        created = FakeQueue(name, connection=connection, default_timeout=default_timeout)
        queues.append(created)
        return created

    monkeypatch.setattr(queue, "Redis", FakeRedis)
    monkeypatch.setattr(queue, "Queue", fake_queue)
    monkeypatch.setattr(queue, "Retry", FakeRetry)
    settings = Settings(
        _env_file=None,
        redis_url="redis://redis:6379/0",
        generation_queue_name="creator:rq:generations",
        image_generation_job_timeout_seconds=123,
        image_generation_job_max_attempts=4,
        image_generation_retry_interval_seconds=[10, 20, 40],
    )
    job_id = UUID("50000000-0000-0000-0000-000000000001")
    request_id = UUID("70000000-0000-0000-0000-000000000001")

    queue.RqGenerationQueue(settings).enqueue_image_generation(
        job_id=job_id,
        request_id=request_id,
    )

    created = queues[0]
    call = created.calls[0]
    assert created.name == "creator:rq:generations"
    assert created.connection == "connection:redis://redis:6379/0"
    assert created.default_timeout == 123
    assert call["f"] == "creator.workers.image_generation.run_image_generation"
    assert call["args"] == (str(job_id), str(request_id))
    assert call["job_id"] == f"creator:rq:image-generation:{job_id}"
    assert call["job_timeout"] == 123
    assert call["meta"] == {
        "request_id": str(request_id),
        "generation_job_id": str(job_id),
    }
    retry = call["retry"]
    assert retry.max == 3
    assert retry.interval == [10, 20, 40]


@pytest.mark.parametrize(
    ("event_type", "handler"),
    [
        (PipelineEventType.WORKFLOW_STARTED, "consume_business_event"),
        (PipelineEventType.BUSINESS_COMPLETED, "consume_planner_event"),
        (PipelineEventType.PLANNER_COMPLETED, "consume_writer_event"),
        (PipelineEventType.WRITER_REFINEMENT_REQUESTED, "consume_writer_event"),
        (PipelineEventType.WRITER_COMPLETED, "consume_artist_event"),
        (PipelineEventType.ARTIST_COMPLETED, "consume_reviewer_event"),
        (PipelineEventType.REVIEWER_COMPLETED, "consume_terminal_event"),
    ],
)
def test_pipeline_events_enqueue_stage_specific_jobs_with_retry(
    monkeypatch: pytest.MonkeyPatch,
    event_type: PipelineEventType,
    handler: str,
) -> None:
    queues: list[FakeQueue] = []

    def fake_queue(name: str, *, connection: object, default_timeout: int) -> FakeQueue:
        created = FakeQueue(name, connection=connection, default_timeout=default_timeout)
        queues.append(created)
        return created

    monkeypatch.setattr(queue, "Redis", FakeRedis)
    monkeypatch.setattr(queue, "Queue", fake_queue)
    monkeypatch.setattr(queue, "Retry", FakeRetry)
    settings = Settings(
        _env_file=None,
        pipeline_event_max_attempts=5,
        pipeline_event_retry_interval_seconds=[30, 60, 120, 300],
    )
    event = PipelineEvent(
        event_id=uuid4(),
        event_type=event_type,
        event_version="1.0",
        workspace_id=uuid4(),
        run_id=uuid4(),
        correlation_id=uuid4(),
        request_id=uuid4(),
    )

    queue.RqGenerationQueue(settings).enqueue_pipeline_event(event_id=event.event_id, event=event)

    call = queues[0].calls[0]
    assert call["f"] == f"creator.workers.pipeline_events.{handler}"
    assert call["job_id"] == f"creator:rq:pipeline-event:{event.event_id}"
    assert call["unique"] is True
    assert call["meta"] == {
        "event_id": str(event.event_id),
        "event_type": event.event_type.value,
        "request_id": str(event.request_id or event.correlation_id),
        "agent_workflow_run_id": str(event.run_id),
    }
    retry = call["retry"]
    assert retry.max == 4
    assert retry.interval == [30, 60, 120, 300]
