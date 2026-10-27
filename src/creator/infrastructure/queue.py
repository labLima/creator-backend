from typing import Final
from uuid import UUID

from redis import Redis
from rq import Queue, Retry

from creator.config import Settings, get_settings
from creator.domain.pipeline_events import PipelineEvent, PipelineEventType

_PIPELINE_HANDLERS: Final = {
    PipelineEventType.WORKFLOW_STARTED: "creator.workers.pipeline_events.consume_business_event",
    PipelineEventType.BUSINESS_COMPLETED: "creator.workers.pipeline_events.consume_planner_event",
    PipelineEventType.PLANNER_COMPLETED: "creator.workers.pipeline_events.consume_writer_event",
    PipelineEventType.WRITER_REFINEMENT_REQUESTED: (
        "creator.workers.pipeline_events.consume_writer_event"
    ),
    PipelineEventType.WRITER_COMPLETED: "creator.workers.pipeline_events.consume_artist_event",
    PipelineEventType.ARTIST_COMPLETED: "creator.workers.pipeline_events.consume_reviewer_event",
    PipelineEventType.REVIEWER_COMPLETED: "creator.workers.pipeline_events.consume_terminal_event",
}


class RqGenerationQueue:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection = Redis.from_url(settings.redis_url)
        self._queue = Queue(
            settings.generation_queue_name,
            connection=self._connection,
            default_timeout=settings.image_generation_job_timeout_seconds,
        )

    @property
    def name(self) -> str:
        return self._queue.name

    def enqueue_image_generation(self, *, job_id: UUID, request_id: UUID) -> object:
        retry_intervals = list(self._settings.image_generation_retry_interval_seconds)
        return self._queue.enqueue(
            "creator.workers.image_generation.run_image_generation",
            str(job_id),
            str(request_id),
            job_id=f"creator:rq:image-generation:{job_id}",
            job_timeout=self._settings.image_generation_job_timeout_seconds,
            retry=Retry(
                max=max(self._settings.image_generation_job_max_attempts - 1, 0),
                interval=retry_intervals,
            ),
            meta={
                "request_id": str(request_id),
                "generation_job_id": str(job_id),
            },
        )

    def enqueue_agent_workflow(self, *, run_id: UUID, request_id: UUID) -> object:
        return self._queue.enqueue(
            "creator.workers.agent_workflow.run_image_agent_workflow",
            str(run_id),
            str(request_id),
            job_id=f"creator:rq:agent-workflow:{run_id}",
            job_timeout=self._settings.agent_workflow_job_timeout_seconds,
            meta={"request_id": str(request_id), "agent_workflow_run_id": str(run_id)},
        )

    def enqueue_pipeline_event(self, *, event_id: UUID, event: PipelineEvent) -> object:
        retry_intervals = list(self._settings.pipeline_event_retry_interval_seconds)
        return self._queue.enqueue(
            _PIPELINE_HANDLERS[event.event_type],
            event.model_dump(mode="json"),
            job_id=f"creator:rq:pipeline-event:{event_id}",
            job_timeout=self._settings.agent_workflow_job_timeout_seconds,
            retry=Retry(
                max=max(self._settings.pipeline_event_max_attempts - 1, 0),
                interval=retry_intervals,
            ),
            unique=True,
            meta={"event_id": str(event_id), "event_type": event.event_type.value},
        )


def get_generation_queue() -> RqGenerationQueue:
    return RqGenerationQueue(get_settings())
