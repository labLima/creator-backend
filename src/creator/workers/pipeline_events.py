from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from creator.config import get_settings
from creator.domain.agent_workflow import AgentWorkflowStatus
from creator.domain.pipeline_events import PipelineEvent, PipelineEventType
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.infrastructure.runtime.observability import correlation_context
from creator.infrastructure.runtime.queue import RqGenerationQueue
from creator.services.agents.event_publisher import OutboxPublisher
from creator.workers.agent_workflow import run_pipeline_stage

logger = logging.getLogger(__name__)


class InvalidPipelineEvent(RuntimeError):
    """Raised when a durable event cannot safely be consumed."""


def consume_business_event(payload: dict[str, Any]) -> None:
    _consume_stage(payload, {PipelineEventType.WORKFLOW_STARTED}, "BUSINESS")


def consume_planner_event(payload: dict[str, Any]) -> None:
    _consume_stage(payload, {PipelineEventType.BUSINESS_COMPLETED}, "PLANNER")


def consume_writer_event(payload: dict[str, Any]) -> None:
    _consume_stage(
        payload,
        {
            PipelineEventType.PLANNER_COMPLETED,
            PipelineEventType.WRITER_REFINEMENT_REQUESTED,
        },
        "WRITER",
    )


def consume_artist_event(payload: dict[str, Any]) -> None:
    _consume_stage(payload, {PipelineEventType.WRITER_COMPLETED}, "ARTIST")


def consume_reviewer_event(payload: dict[str, Any]) -> None:
    _consume_stage(payload, {PipelineEventType.ARTIST_COMPLETED}, "REVIEWER")


def consume_terminal_event(payload: dict[str, Any]) -> None:
    _consume(payload, {PipelineEventType.REVIEWER_COMPLETED}, lambda _event: None)


def handle_pipeline_event(payload: dict[str, Any]) -> None:
    """Compatibility dispatcher for jobs published before stage-specific routing."""
    event = PipelineEvent.model_validate(payload)
    handler = {
        PipelineEventType.WORKFLOW_STARTED: consume_business_event,
        PipelineEventType.BUSINESS_COMPLETED: consume_planner_event,
        PipelineEventType.PLANNER_COMPLETED: consume_writer_event,
        PipelineEventType.WRITER_REFINEMENT_REQUESTED: consume_writer_event,
        PipelineEventType.WRITER_COMPLETED: consume_artist_event,
        PipelineEventType.ARTIST_COMPLETED: consume_reviewer_event,
        PipelineEventType.REVIEWER_COMPLETED: consume_terminal_event,
    }[event.event_type]
    handler(event.model_dump(mode="json"))


def _consume_stage(
    payload: dict[str, Any], expected_types: set[PipelineEventType], stage: str
) -> None:
    _consume(
        payload,
        expected_types,
        lambda event: _run_stage_with_context(event, stage),
    )


def _run_stage_with_context(event: PipelineEvent, stage: str) -> None:
    request_id = event.request_id or event.correlation_id
    with correlation_context(
        request_id=request_id,
        job_id=event.run_id,
        correlation_id=event.correlation_id,
    ):
        run_pipeline_stage(
            str(event.run_id),
            str(request_id),
            stage=stage,
            source_event_id=event.event_id,
        )


def _consume(
    payload: dict[str, Any],
    expected_types: set[PipelineEventType],
    execute: Callable[[PipelineEvent], None],
) -> None:
    event = PipelineEvent.model_validate(payload)
    if event.event_type not in expected_types:
        _dead_letter(event, f"Unexpected event type {event.event_type.value}")
        return

    settings = get_settings()
    lease_seconds = (
        settings.agent_workflow_job_timeout_seconds + settings.pipeline_event_lease_grace_seconds
    )
    try:
        with SqlAlchemyUnitOfWork() as unit_of_work:
            record = unit_of_work.outbox.claim_for_consumption(
                event.event_id, lease_seconds=lease_seconds
            )
            if record is None:
                return
            persisted = PipelineEvent.model_validate(record.payload)
            run = unit_of_work.agent_workflows.get_internal(event.run_id)
            if persisted != event:
                raise InvalidPipelineEvent("Queued payload differs from the durable event")
            if record.aggregate_id != event.run_id:
                raise InvalidPipelineEvent("Event aggregate does not match its Agent Workflow")
            if run is None:
                raise InvalidPipelineEvent("Agent Workflow does not exist")
            if run.workspace_id != event.workspace_id or record.workspace_id != event.workspace_id:
                raise InvalidPipelineEvent("Event is outside the Agent Workflow Workspace")
            _validate_predecessor(unit_of_work, event)
            unit_of_work.commit()
        execute(event)
    except InvalidPipelineEvent as error:
        _dead_letter(event, str(error))
        return
    except Exception as error:
        _record_consumer_failure(event, error)
        return

    with SqlAlchemyUnitOfWork() as unit_of_work:
        unit_of_work.outbox.mark_consumed(event.event_id)
        unit_of_work.commit()


def _validate_predecessor(unit_of_work: SqlAlchemyUnitOfWork, event: PipelineEvent) -> None:
    if event.predecessor_step_id is None:
        return
    steps = unit_of_work.agent_workflows.list_steps_internal(event.run_id)
    predecessor = next((step for step in steps if step.id == event.predecessor_step_id), None)
    if predecessor is None or predecessor.workspace_id != event.workspace_id:
        raise InvalidPipelineEvent("Event predecessor is missing or cross-Workspace")
    if event.input_hash is not None and predecessor.output_hash != event.input_hash:
        raise InvalidPipelineEvent("Event predecessor hash is stale")


def _record_consumer_failure(event: PipelineEvent, error: Exception) -> None:
    settings = get_settings()
    with SqlAlchemyUnitOfWork() as unit_of_work:
        dead_lettered = unit_of_work.outbox.mark_consumer_failed(
            event.event_id,
            str(error),
            max_attempts=settings.pipeline_event_max_attempts,
            retry_intervals=tuple(settings.pipeline_event_retry_interval_seconds),
        )
        if dead_lettered:
            run = unit_of_work.agent_workflows.get_internal(event.run_id)
            if run is not None and run.status not in {
                AgentWorkflowStatus.COMPLETED,
                AgentWorkflowStatus.REJECTED,
                AgentWorkflowStatus.FAILED,
            }:
                unit_of_work.agent_workflows.transition(
                    event.run_id,
                    AgentWorkflowStatus.FAILED,
                    current_step=run.current_step,
                    failure_code="PIPELINE_EVENT_DEAD_LETTERED",
                    failure_message="Agent Workflow stage exhausted its retry policy",
                )
        unit_of_work.commit()
    if not dead_lettered:
        raise error
    logger.error(
        "pipeline_event_dead_lettered",
        extra={"event_id": str(event.event_id), "event_type": event.event_type.value},
    )


def _dead_letter(event: PipelineEvent, reason: str) -> None:
    with SqlAlchemyUnitOfWork() as unit_of_work:
        unit_of_work.outbox.dead_letter(event.event_id, phase="VALIDATE", reason=reason)
        run = unit_of_work.agent_workflows.get_internal(event.run_id)
        if run is not None and run.status not in {
            AgentWorkflowStatus.COMPLETED,
            AgentWorkflowStatus.REJECTED,
            AgentWorkflowStatus.FAILED,
        }:
            unit_of_work.agent_workflows.transition(
                event.run_id,
                AgentWorkflowStatus.FAILED,
                current_step=run.current_step,
                failure_code="PIPELINE_EVENT_INVALID",
                failure_message="Agent Workflow event failed validation",
            )
        unit_of_work.commit()


def publish_pipeline_outbox_once(limit: int = 50) -> int:
    settings = get_settings()
    with SqlAlchemyUnitOfWork() as unit_of_work:
        return OutboxPublisher(unit_of_work, RqGenerationQueue(settings), settings).publish_once(
            limit=limit
        )
