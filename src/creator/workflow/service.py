from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from creator.config import Settings
from creator.domain.agent_workflow import AgentWorkflowStatus, HumanReviewMode, WorkflowDecision
from creator.domain.exceptions import ConflictError, EntityNotFoundError
from creator.domain.pipeline_events import (
    PipelineEvent,
    PipelineEventType,
    PipelinePayloadReference,
)
from creator.prompts.base import normalize_json_object
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord
from creator.workflow.ports import AgentWorkflowRunRecord, AgentWorkflowStepRecord


class AgentWorkflowQueue(Protocol):
    def enqueue_agent_workflow(self, *, run_id: UUID, request_id: UUID) -> object: ...

    def enqueue_pipeline_event(self, *, event_id: UUID, event: PipelineEvent) -> object: ...


class AgentWorkflowInputError(ValueError):
    """Raised when a workflow request cannot be safely executed."""


class AgentWorkflowIdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused for a different input."""


class AgentWorkflowDecisionError(ValueError):
    """Raised when a human decision is invalid for the current run."""


class AgentWorkflowQueueError(RuntimeError):
    """Compatibility error; Outbox-backed workflow acceptance no longer raises it."""


class AgentWorkflowApplication:
    """Application boundary for Agent Workflow use cases and queries."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def start(
        self,
        *,
        queue: AgentWorkflowQueue,
        settings: Settings,
        user: UserRecord,
        command: StartImageWorkflowCommand,
    ) -> AgentWorkflowRunRecord:
        return start_image_workflow(
            unit_of_work=self._unit_of_work,
            queue=queue,
            settings=settings,
            user=user,
            command=command,
        )

    def decide(
        self,
        *,
        queue: AgentWorkflowQueue,
        run_id: UUID,
        user: UserRecord,
        request_id: UUID,
        decision: WorkflowDecision,
        feedback: str | None,
    ) -> AgentWorkflowRunRecord:
        return decide_image_workflow(
            unit_of_work=self._unit_of_work,
            queue=queue,
            run_id=run_id,
            user=user,
            request_id=request_id,
            decision=decision,
            feedback=feedback,
        )

    def get_run(self, *, user_id: UUID, run_id: UUID) -> AgentWorkflowRunRecord:
        run = self._unit_of_work.agent_workflow.workflows.get_for_user(
            user_id=user_id, run_id=run_id
        )
        if run is None:
            raise EntityNotFoundError("Agent workflow not found")
        return run

    def list_steps(self, *, user_id: UUID, run_id: UUID) -> list[AgentWorkflowStepRecord]:
        steps = self._unit_of_work.agent_workflow.workflows.list_steps_for_user(
            user_id=user_id, run_id=run_id
        )
        if steps is None:
            raise EntityNotFoundError("Agent workflow not found")
        return steps


@dataclass(frozen=True, slots=True)
class StartImageWorkflowCommand:
    brand_id: UUID | None
    campaign: str | None
    persona: str | None
    quantity: int
    extra_instructions: str | None
    human_review: str
    max_refinements: int | None
    extensions: Mapping[str, object]
    idempotency_key: str
    request_id: UUID
    composition: Mapping[str, object] = field(default_factory=dict)
    planning_id: UUID | None = None
    post_structure_id: UUID | None = None


def start_image_workflow(
    *,
    unit_of_work: UnitOfWork,
    queue: AgentWorkflowQueue,
    settings: Settings,
    user: UserRecord,
    command: StartImageWorkflowCommand,
) -> AgentWorkflowRunRecord:
    if (command.planning_id is None) != (command.post_structure_id is None):
        raise AgentWorkflowInputError("planning_id and post_structure_id must be provided together")
    editorial: dict[str, object] = {}
    if command.planning_id is not None and command.post_structure_id is not None:
        planning = unit_of_work.planning.get_for_user(
            user_id=user.id, planning_id=command.planning_id
        )
        structure = unit_of_work.post_structures.get_for_user(
            user_id=user.id, post_structure_id=command.post_structure_id
        )
        if planning is None or structure is None or structure.planning_id != planning.id:
            raise EntityNotFoundError("Planning or Post Structure not found")
        brand = unit_of_work.brand.brands.get_for_user(user_id=user.id, brand_id=planning.brand_id)
        campaign = unit_of_work.campaigns.get_for_user(
            user_id=user.id, campaign_id=planning.campaign_id
        )
        persona = unit_of_work.personas.get_for_user(
            user_id=user.id, persona_id=planning.persona_id
        )
        if (
            brand is None
            or campaign is None
            or persona is None
            or structure.workspace_id != brand.workspace_id
            or campaign.workspace_id != brand.workspace_id
            or persona.brand_id != brand.id
        ):
            raise EntityNotFoundError("Planning or Post Structure not found")
        if command.brand_id is not None and command.brand_id != brand.id:
            raise EntityNotFoundError("Planning or Post Structure not found")
        editorial = {
            "planning": {
                "id": str(planning.id),
                "info": planning.info,
                "start_period": planning.start_period.isoformat()
                if planning.start_period
                else None,
                "end_period": planning.end_period.isoformat() if planning.end_period else None,
            },
            "campaign": {
                "name": campaign.name,
                "objectives": campaign.objectives,
                "audience": campaign.target_audience,
                "voice": campaign.expected_action,
            },
            "persona": {
                "name": persona.name,
                "age": persona.age_range,
                "gender": persona.gender,
                "main_goal": persona.main_goal,
                "challenge": persona.challenge,
                "interest": persona.main_goal,
                "routine": persona.routine,
                "journey": persona.journey,
                "trigger": persona.trigger_event,
            },
            "post_structure": {
                "id": str(structure.id),
                "title": structure.title,
                "objective": structure.objective,
                "big_idea": structure.big_idea,
                "main_message": structure.main_message,
                "headline": structure.headline,
                "cta": structure.image_cta,
                "art_guidance": structure.art_guiding,
                "format": structure.format,
                "ratio": structure.ratio,
                "resolution": structure.resolution,
            },
        }
    else:
        if command.brand_id is None or command.campaign is None or command.persona is None:
            raise AgentWorkflowInputError(
                "brand_id, campaign, and persona are required without Planning"
            )
        brand = unit_of_work.brand.brands.get_for_user(user_id=user.id, brand_id=command.brand_id)
    if brand is None:
        raise EntityNotFoundError("Brand not found")
    existing = unit_of_work.agent_workflow.workflows.get_by_idempotency(
        user_id=user.id,
        workspace_id=brand.workspace_id,
        idempotency_key=command.idempotency_key,
    )
    request_payload = normalize_json_object(
        {
            "brand_id": str(brand.id),
            "planning_id": str(command.planning_id) if command.planning_id else None,
            "post_structure_id": str(command.post_structure_id)
            if command.post_structure_id
            else None,
            "campaign": command.campaign,
            "persona": command.persona,
            "quantity": command.quantity,
            "extra_instructions": command.extra_instructions,
            "human_review": command.human_review,
            "max_refinements": command.max_refinements,
            "extensions": dict(command.extensions),
            "composition": dict(command.composition),
        }
    )
    fingerprint = _fingerprint(request_payload)
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise AgentWorkflowIdempotencyConflictError("Workflow idempotency key was reused")
        return existing

    input_values: dict[str, object] = {**request_payload, "editorial_context": editorial}
    if editorial:
        input_values["campaign"] = editorial["campaign"]
        input_values["persona"] = editorial["persona"]
    input_payload = normalize_json_object(input_values)

    configured_max = settings.agent_workflow_max_refinements
    max_refinements = configured_max if command.max_refinements is None else command.max_refinements
    if max_refinements > configured_max:
        raise AgentWorkflowInputError("max_refinements exceeds the configured workflow limit")

    campaign_context = editorial.get("campaign")
    planned_title = "Planned content"
    if isinstance(campaign_context, dict):
        candidate_title = campaign_context.get("name")
        if isinstance(candidate_title, str):
            planned_title = candidate_title
    content = unit_of_work.contents.add(
        workspace_id=brand.workspace_id,
        created_by_user_id=user.id,
        content_type="IMAGE",
        brand_id=brand.id,
        title=(command.campaign or planned_title)[:255],
        payload={
            "workflow_status": "PENDING",
            "workflow_input": input_payload,
            "planning_id": str(command.planning_id) if command.planning_id else None,
            "post_structure_id": str(command.post_structure_id)
            if command.post_structure_id
            else None,
        },
    )
    try:
        run = unit_of_work.agent_workflow.workflows.create_run(
            user_id=user.id,
            workspace_id=brand.workspace_id,
            content_id=content.id,
            brand_id=brand.id,
            idempotency_key=command.idempotency_key,
            request_fingerprint=fingerprint,
            input=dict(input_payload),
            human_review=HumanReviewMode(command.human_review),
            max_refinements=max_refinements,
        )
    except ConflictError as error:
        unit_of_work.rollback()
        raced = unit_of_work.agent_workflow.workflows.get_by_idempotency(
            user_id=user.id,
            workspace_id=brand.workspace_id,
            idempotency_key=command.idempotency_key,
        )
        if raced is None:
            raise
        if raced.request_fingerprint != fingerprint:
            raise AgentWorkflowIdempotencyConflictError(
                "Workflow idempotency key was reused"
            ) from error
        return raced
    started_event = PipelineEvent(
        event_id=uuid5(NAMESPACE_URL, f"creator:workflow:{run.id}:started"),
        event_type=PipelineEventType.WORKFLOW_STARTED,
        event_version="1.0",
        workspace_id=run.workspace_id,
        run_id=run.id,
        correlation_id=command.request_id,
        request_id=command.request_id,
        payload_ref=PipelinePayloadReference(input_ref="AgentWorkflowRun.input"),
    )
    unit_of_work.outbox.add(
        workspace_id=run.workspace_id,
        aggregate_id=run.id,
        event=started_event,
    )
    unit_of_work.commit()
    return run


def decide_image_workflow(
    *,
    unit_of_work: UnitOfWork,
    queue: AgentWorkflowQueue,
    run_id: UUID,
    user: UserRecord,
    request_id: UUID,
    decision: WorkflowDecision,
    feedback: str | None,
) -> AgentWorkflowRunRecord:
    run = unit_of_work.agent_workflow.workflows.get_for_user(user_id=user.id, run_id=run_id)
    if run is None:
        raise EntityNotFoundError("Agent workflow not found")
    if run.status != AgentWorkflowStatus.WAITING_FOR_HUMAN_REVIEW:
        raise AgentWorkflowDecisionError("Workflow is not waiting for human review")
    if decision == WorkflowDecision.REFINE and not feedback:
        raise AgentWorkflowDecisionError("Feedback is required to refine a workflow")
    if run.current_step == "SCENE_REVIEW":
        pending = run.input.get("pending_scenes")
        if not isinstance(pending, dict) or not pending:
            raise AgentWorkflowDecisionError("Pending scene is unavailable")
        if decision == WorkflowDecision.APPROVE:
            updated_input = dict(run.input)
            prior_approved = updated_input.get("approved_scenes")
            approved = dict(prior_approved) if isinstance(prior_approved, dict) else {}
            approved.update(pending)
            updated_input["approved_scenes"] = approved
            updated_input.pop("pending_scenes", None)
            updated_input.pop("scene_review_reason", None)
            unit_of_work.agent_workflow.workflows.update_input(run_id, updated_input)
            updated = unit_of_work.agent_workflow.workflows.transition(
                run_id, AgentWorkflowStatus.REFINING, current_step="ARTIST"
            )
            unit_of_work.outbox.add(
                workspace_id=run.workspace_id,
                aggregate_id=run.id,
                event=PipelineEvent(
                    event_id=uuid5(
                        NAMESPACE_URL,
                        f"creator:workflow:{run.id}:scene-approved:{run.refinement_count}",
                    ),
                    event_type=PipelineEventType.WRITER_COMPLETED,
                    event_version="1.0",
                    workspace_id=run.workspace_id,
                    run_id=run.id,
                    correlation_id=request_id,
                    request_id=request_id,
                    payload_ref=PipelinePayloadReference(
                        input_ref="AgentWorkflowRun.input.approved_scenes",
                        predecessor_role="WRITER",
                        attempt=min(run.refinement_count + 1, 5),
                    ),
                ),
            )
            unit_of_work.commit()
            return updated
        if decision == WorkflowDecision.REJECT:
            updated = unit_of_work.agent_workflow.workflows.transition(
                run_id, AgentWorkflowStatus.REJECTED, current_step="DELIVERY"
            )
            unit_of_work.commit()
            return updated
    if decision == WorkflowDecision.APPROVE:
        updated = unit_of_work.agent_workflow.workflows.transition(
            run_id, AgentWorkflowStatus.COMPLETED, current_step="DELIVERY"
        )
        unit_of_work.commit()
        return updated
    if decision == WorkflowDecision.REJECT:
        updated = unit_of_work.agent_workflow.workflows.transition(
            run_id, AgentWorkflowStatus.REJECTED, current_step="DELIVERY"
        )
        unit_of_work.commit()
        return updated

    if run.refinement_count >= run.max_refinements:
        raise AgentWorkflowDecisionError("Maximum workflow refinements reached")
    updated_input = dict(run.input)
    updated_input["human_feedback"] = feedback
    unit_of_work.agent_workflow.workflows.update_input(run_id, updated_input)
    updated = unit_of_work.agent_workflow.workflows.transition(
        run_id,
        AgentWorkflowStatus.REFINING,
        current_step="WRITER",
        refinement_count=run.refinement_count + 1,
    )
    unit_of_work.outbox.add(
        workspace_id=updated.workspace_id,
        aggregate_id=updated.id,
        event=PipelineEvent(
            event_id=uuid5(
                NAMESPACE_URL,
                f"creator:workflow:{updated.id}:refinement:{updated.refinement_count}",
            ),
            event_type=PipelineEventType.WRITER_REFINEMENT_REQUESTED,
            event_version="1.0",
            workspace_id=updated.workspace_id,
            run_id=updated.id,
            correlation_id=request_id,
            request_id=request_id,
            payload_ref=PipelinePayloadReference(
                feedback_ref="AgentWorkflowRun.input.human_feedback",
                predecessor_role="REVIEWER",
                attempt=min(updated.refinement_count + 1, 5),
            ),
        ),
    )
    unit_of_work.commit()
    return updated


def _fingerprint(payload: Mapping[str, object]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
