"""HTTP routes for the generation capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_generation_queue,
    get_storage_provider,
    get_uow,
)
from creator.api.dtos import (
    GenerateImageRequest,
    GenerationCreateRequest,
    GenerationUpdateRequest,
    ImageWorkflowDecisionRequest,
    ImageWorkflowRequest,
    RegenerateImageRequest,
)
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    page_payload,
    request_id_for,
    success_response,
)
from creator.api.serializers import (
    _agent_workflow_data,
    _agent_workflow_step_data,
    _generated_image_data,
    _generation_data,
    _image_generation_status_data,
)
from creator.application.agent_image_workflow import (
    AgentWorkflowDecisionError,
    AgentWorkflowIdempotencyConflictError,
    AgentWorkflowInputError,
    StartImageWorkflowCommand,
    decide_image_workflow,
    start_image_workflow,
)
from creator.application.image_generation import (
    GenerationQueue,
    IdempotencyConflictError,
    QueueEnqueueError,
    submit_image_generation,
    submit_image_regeneration,
)
from creator.application.unit_of_work import UnitOfWork
from creator.config import Settings, get_settings
from creator.core.pagination import page_request
from creator.domain.agent_workflow import WorkflowDecision
from creator.domain.exceptions import EntityNotFoundError
from creator.domain.generation import GenerationJobStatus
from creator.repositories import (
    UserRecord,
)
from creator.services.storage.provider import StorageProvider, StorageUrlError

router = APIRouter()


@router.get("/api/v1/generations", tags=["Generations"])
def list_generations(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
    content_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    generations = unit_of_work.generations.list_for_user(
        user_id=current_user.id,
        workspace_id=workspace_id,
        content_id=content_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(generations, _generation_data), request)


@router.post("/api/v1/generations", tags=["Generations"])
def create_generation(
    payload: GenerationCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    generation = unit_of_work.generations.add(
        workspace_id=payload.workspace_id,
        content_id=payload.content_id,
        requested_by_user_id=current_user.id,
        generation_type=payload.type,
        brand_id=payload.brand_id,
        project_id=payload.project_id,
        model=payload.model,
        prompt=payload.prompt,
        parameters=payload.parameters,
    )
    unit_of_work.commit()
    return success_response(_generation_data(generation), request, status_code=201)


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


@router.get("/api/v1/generations/{id}", tags=["Generations"])
def get_generation(
    generation_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    generation = unit_of_work.generations.get_for_user(
        user_id=current_user.id,
        generation_id=generation_id,
    )
    if generation is None:
        raise not_found("Generation")
    return success_response(_generation_data(generation), request)


@router.put("/api/v1/generations/{id}", tags=["Generations"])
def update_generation(
    generation_id: Annotated[UUID, Path(alias="id")],
    payload: GenerationUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        generation = unit_of_work.generations.update(
            user_id=current_user.id,
            generation_id=generation_id,
            model=payload.model,
            prompt=payload.prompt,
            parameters=payload.parameters,
        )
    except EntityNotFoundError as error:
        raise not_found("Generation") from error
    unit_of_work.commit()
    return success_response(_generation_data(generation), request)


@router.delete("/api/v1/generations/{id}", tags=["Generations"])
def delete_generation(
    generation_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    try:
        unit_of_work.generations.soft_delete(user_id=current_user.id, generation_id=generation_id)
    except EntityNotFoundError as error:
        raise not_found("Generation") from error
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/generated-images/{id}", tags=["Images"])
def get_generated_image(
    image_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    image = unit_of_work.generated_images.get_for_user(user_id=current_user.id, image_id=image_id)
    if image is None:
        raise not_found("Generated image")
    return success_response(_generated_image_data(image), request)


@router.post("/api/v1/images/generate", tags=["Images"])
def generate_image(
    payload: GenerateImageRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        request_id = request_id_for(request)
        status = submit_image_generation(
            unit_of_work=unit_of_work,
            queue=queue,
            settings=settings,
            user=current_user,
            content_id=payload.content_id,
            style=payload.style,
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
    except EntityNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "CONTENT_NOT_FOUND", "message": "Content not found"},
        ) from error
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "IDEMPOTENCY_CONFLICT",
                "message": "Idempotency key was reused with a different request",
            },
        ) from error
    except QueueEnqueueError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "QUEUE_ENQUEUE_FAILED",
                "message": "Image generation could not be queued",
            },
        ) from error

    return success_response(_image_generation_status_data(status), request, status_code=202)


@router.post("/api/v1/images/{id}/regenerate", tags=["Images"])
def regenerate_image(
    image_id: Annotated[UUID, Path(alias="id")],
    payload: RegenerateImageRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        request_id = request_id_for(request)
        status = submit_image_regeneration(
            unit_of_work=unit_of_work,
            queue=queue,
            settings=settings,
            user=current_user,
            image_id=image_id,
            style=payload.style,
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
    except EntityNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "IMAGE_NOT_FOUND", "message": "Image not found"},
        ) from error
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "IDEMPOTENCY_CONFLICT",
                "message": "Idempotency key was reused with a different request",
            },
        ) from error
    except QueueEnqueueError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "QUEUE_ENQUEUE_FAILED",
                "message": "Image regeneration could not be queued",
            },
        ) from error

    return success_response(_image_generation_status_data(status), request, status_code=202)


@router.get("/api/v1/images/{id}", tags=["Images"])
def get_image(
    job_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> JSONResponse:
    generated_images = getattr(unit_of_work, "generated_images", None)
    generated_image = (
        generated_images.get_for_user(user_id=current_user.id, image_id=job_id)
        if generated_images is not None
        else None
    )
    if generated_image is not None:
        return success_response(_generated_image_data(generated_image), request)
    status = unit_of_work.image_generations.get_status_for_user(
        user_id=current_user.id,
        job_id=job_id,
    )
    if status is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "IMAGE_GENERATION_NOT_FOUND",
                "message": "Image Generation Job not found",
            },
        )
    public_url = None
    try:
        if status.job.status == GenerationJobStatus.COMPLETED and status.image is not None:
            public_url = storage.get_url(status.image.storage_path)
    except StorageUrlError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "STORAGE_URL_UNAVAILABLE",
                "message": "Stored image URL is unavailable",
            },
        ) from error
    return success_response(
        _image_generation_status_data(status, public_url=public_url),
        request,
    )
