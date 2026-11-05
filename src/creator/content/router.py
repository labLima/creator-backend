"""HTTP routes for the content capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_content_application,
    get_current_user,
    get_llm_provider,
)
from creator.api.errors import (
    not_found,
)
from creator.api.responses import (
    page_payload,
    success_response,
)
from creator.api.serializers import (
    _content_data,
    _content_detail_data,
    _content_page_data,
    _improved_content_data,
    _post_structure_data,
)
from creator.config import Settings, get_settings
from creator.content.generation_service import (
    ContentGenerationPersistenceError,
    GenerateContentCommand,
    WorkspaceAccessDeniedError,
)
from creator.content.improvement_service import (
    ContentImprovementInvalidResponseError,
    ImproveContentCommand,
)
from creator.content.ports import ContentFilters
from creator.content.schemas import (
    ContentCreateRequest,
    ContentUpdateRequest,
    GenerateContentRequest,
    ImproveContentRequest,
)
from creator.content.service import ContentApplication
from creator.core.pagination import PageRequest, page_request
from creator.domain.exceptions import EntityNotFoundError
from creator.integrations.gemini.exceptions import (
    GeminiAuthenticationError,
    GeminiBlockedContentError,
    GeminiInvalidResponseError,
    GeminiProviderError,
    GeminiQuotaError,
    GeminiTimeoutError,
    GeminiTransientError,
)
from creator.post_structure.ports import PostStructureRecord
from creator.services.ai.provider import (
    LLMAuthenticationError,
    LLMBlockedContentError,
    LLMInvalidResponseError,
    LLMProvider,
    LLMProviderError,
    LLMQuotaError,
    LLMTimeoutError,
    LLMTransientError,
    ProviderNotConfiguredError,
)
from creator.user.ports import UserRecord

router = APIRouter()


@router.post(
    "/api/v1/contents",
    tags=["Contents"],
    operation_id="createContent",
    responses={"403": {"$ref": "#/components/responses/WorkspaceAccessDenied"}},
)
def create_content(
    payload: ContentCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[ContentApplication, Depends(get_content_application)],
) -> JSONResponse:
    record = application.create_content(
        user=current_user,
        workspace_id=payload.workspace_id,
        content_type=payload.type,
        brand_id=payload.brand_id,
        project_id=payload.project_id,
        title=payload.title,
        payload=payload.payload,
        planning_id=payload.planning_id,
    )
    if isinstance(record, PostStructureRecord):
        return success_response(_post_structure_data(record), request, status_code=201)
    return success_response(_content_data(record), request, status_code=201)


@router.get(
    "/api/v1/contents/{id}",
    tags=["Contents"],
    operation_id="getContentCanonical",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
@router.get(
    "/api/v1/content/{id}",
    tags=["Contents"],
    operation_id="getContent",
    responses={"404": {"$ref": "#/components/responses/NotFound"}},
)
def get_content(
    content_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[ContentApplication, Depends(get_content_application)],
) -> JSONResponse:
    post_structure = application.get_post_structure(user_id=current_user.id, item_id=content_id)
    if post_structure is not None:
        return success_response(_post_structure_data(post_structure), request)
    detail = application.get_detail(user_id=current_user.id, content_id=content_id)
    if detail is None:
        raise not_found("Content")
    return success_response(_content_detail_data(detail), request)


@router.put(
    "/api/v1/contents/{id}",
    tags=["Contents"],
    operation_id="updateContent",
    responses={
        "403": {"$ref": "#/components/responses/WorkspaceAccessDenied"},
        "404": {"$ref": "#/components/responses/NotFound"},
    },
)
def update_content(
    content_id: Annotated[UUID, Path(alias="id")],
    payload: ContentUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[ContentApplication, Depends(get_content_application)],
) -> JSONResponse:
    post_structure = application.get_post_structure(user_id=current_user.id, item_id=content_id)
    if post_structure is not None:
        updated = application.update_post_structure(
            user=current_user, item_id=content_id, title=payload.title, payload=payload.payload
        )
        return success_response(_post_structure_data(updated), request)
    try:
        content = application.update_content(
            user=current_user,
            content_id=content_id,
            brand_id=payload.brand_id,
            project_id=payload.project_id,
            title=payload.title,
            payload=payload.payload,
        )
    except EntityNotFoundError as error:
        raise not_found("Content") from error
    return success_response(_content_data(content), request)


@router.delete(
    "/api/v1/contents/{id}",
    tags=["Contents"],
    operation_id="deleteContentCanonical",
    responses={
        "403": {"$ref": "#/components/responses/WorkspaceAccessDenied"},
        "404": {"$ref": "#/components/responses/NotFound"},
    },
)
@router.delete(
    "/api/v1/content/{id}",
    tags=["Contents"],
    operation_id="deleteContent",
    responses={
        "403": {"$ref": "#/components/responses/WorkspaceAccessDenied"},
        "404": {"$ref": "#/components/responses/NotFound"},
    },
)
def delete_content(
    content_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[ContentApplication, Depends(get_content_application)],
) -> JSONResponse:
    post_structure = application.get_post_structure(user_id=current_user.id, item_id=content_id)
    if post_structure is not None:
        application.delete_post_structure(user=current_user, item_id=content_id)
        return success_response({"deleted": True}, request)
    try:
        application.delete_content(user=current_user, content_id=content_id)
    except EntityNotFoundError as error:
        raise not_found("Content") from error
    return success_response({"deleted": True}, request)


@router.post(
    "/api/v1/content/generate",
    tags=["Contents"],
    operation_id="generateContent",
    responses={
        "403": {"$ref": "#/components/responses/WorkspaceAccessDenied"},
        "422": {
            "$ref": "#/components/responses/ValidationFailed",
            "x-error-codes": ["VALIDATION_FAILED", "CONTENT_GENERATION_BLOCKED"],
        },
    },
)
def generate_text_content(
    payload: GenerateContentRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    application: Annotated[ContentApplication, Depends(get_content_application)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> JSONResponse:
    try:
        generated = application.generate_content(
            settings=settings,
            llm_provider=llm_provider,
            user=current_user,
            command=GenerateContentCommand(
                workspace_id=payload.workspace_id,
                topic=payload.topic,
                audience=payload.audience,
                tone=payload.tone,
                content_type=payload.content_type,
                brand_voice=payload.brand_voice,
            ),
        )
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "WORKSPACE_ACCESS_DENIED",
                "message": "Workspace is not visible to the authenticated user",
            },
        ) from error
    except ProviderNotConfiguredError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "LLM_PROVIDER_MISCONFIGURED",
                "message": "LLM provider is not configured",
            },
        ) from error
    except (GeminiAuthenticationError, LLMAuthenticationError) as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "LLM_PROVIDER_MISCONFIGURED",
                "message": "LLM provider authentication is not configured",
            },
        ) from error
    except (GeminiQuotaError, LLMQuotaError) as error:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "LLM_PROVIDER_RATE_LIMITED",
                "message": "LLM provider quota or rate limit exceeded",
            },
        ) from error
    except (GeminiBlockedContentError, LLMBlockedContentError) as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CONTENT_GENERATION_BLOCKED",
                "message": "Content generation was blocked by the provider",
            },
        ) from error
    except (GeminiInvalidResponseError, LLMInvalidResponseError) as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "LLM_PROVIDER_INVALID_RESPONSE",
                "message": "LLM provider returned an invalid response",
            },
        ) from error
    except (GeminiTimeoutError, LLMTimeoutError) as error:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "LLM_PROVIDER_TIMEOUT",
                "message": "LLM provider timed out",
            },
        ) from error
    except (
        GeminiTransientError,
        GeminiProviderError,
        LLMTransientError,
        LLMProviderError,
    ) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LLM_PROVIDER_UNAVAILABLE",
                "message": "LLM provider is unavailable",
            },
        ) from error
    except ContentGenerationPersistenceError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "CONTENT_GENERATION_PERSISTENCE_FAILED",
                "message": "Generated Content could not be persisted",
            },
        ) from error

    return success_response(
        _content_data(
            generated.content,
            generation_id=generated.generation_id,
            generation_model=generated.generation_model,
            generation_parameters=generated.generation_parameters,
        ),
        request,
    )


@router.post(
    "/api/v1/content/improve",
    tags=["Contents"],
    operation_id="improveContent",
    responses={
        "403": {"$ref": "#/components/responses/WorkspaceAccessDenied"},
        "404": {"$ref": "#/components/responses/NotFound"},
        "422": {
            "$ref": "#/components/responses/ValidationFailed",
            "x-error-codes": ["VALIDATION_FAILED", "CONTENT_IMPROVEMENT_BLOCKED"],
        },
    },
)
def improve_text_content(
    payload: ImproveContentRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    application: Annotated[ContentApplication, Depends(get_content_application)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> JSONResponse:
    try:
        preview = application.improve_content(
            settings=settings,
            llm_provider=llm_provider,
            user=current_user,
            command=ImproveContentCommand(
                workspace_id=payload.workspace_id,
                text=payload.text,
                content_id=payload.content_id,
                objective=payload.objective,
                context=payload.context,
                audience=payload.audience,
            ),
        )
    except WorkspaceAccessDeniedError as error:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "WORKSPACE_ACCESS_DENIED",
                "message": "Workspace is not visible to the authenticated user",
            },
        ) from error
    except EntityNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "CONTENT_NOT_FOUND", "message": "Content not found"},
        ) from error
    except ProviderNotConfiguredError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "LLM_PROVIDER_MISCONFIGURED",
                "message": "LLM provider is not configured",
            },
        ) from error
    except (GeminiAuthenticationError, LLMAuthenticationError) as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "LLM_PROVIDER_MISCONFIGURED",
                "message": "LLM provider authentication is not configured",
            },
        ) from error
    except (GeminiQuotaError, LLMQuotaError) as error:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "LLM_PROVIDER_RATE_LIMITED",
                "message": "LLM provider quota or rate limit exceeded",
            },
        ) from error
    except (GeminiBlockedContentError, LLMBlockedContentError) as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CONTENT_IMPROVEMENT_BLOCKED",
                "message": "Content improvement was blocked by the provider",
            },
        ) from error
    except (
        GeminiInvalidResponseError,
        LLMInvalidResponseError,
        ContentImprovementInvalidResponseError,
    ) as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "LLM_PROVIDER_INVALID_RESPONSE",
                "message": "LLM provider returned an invalid response",
            },
        ) from error
    except (GeminiTimeoutError, LLMTimeoutError) as error:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "LLM_PROVIDER_TIMEOUT",
                "message": "LLM provider timed out",
            },
        ) from error
    except (
        GeminiTransientError,
        GeminiProviderError,
        LLMTransientError,
        LLMProviderError,
    ) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LLM_PROVIDER_UNAVAILABLE",
                "message": "LLM provider is unavailable",
            },
        ) from error

    return success_response(_improved_content_data(preview), request)


@router.get("/api/v1/content", tags=["Contents"], operation_id="listContent")
@router.get("/api/v1/contents", tags=["Contents"], operation_id="listContents")
def list_content(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    application: Annotated[ContentApplication, Depends(get_content_application)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
    planning_id: UUID | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    content_type: Annotated[
        str | None,
        Query(alias="type", pattern="^(IMAGE|TEXT)$"),
    ] = None,
) -> JSONResponse:
    if planning_id is not None:
        structures = application.list_post_structures(
            user_id=current_user.id,
            planning_id=planning_id,
            page=page_request(page, limit, sort),
        )
        return success_response(page_payload(structures, _post_structure_data), request)
    content_page = application.list_content(
        user_id=current_user.id,
        filters=ContentFilters(content_type=content_type, query=q),
        page=PageRequest(
            page=page,
            limit=limit,
            sort="asc" if sort == "created_at" else "desc",
        ),
    )
    return success_response(_content_page_data(content_page), request)
