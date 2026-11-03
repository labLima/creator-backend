"""SQLAlchemy implementation of the workflow persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

import creator.workflow.models as workflow_models
from creator.core.types import JsonObject
from creator.domain.agent_workflow import (
    AgentWorkflowStatus,
    AgentWorkflowStepRole,
    AgentWorkflowStepStatus,
    HumanReviewMode,
    can_transition_agent_workflow,
    can_transition_agent_workflow_step,
)
from creator.domain.exceptions import EntityNotFoundError, InvalidStateTransitionError
from creator.domain.pipeline_events import PipelineEvent
from creator.infrastructure.persistence.sql import as_datetime as _datetime
from creator.infrastructure.persistence.sql import as_optional_datetime as _optional_datetime
from creator.infrastructure.persistence.sql import flush_or_raise
from creator.infrastructure.persistence.sql import json_object as _json
from creator.infrastructure.persistence.sql import now as _now
from creator.infrastructure.persistence.sql import scoped_resource_select as _scoped_resource_select
from creator.infrastructure.persistence.sql import (
    user_has_workspace_role as _user_has_workspace_role,
)
from creator.workflow import models as workflow_tables
from creator.workflow.ports import (
    AgentWorkflowRunRecord,
    AgentWorkflowStepRecord,
    OutboxEventRecord,
)


def _record(row: workflow_models.OutboxEvent) -> OutboxEventRecord:
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


class SqlAlchemyOutboxRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, workspace_id: UUID, aggregate_id: UUID, event: PipelineEvent) -> UUID:
        row = workflow_models.OutboxEvent(
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
            select(workflow_models.OutboxEvent.id)
            .where(
                workflow_models.OutboxEvent.published_at.is_(None),
                workflow_models.OutboxEvent.dead_lettered_at.is_(None),
                workflow_models.OutboxEvent.available_at <= now,
                (workflow_models.OutboxEvent.claimed_at.is_(None))
                | (workflow_models.OutboxEvent.claimed_at < stale_before),
            )
            .order_by(workflow_models.OutboxEvent.created_at.asc())
            .limit(limit)
        )
        self._session.execute(
            update(workflow_models.OutboxEvent)
            .where(workflow_models.OutboxEvent.id.in_(candidate_ids))
            .values(
                claimed_at=now,
                claimed_by=claim_token,
                attempts=workflow_models.OutboxEvent.attempts + 1,
            )
            .execution_options(synchronize_session=False)
        )
        rows = self._session.scalars(
            select(workflow_models.OutboxEvent)
            .where(
                workflow_models.OutboxEvent.claimed_by == claim_token,
                workflow_models.OutboxEvent.published_at.is_(None),
            )
            .order_by(workflow_models.OutboxEvent.created_at.asc())
        ).all()
        return [_record(row) for row in rows]

    def mark_published(self, event_id: UUID) -> None:
        row = self._session.get(workflow_models.OutboxEvent, event_id)
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
        row = self._session.get(workflow_models.OutboxEvent, event_id)
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
            update(workflow_models.OutboxEvent)
            .where(
                workflow_models.OutboxEvent.id == event_id,
                workflow_models.OutboxEvent.consumed_at.is_(None),
                workflow_models.OutboxEvent.dead_lettered_at.is_(None),
                (workflow_models.OutboxEvent.consumer_claimed_at.is_(None))
                | (workflow_models.OutboxEvent.consumer_claimed_at < stale_before),
            )
            .values(
                consumer_claimed_at=now,
                consumer_claimed_by=claim_token,
                consumer_attempts=workflow_models.OutboxEvent.consumer_attempts + 1,
            )
            .execution_options(synchronize_session=False)
        )
        row = self._session.scalars(
            select(workflow_models.OutboxEvent).where(
                workflow_models.OutboxEvent.id == event_id,
                workflow_models.OutboxEvent.consumer_claimed_by == claim_token,
            )
        ).one_or_none()
        return _record(row) if row is not None else None

    def mark_consumed(self, event_id: UUID) -> None:
        row = self._session.get(workflow_models.OutboxEvent, event_id)
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
        row = self._session.get(workflow_models.OutboxEvent, event_id)
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
        row = self._session.get(workflow_models.OutboxEvent, event_id)
        if row is not None:
            self._set_dead_letter(row, phase=phase, reason=reason)

    def exists(self, event_id: UUID) -> bool:
        return self._session.get(workflow_models.OutboxEvent, event_id) is not None

    @staticmethod
    def _set_dead_letter(row: workflow_models.OutboxEvent, *, phase: str, reason: str) -> None:
        row.dead_lettered_at = datetime.now(UTC)
        row.dead_letter_phase = phase[:32]
        row.dead_letter_reason = reason[:2_000]
        row.claimed_at = None
        row.claimed_by = None
        row.consumer_claimed_at = None
        row.consumer_claimed_by = None


def _agent_workflow_run_record(row: workflow_tables.AgentWorkflowRun) -> AgentWorkflowRunRecord:
    return AgentWorkflowRunRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        content_id=row.content_id,
        brand_id=row.brand_id,
        requested_by_user_id=row.requested_by_user_id,
        idempotency_key=row.idempotency_key,
        request_fingerprint=row.request_fingerprint,
        status=row.status,
        human_review=row.human_review,
        max_refinements=row.max_refinements,
        refinement_count=row.refinement_count,
        current_step=row.current_step,
        input=_json(row.input_json),
        final_image_ids=[str(value) for value in (row.final_image_ids or [])],
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        completed_at=_optional_datetime(row.completed_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


def _agent_workflow_step_record(row: workflow_tables.AgentWorkflowStep) -> AgentWorkflowStepRecord:
    return AgentWorkflowStepRecord(
        id=row.id,
        run_id=row.run_id,
        workspace_id=row.workspace_id,
        sequence_number=row.sequence_number,
        role=row.role,
        status=row.status,
        attempt=row.attempt,
        input=_json(row.input_json),
        output=_json(row.output_json),
        prompt=row.prompt,
        prompt_template_id=row.prompt_template_id,
        prompt_template_version=row.prompt_template_version,
        input_hash=row.input_hash,
        output_hash=row.output_hash,
        schema_name=row.schema_name,
        schema_version=row.schema_version,
        predecessor_step_id=row.predecessor_step_id,
        correlation_id=row.correlation_id,
        source_event_id=row.source_event_id,
        stage_item=row.stage_item,
        provider=row.provider,
        model=row.model,
        decision=row.decision,
        error_code=row.error_code,
        error_message=row.error_message,
        started_at=_optional_datetime(row.started_at),
        completed_at=_optional_datetime(row.completed_at),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


class SqlAlchemyAgentWorkflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_run(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        content_id: UUID,
        brand_id: UUID,
        idempotency_key: str,
        request_fingerprint: str,
        input: JsonObject,
        human_review: HumanReviewMode,
        max_refinements: int,
    ) -> AgentWorkflowRunRecord:
        if not _user_has_workspace_role(
            self._session, user_id=user_id, workspace_id=workspace_id, minimum_role="editor"
        ):
            raise EntityNotFoundError("Workspace not found")
        row = workflow_tables.AgentWorkflowRun(
            workspace_id=workspace_id,
            content_id=content_id,
            brand_id=brand_id,
            requested_by_user_id=user_id,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            human_review=human_review,
            max_refinements=max_refinements,
            input_json=_json(input),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _agent_workflow_run_record(row)

    def get_for_user(self, *, user_id: UUID, run_id: UUID) -> AgentWorkflowRunRecord | None:
        row = self._session.scalars(
            self._scoped_select(user_id).where(workflow_tables.AgentWorkflowRun.id == run_id)
        ).one_or_none()
        return _agent_workflow_run_record(row) if row else None

    def get_by_idempotency(
        self, *, user_id: UUID, workspace_id: UUID, idempotency_key: str
    ) -> AgentWorkflowRunRecord | None:
        statement = self._scoped_select(user_id).where(
            workflow_tables.AgentWorkflowRun.workspace_id == workspace_id,
            workflow_tables.AgentWorkflowRun.idempotency_key == idempotency_key,
        )
        row = self._session.scalars(statement).one_or_none()
        return _agent_workflow_run_record(row) if row else None

    def get_internal(self, run_id: UUID) -> AgentWorkflowRunRecord | None:
        row = self._session.scalars(
            select(workflow_tables.AgentWorkflowRun).where(
                workflow_tables.AgentWorkflowRun.id == run_id,
                workflow_tables.AgentWorkflowRun.deleted_at.is_(None),
            )
        ).one_or_none()
        return _agent_workflow_run_record(row) if row else None

    def list_steps_for_user(
        self, *, user_id: UUID, run_id: UUID
    ) -> list[AgentWorkflowStepRecord] | None:
        run = self.get_for_user(user_id=user_id, run_id=run_id)
        if run is None:
            return None
        rows = self._session.scalars(
            select(workflow_tables.AgentWorkflowStep)
            .where(
                workflow_tables.AgentWorkflowStep.run_id == run_id,
                workflow_tables.AgentWorkflowStep.workspace_id == run.workspace_id,
                workflow_tables.AgentWorkflowStep.deleted_at.is_(None),
            )
            .order_by(
                workflow_tables.AgentWorkflowStep.sequence_number.asc(),
                workflow_tables.AgentWorkflowStep.attempt.asc(),
            )
        ).all()
        return [_agent_workflow_step_record(row) for row in rows]

    def list_steps_internal(self, run_id: UUID) -> list[AgentWorkflowStepRecord]:
        rows = self._session.scalars(
            select(workflow_tables.AgentWorkflowStep)
            .where(
                workflow_tables.AgentWorkflowStep.run_id == run_id,
                workflow_tables.AgentWorkflowStep.deleted_at.is_(None),
            )
            .order_by(
                workflow_tables.AgentWorkflowStep.sequence_number.asc(),
                workflow_tables.AgentWorkflowStep.attempt.asc(),
            )
        ).all()
        return [_agent_workflow_step_record(row) for row in rows]

    def add_step(
        self,
        *,
        run_id: UUID,
        workspace_id: UUID,
        sequence_number: int,
        role: AgentWorkflowStepRole,
        attempt: int,
        input: JsonObject,
        source_event_id: UUID | None = None,
        stage_item: int = 0,
    ) -> AgentWorkflowStepRecord:
        run = self._session.scalars(
            select(workflow_tables.AgentWorkflowRun)
            .where(
                workflow_tables.AgentWorkflowRun.id == run_id,
                workflow_tables.AgentWorkflowRun.workspace_id == workspace_id,
                workflow_tables.AgentWorkflowRun.deleted_at.is_(None),
            )
            .with_for_update()
        ).one_or_none()
        if run is None:
            raise EntityNotFoundError("Agent workflow not found")
        row = workflow_tables.AgentWorkflowStep(
            run_id=run_id,
            workspace_id=workspace_id,
            sequence_number=sequence_number,
            role=role,
            attempt=attempt,
            input_json=_json(input),
            source_event_id=source_event_id,
            stage_item=stage_item,
            status=AgentWorkflowStepStatus.RUNNING,
            started_at=_now(),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _agent_workflow_step_record(row)

    def complete_step(
        self,
        step_id: UUID,
        *,
        output: JsonObject,
        prompt: str | None = None,
        prompt_template_id: str | None = None,
        prompt_template_version: str | None = None,
        input_hash: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        decision: str | None = None,
        output_hash: str | None = None,
        schema_name: str | None = None,
        schema_version: str | None = None,
        predecessor_step_id: UUID | None = None,
        correlation_id: UUID | None = None,
    ) -> AgentWorkflowStepRecord:
        row = self._session.scalars(
            select(workflow_tables.AgentWorkflowStep).where(
                workflow_tables.AgentWorkflowStep.id == step_id,
                workflow_tables.AgentWorkflowStep.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Agent workflow step not found")
        if not can_transition_agent_workflow_step(row.status, AgentWorkflowStepStatus.COMPLETED):
            raise InvalidStateTransitionError(f"Cannot complete step in {row.status} state")
        row.status = AgentWorkflowStepStatus.COMPLETED
        row.output_json = _json(output)
        row.prompt = prompt
        row.prompt_template_id = prompt_template_id
        row.prompt_template_version = prompt_template_version
        row.input_hash = input_hash
        row.output_hash = output_hash
        row.schema_name = schema_name
        row.schema_version = schema_version
        row.predecessor_step_id = predecessor_step_id
        row.correlation_id = correlation_id
        row.provider = provider
        row.model = model
        row.decision = decision
        row.completed_at = _now()
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _agent_workflow_step_record(row)

    def fail_step(self, step_id: UUID, *, error_code: str, error_message: str) -> None:
        row = self._session.scalars(
            select(workflow_tables.AgentWorkflowStep).where(
                workflow_tables.AgentWorkflowStep.id == step_id
            )
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Agent workflow step not found")
        if not can_transition_agent_workflow_step(row.status, AgentWorkflowStepStatus.FAILED):
            raise InvalidStateTransitionError(f"Cannot fail step in {row.status} state")
        row.status = AgentWorkflowStepStatus.FAILED
        row.error_code = error_code
        row.error_message = error_message[:2_000]
        row.completed_at = _now()
        row.updated_at = _now()
        flush_or_raise(self._session)

    def transition(
        self,
        run_id: UUID,
        target: AgentWorkflowStatus,
        *,
        current_step: str | None = None,
        refinement_count: int | None = None,
        final_image_ids: list[str] | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> AgentWorkflowRunRecord:
        row = self._session.scalars(
            select(workflow_tables.AgentWorkflowRun)
            .where(
                workflow_tables.AgentWorkflowRun.id == run_id,
                workflow_tables.AgentWorkflowRun.deleted_at.is_(None),
            )
            .with_for_update()
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Agent workflow not found")
        if not can_transition_agent_workflow(row.status, target):
            raise InvalidStateTransitionError(f"Cannot transition {row.status} to {target}")
        row.status = target
        if current_step is not None:
            row.current_step = current_step
        if refinement_count is not None:
            row.refinement_count = refinement_count
        if final_image_ids is not None:
            row.final_image_ids = list(final_image_ids)
        if failure_code is not None:
            row.failure_code = failure_code
        if failure_message is not None:
            row.failure_message = failure_message[:2_000]
        if target == AgentWorkflowStatus.COMPLETED:
            row.completed_at = _now()
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _agent_workflow_run_record(row)

    def update_input(self, run_id: UUID, input: JsonObject) -> AgentWorkflowRunRecord:
        row = self._session.scalars(
            select(workflow_tables.AgentWorkflowRun).where(
                workflow_tables.AgentWorkflowRun.id == run_id,
                workflow_tables.AgentWorkflowRun.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Agent workflow not found")
        row.input_json = _json(input)
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _agent_workflow_run_record(row)

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_select(user_id, workflow_tables.AgentWorkflowRun)
