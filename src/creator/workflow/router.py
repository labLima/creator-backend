"""HTTP routes for the workflow capability.

The image workflow endpoints live under `/api/v1/generations/...` for contract
compatibility; ownership and business logic belong to Agent Workflow.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_generation_queue,
    get_uow,
)
from creator.api.errors import not_found
from creator.api.responses import request_id_for, success_response
from creator.api.serializers import _agent_workflow_data, _agent_workflow_step_data
from creator.config import Settings, get_settings
from creator.domain.agent_workflow import WorkflowDecision
from creator.domain.exceptions import EntityNotFoundError
from creator.generation.ports import GenerationQueue
from creator.generation.schemas import (
    ImageWorkflowDecisionRequest,
    ImageWorkflowRequest,
)
from creator.repositories import UserRecord
from creator.uow import UnitOfWork
from creator.workflow.service import (
    AgentWorkflowDecisionError,
    AgentWorkflowIdempotencyConflictError,
    AgentWorkflowInputError,
    StartImageWorkflowCommand,
    decide_image_workflow,
    start_image_workflow,
)

router = APIRouter()


@router.post("/api/v1/generations/image-workflows", tags=["Generations"])
def create_image_workflow(
    payload: ImageWorkflowRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        run = start_image_workflow(
            unit_of_work=unit_of_work,
            queue=queue,
            settings=settings,
            user=current_user,
            command=StartImageWorkflowCommand(
                brand_id=payload.brand_id,
                campaign=payload.campaign,
                persona=payload.persona,
                quantity=payload.quantity,
                extra_instructions=payload.extra_instructions,
                human_review=payload.human_review,
                max_refinements=payload.max_refinements,
                extensions=payload.extensions,
                idempotency_key=idempotency_key,
                request_id=request_id_for(request),
            ),
        )
    except EntityNotFoundError as error:
        raise HTTPException(
            status_code=404, detail={"code": "BRAND_NOT_FOUND", "message": "Brand not found"}
        ) from error
    except AgentWorkflowIdempotencyConflictError as error:
        raise HTTPException(
            status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": str(error)}
        ) from error
    except AgentWorkflowInputError as error:
        raise HTTPException(
            status_code=422, detail={"code": "WORKFLOW_INPUT_INVALID", "message": str(error)}
        ) from error
    return success_response(_agent_workflow_data(run), request, status_code=202)


@router.get("/api/v1/generations/image-workflows/{id}", tags=["Generations"])
def get_image_workflow(
    workflow_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    run = unit_of_work.agent_workflows.get_for_user(user_id=current_user.id, run_id=workflow_id)
    if run is None:
        raise not_found("Agent workflow")
    return success_response(_agent_workflow_data(run), request)


@router.get("/api/v1/generations/image-workflows/{id}/steps", tags=["Generations"])
def list_image_workflow_steps(
    workflow_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    steps = unit_of_work.agent_workflows.list_steps_for_user(
        user_id=current_user.id, run_id=workflow_id
    )
    if steps is None:
        raise not_found("Agent workflow")
    return success_response({"items": [_agent_workflow_step_data(step) for step in steps]}, request)


@router.post("/api/v1/generations/image-workflows/{id}/decision", tags=["Generations"])
def decide_image_workflow_route(
    workflow_id: Annotated[UUID, Path(alias="id")],
    payload: ImageWorkflowDecisionRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        run = decide_image_workflow(
            unit_of_work=unit_of_work,
            queue=queue,
            run_id=workflow_id,
            user=current_user,
            request_id=request_id_for(request),
            decision=WorkflowDecision(payload.decision),
            feedback=payload.feedback,
        )
    except EntityNotFoundError as error:
        raise not_found("Agent workflow") from error
    except AgentWorkflowDecisionError as error:
        raise HTTPException(
            status_code=409, detail={"code": "WORKFLOW_DECISION_INVALID", "message": str(error)}
        ) from error
    return success_response(_agent_workflow_data(run), request)
