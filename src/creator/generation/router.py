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
    get_generation_application,
    get_generation_queue,
    get_storage_provider,
)
from creator.api.errors import (
    not_found,
)
from creator.api.responses import (
    page_payload,
    request_id_for,
    success_response,
)
from creator.api.serializers import (
    _generated_image_data,
    _generation_data,
    _image_data,
    _image_generation_status_data,
)
from creator.config import Settings, get_settings
from creator.core.pagination import page_request
from creator.domain.exceptions import EntityNotFoundError, InvalidStateTransitionError
from creator.domain.generation import GenerationJobStatus
from creator.generation.ports import GenerationJobRecord, GenerationQueue
from creator.generation.schemas import (
    GenerateImageRequest,
    GenerationCreateRequest,
    GenerationUpdateRequest,
    IndependentGenerationRequest,
    RegenerateImageRequest,
    SceneReviewDecisionRequest,
)
from creator.generation.service import (
    GenerationApplication,
    IdempotencyConflictError,
    QueueEnqueueError,
)
from creator.services.storage.provider import StorageProvider, StorageUrlError
from creator.user.ports import UserRecord

router = APIRouter()


@router.post(
    "/api/v1/generation-jobs",
    tags=["Generations"],
    operation_id="createIndependentGenerationJob",
    status_code=202,
    responses={
        "404": {"$ref": "#/components/responses/NotFound"},
        "409": {"$ref": "#/components/responses/Conflict"},
    },
)
def create_independent_generation_job(
    payload: IndependentGenerationRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> JSONResponse:
    try:
        job = application.submit_independent_generation(
            queue=queue,
            storage=storage,
            settings=settings,
            user=current_user,
            payload=payload,
            idempotency_key=idempotency_key,
            request_id=request_id_for(request),
        )
    except EntityNotFoundError as error:
        raise not_found("Generation input") from error
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "IDEMPOTENCY_CONFLICT", "message": str(error)},
        ) from error
    except QueueEnqueueError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "QUEUE_ENQUEUE_FAILED",
                "message": "Generation Job could not be queued",
            },
        ) from error
    return success_response(
        _generation_job_data(
            job,
            planning_id=payload.planning_id,
            post_structure_id=payload.post_structure_id,
        ),
        request,
        status_code=202,
    )


@router.get(
    "/api/v1/generation-jobs/{id}",
    tags=["Generations"],
    operation_id="getIndependentGenerationJob",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_independent_generation_job(
    job_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> JSONResponse:
    details = application.get_independent_generation_job(user_id=current_user.id, job_id=job_id)
    if details is None:
        raise not_found("Generation Job")
    job, status, versions = details
    result: dict[str, object] = _generation_job_data(job)
    if status is not None:
        request_input = status.parameters.get("request_input")
        if isinstance(request_input, dict):
            for field in ("planning_id", "post_structure_id"):
                value = request_input.get(field)
                if isinstance(value, str):
                    result[field] = value
    if status is not None and status.image is not None:
        result["image"] = _image_data(status.image)
    if status is not None:
        review = status.parameters.get("scene_review")
        if (
            job.status == GenerationJobStatus.PROCESSING
            and isinstance(review, dict)
            and review.get("status") in {"PENDING", "APPROVED"}
        ):
            path = review.get("storage_path")
            if isinstance(path, str):
                try:
                    result["scene_review"] = {
                        "status": review["status"],
                        "stage": review.get("stage", "FINAL"),
                        "image_url": storage.get_url(path),
                    }
                except StorageUrlError:
                    pass
    if job.artifact_type in {"COPY", "CAPTION"}:
        result["text_versions"] = [
            {
                "version_number": version.version_number,
                "artifact_type": version.artifact_type,
                "text": version.text,
                "metadata": version.metadata,
                "created_at": version.created_at.isoformat(),
            }
            for version in versions
        ]
    return success_response(result, request)


@router.post(
    "/api/v1/generation-jobs/{id}/scene-decision",
    tags=["Generations"],
    operation_id="decideIndependentGenerationScene",
    responses={
        "404": {"$ref": "#/components/responses/NotFound"},
        "409": {"$ref": "#/components/responses/Conflict"},
    },
)
def decide_independent_generation_scene(
    job_id: Annotated[UUID, Path(alias="id")],
    payload: SceneReviewDecisionRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> JSONResponse:
    try:
        job = application.decide_independent_scene(
            user=current_user,
            job_id=job_id,
            approve=payload.decision == "APPROVE",
            queue=queue,
            request_id=request_id_for(request),
            storage=storage,
        )
    except EntityNotFoundError as error:
        raise not_found("Generation Job") from error
    except InvalidStateTransitionError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SCENE_REVIEW_INVALID_STATE",
                "message": str(error),
            },
        ) from error
    except QueueEnqueueError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "QUEUE_ENQUEUE_FAILED",
                "message": str(error),
            },
        ) from error
    return success_response(_generation_job_data(job), request)


def _generation_job_data(
    job: GenerationJobRecord,
    *,
    planning_id: UUID | None = None,
    post_structure_id: UUID | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": str(job.id),
        "workspace_id": str(job.workspace_id),
        "generation_id": str(job.generation_id),
        "content_id": str(job.content_id),
        "artifact_type": job.artifact_type,
        "operation": job.operation,
        "status": job.status.value,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "failure_code": job.failure_code,
        "failure_message": job.failure_message,
        "queued_at": job.queued_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "failed_at": job.failed_at.isoformat() if job.failed_at else None,
        "request_id": str(job.request_id) if job.request_id else None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
    if planning_id is not None:
        result["planning_id"] = str(planning_id)
    if post_structure_id is not None:
        result["post_structure_id"] = str(post_structure_id)
    return result


@router.get("/api/v1/generations", tags=["Generations"], operation_id="listGenerations")
def list_generations(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
    workspace_id: UUID | None = None,
    content_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    generations = application.list_generations(
        user_id=current_user.id,
        workspace_id=workspace_id,
        content_id=content_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(generations, _generation_data), request)


@router.post("/api/v1/generations", tags=["Generations"], operation_id="createGeneration")
def create_generation(
    payload: GenerationCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
) -> JSONResponse:
    generation = application.create_generation(
        user=current_user,
        workspace_id=payload.workspace_id,
        content_id=payload.content_id,
        generation_type=payload.type,
        brand_id=payload.brand_id,
        project_id=payload.project_id,
        model=payload.model,
        prompt=payload.prompt,
        parameters=payload.parameters,
    )
    return success_response(_generation_data(generation), request, status_code=201)


@router.get("/api/v1/generations/{id}", tags=["Generations"], operation_id="getGeneration")
def get_generation(
    generation_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
) -> JSONResponse:
    generation = application.get_generation(
        user_id=current_user.id,
        generation_id=generation_id,
    )
    if generation is None:
        raise not_found("Generation")
    return success_response(_generation_data(generation), request)


@router.put("/api/v1/generations/{id}", tags=["Generations"], operation_id="updateGeneration")
def update_generation(
    generation_id: Annotated[UUID, Path(alias="id")],
    payload: GenerationUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
) -> JSONResponse:
    try:
        generation = application.update_generation(
            user_id=current_user.id,
            generation_id=generation_id,
            model=payload.model,
            prompt=payload.prompt,
            parameters=payload.parameters,
        )
    except EntityNotFoundError as error:
        raise not_found("Generation") from error
    return success_response(_generation_data(generation), request)


@router.delete("/api/v1/generations/{id}", tags=["Generations"], operation_id="deleteGeneration")
def delete_generation(
    generation_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
) -> JSONResponse:
    try:
        application.delete_generation(user_id=current_user.id, generation_id=generation_id)
    except EntityNotFoundError as error:
        raise not_found("Generation") from error
    return success_response({"deleted": True}, request)


@router.get(
    "/api/v1/generated-images/{id}",
    tags=["Images"],
    operation_id="getGeneratedImage",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_generated_image(
    image_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
) -> JSONResponse:
    image = application.get_generated_image(user_id=current_user.id, image_id=image_id)
    if image is None:
        raise not_found("Generated image")
    return success_response(_generated_image_data(image), request)


@router.post(
    "/api/v1/images/generate",
    tags=["Images"],
    operation_id="generateImage",
    responses={
        "404": {"$ref": "#/components/responses/NotFound"},
        "409": {"$ref": "#/components/responses/Conflict"},
    },
)
def generate_image(
    payload: GenerateImageRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        request_id = request_id_for(request)
        status = application.submit_image_generation(
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


@router.post(
    "/api/v1/images/{id}/regenerate",
    tags=["Images"],
    operation_id="regenerateImage",
    responses={
        "404": {"$ref": "#/components/responses/NotFound"},
        "409": {"$ref": "#/components/responses/Conflict"},
    },
)
def regenerate_image(
    image_id: Annotated[UUID, Path(alias="id")],
    payload: RegenerateImageRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
    queue: Annotated[GenerationQueue, Depends(get_generation_queue)],
) -> JSONResponse:
    try:
        request_id = request_id_for(request)
        status = application.submit_image_regeneration(
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


@router.get(
    "/api/v1/images/{id}",
    tags=["Images"],
    operation_id="getImage",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_image(
    job_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[GenerationApplication, Depends(get_generation_application)],
    storage: Annotated[StorageProvider, Depends(get_storage_provider)],
) -> JSONResponse:
    generated_image = application.get_generated_image(user_id=current_user.id, image_id=job_id)
    if generated_image is not None:
        return success_response(_generated_image_data(generated_image), request)
    status = application.get_image_generation_status(
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
