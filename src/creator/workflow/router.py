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
    get_agent_workflow_application,
    get_current_user,
    get_generation_queue,
)
from creator.api.errors import not_found
from creator.api.responses import request_id_for, success_response
from creator.api.serializers import _agent_workflow_data, _agent_workflow_step_data
from creator.config import Settings, get_settings
from creator.domain.agent_workflow import WorkflowDecision
from creator.domain.exceptions import EntityNotFoundError
from creator.generation.ports import GenerationQueue
from creator.user.ports import UserRecord
from creator.workflow.schemas import (
    ImageWorkflowDecisionRequest,
    ImageWorkflowRequest,
)
from creator.workflow.service import (
    AgentWorkflowApplication,
    AgentWorkflowDecisionError,
    AgentWorkflowIdempotencyConflictError,
    AgentWorkflowInputError,
    StartImageWorkflowCommand,
)

router = APIRouter()


@router.post(
    "/api/v1/generations/image-workflows",
    tags=["Generations"],
    operation_id="createImageAgentWorkflow",
    responses={
        "404": {"$ref": "#/components/responses/NotFound"},
        "409": {"$ref": "#/components/responses/Conflict"},
        "422": {
            "$ref": "#/components/responses/ValidationFailed",
            "x-error-codes": ["VALIDATION_FAILED", "WORKFLOW_INPUT_INVALID"],
        },
    },
)
def create_image_workflow(
    payload: ImageWorkflowRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    application: Annotated[AgentWorkflowApplication, Depends(get_agent_workflow_application)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        run = application.start(
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


@router.get(
    "/api/v1/generations/image-workflows/{id}",
    tags=["Generations"],
    operation_id="getImageAgentWorkflow",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_image_workflow(
    workflow_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[AgentWorkflowApplication, Depends(get_agent_workflow_application)],
) -> JSONResponse:
    try:
        run = application.get_run(user_id=current_user.id, run_id=workflow_id)
    except EntityNotFoundError as error:
        raise not_found("Agent workflow") from error
    return success_response(_agent_workflow_data(run), request)


@router.get(
    "/api/v1/generations/image-workflows/{id}/steps",
    tags=["Generations"],
    operation_id="listImageAgentWorkflowSteps",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def list_image_workflow_steps(
    workflow_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[AgentWorkflowApplication, Depends(get_agent_workflow_application)],
) -> JSONResponse:
    try:
        steps = application.list_steps(user_id=current_user.id, run_id=workflow_id)
    except EntityNotFoundError as error:
        raise not_found("Agent workflow") from error
    return success_response({"items": [_agent_workflow_step_data(step) for step in steps]}, request)


@router.post(
    "/api/v1/generations/image-workflows/{id}/decision",
    tags=["Generations"],
    operation_id="decideImageAgentWorkflow",
    responses={
        "404": {"$ref": "#/components/responses/NotFound"},
        "409": {"$ref": "#/components/responses/Conflict"},
        "422": {
            "$ref": "#/components/responses/ValidationFailed",
            "x-error-codes": ["VALIDATION_FAILED", "WORKFLOW_INPUT_INVALID"],
        },
    },
)
def decide_image_workflow_route(
    workflow_id: Annotated[UUID, Path(alias="id")],
    payload: ImageWorkflowDecisionRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[AgentWorkflowApplication, Depends(get_agent_workflow_application)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        run = application.decide(
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
