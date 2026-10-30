"""HTTP routes for the content capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_llm_provider,
    get_uow,
)
from creator.api.errors import (
    not_found,
    require_workspace_write,
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
from creator.core.pagination import page_request
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
from creator.modules.content.generation_service import (
    ContentGenerationPersistenceError,
    GenerateContentCommand,
    WorkspaceAccessDeniedError,
    generate_content,
)
from creator.modules.content.improvement_service import (
    ContentImprovementInvalidResponseError,
    ImproveContentCommand,
    improve_content,
)
from creator.modules.content.schemas import (
    ContentCreateRequest,
    ContentUpdateRequest,
    GenerateContentRequest,
    ImproveContentRequest,
)
from creator.repositories import (
    ContentFilters,
    UserRecord,
)
from creator.repositories.common import PageRequest
from creator.services.ai.provider import LLMProvider, ProviderNotConfiguredError
from creator.uow import UnitOfWork

router = APIRouter()


@router.post("/api/v1/contents", tags=["Contents"])
def create_content(
    payload: ContentCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    if payload.planning_id is not None:
        post_fields = {
            key: value
            for key, value in payload.payload.items()
            if key
            in {
                "objective",
                "big_idea",
                "main_message",
                "headline",
                "image_cta",
                "art_guiding",
                "status",
                "format",
                "ratio",
                "resolution",
            }
        }
        post_structure = unit_of_work.post_structures.add(
            workspace_id=payload.workspace_id,
            planning_id=payload.planning_id,
            created_by=current_user.id,
            title=payload.title,
            **cast(dict[str, str | None], post_fields),
        )
        unit_of_work.commit()
        return success_response(_post_structure_data(post_structure), request, status_code=201)
    content = unit_of_work.contents.add(
        workspace_id=payload.workspace_id,
        created_by_user_id=current_user.id,
        content_type=payload.type,
        brand_id=payload.brand_id,
        project_id=payload.project_id,
        title=payload.title,
        payload=payload.payload,
    )
    unit_of_work.commit()
    return success_response(_content_data(content), request, status_code=201)


@router.get("/api/v1/contents/{id}", tags=["Contents"])
@router.get("/api/v1/content/{id}", tags=["Contents"])
def get_content(
    content_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    post_structures = getattr(unit_of_work, "post_structures", None)
    post_structure = (
        post_structures.get_for_user(user_id=current_user.id, post_structure_id=content_id)
        if post_structures is not None
        else None
    )
    if post_structure is not None:
        assert post_structures is not None
        return success_response(_post_structure_data(post_structure), request)
    detail = unit_of_work.contents.get_detail_by_id_for_user(
        user_id=current_user.id,
        content_id=content_id,
    )
    if detail is None:
        raise not_found("Content")
    return success_response(_content_detail_data(detail), request)


@router.put("/api/v1/contents/{id}", tags=["Contents"])
def update_content(
    content_id: Annotated[UUID, Path(alias="id")],
    payload: ContentUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    post_structures = getattr(unit_of_work, "post_structures", None)
    post_structure = (
        post_structures.get_for_user(user_id=current_user.id, post_structure_id=content_id)
        if post_structures is not None
        else None
    )
    if post_structure is not None:
        assert post_structures is not None
        require_workspace_write(
            unit_of_work, user_id=current_user.id, workspace_id=post_structure.workspace_id
        )
        allowed_fields = {
            "objective",
            "big_idea",
            "main_message",
            "headline",
            "image_cta",
            "art_guiding",
            "status",
            "format",
            "ratio",
            "resolution",
        }
        fields = {
            key: value for key, value in (payload.payload or {}).items() if key in allowed_fields
        }
        if payload.title is not None:
            fields["title"] = payload.title
        updated = post_structures.update(
            post_structure_id=content_id,
            fields=cast(dict[str, str | None], fields),
        )
        unit_of_work.commit()
        return success_response(_post_structure_data(updated), request)
    existing = unit_of_work.contents.get_by_id_for_user(
        user_id=current_user.id,
        content_id=content_id,
    )
    if existing is None:
        raise not_found("Content")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    try:
        content = unit_of_work.contents.update(
            content_id,
            user_id=current_user.id,
            brand_id=payload.brand_id,
            project_id=payload.project_id,
            title=payload.title,
            payload=payload.payload,
        )
    except EntityNotFoundError as error:
        raise not_found("Content") from error
    unit_of_work.commit()
    return success_response(_content_data(content), request)


@router.delete("/api/v1/contents/{id}", tags=["Contents"])
@router.delete("/api/v1/content/{id}", tags=["Contents"])
def delete_content(
    content_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    post_structures = getattr(unit_of_work, "post_structures", None)
    post_structure = (
        post_structures.get_for_user(user_id=current_user.id, post_structure_id=content_id)
        if post_structures is not None
        else None
    )
    if post_structure is not None:
        assert post_structures is not None
        require_workspace_write(
            unit_of_work, user_id=current_user.id, workspace_id=post_structure.workspace_id
        )
        post_structures.soft_delete(post_structure_id=content_id)
        unit_of_work.commit()
        return success_response({"deleted": True}, request)
    existing = unit_of_work.contents.get_by_id_for_user(
        user_id=current_user.id,
        content_id=content_id,
        include_deleted=True,
    )
    if existing is None:
        raise not_found("Content")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    try:
        unit_of_work.contents.soft_delete(user_id=current_user.id, content_id=content_id)
    except EntityNotFoundError as error:
        raise not_found("Content") from error
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.post("/api/v1/content/generate", tags=["Contents"])
def generate_text_content(
    payload: GenerateContentRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> JSONResponse:
    try:
        generated = generate_content(
            unit_of_work=unit_of_work,
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
    except GeminiAuthenticationError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "LLM_PROVIDER_MISCONFIGURED",
                "message": "LLM provider authentication is not configured",
            },
        ) from error
    except GeminiQuotaError as error:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "LLM_PROVIDER_RATE_LIMITED",
                "message": "LLM provider quota or rate limit exceeded",
            },
        ) from error
    except GeminiBlockedContentError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CONTENT_GENERATION_BLOCKED",
                "message": "Content generation was blocked by the provider",
            },
        ) from error
    except GeminiInvalidResponseError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "LLM_PROVIDER_INVALID_RESPONSE",
                "message": "LLM provider returned an invalid response",
            },
        ) from error
    except GeminiTimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "LLM_PROVIDER_TIMEOUT",
                "message": "LLM provider timed out",
            },
        ) from error
    except (GeminiTransientError, GeminiProviderError) as error:
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


@router.post("/api/v1/content/improve", tags=["Contents"])
def improve_text_content(
    payload: ImproveContentRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> JSONResponse:
    try:
        preview = improve_content(
            unit_of_work=unit_of_work,
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
    except GeminiAuthenticationError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "LLM_PROVIDER_MISCONFIGURED",
                "message": "LLM provider authentication is not configured",
            },
        ) from error
    except GeminiQuotaError as error:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "LLM_PROVIDER_RATE_LIMITED",
                "message": "LLM provider quota or rate limit exceeded",
            },
        ) from error
    except GeminiBlockedContentError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CONTENT_IMPROVEMENT_BLOCKED",
                "message": "Content improvement was blocked by the provider",
            },
        ) from error
    except (GeminiInvalidResponseError, ContentImprovementInvalidResponseError) as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "LLM_PROVIDER_INVALID_RESPONSE",
                "message": "LLM provider returned an invalid response",
            },
        ) from error
    except GeminiTimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "LLM_PROVIDER_TIMEOUT",
                "message": "LLM provider timed out",
            },
        ) from error
    except (GeminiTransientError, GeminiProviderError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LLM_PROVIDER_UNAVAILABLE",
                "message": "LLM provider is unavailable",
            },
        ) from error

    return success_response(_improved_content_data(preview), request)


@router.get("/api/v1/content", tags=["Contents"])
@router.get("/api/v1/contents", tags=["Contents"])
def list_content(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
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
        structures = unit_of_work.post_structures.list_for_user(
            user_id=current_user.id,
            planning_id=planning_id,
            page=page_request(page, limit, sort),
        )
        return success_response(page_payload(structures, _post_structure_data), request)
    content_page = unit_of_work.contents.list_for_user(
        user_id=current_user.id,
        filters=ContentFilters(content_type=content_type, query=q),
        page=PageRequest(
            page=page,
            limit=limit,
            sort="asc" if sort == "created_at" else "desc",
        ),
    )
    return success_response(_content_page_data(content_page), request)
