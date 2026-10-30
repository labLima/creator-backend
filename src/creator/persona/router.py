"""HTTP routes for the persona capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_uow,
)
from creator.api.responses import (
    success_response,
)
from creator.persona import service
from creator.persona.schemas import (
    PersonaCreateRequest,
    PersonaUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/personas", tags=["Personas"])
def list_personas(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    brand_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_personas(
            uow=unit_of_work,
            actor=current_user,
            brand_id=brand_id,
            page=page,
            limit=limit,
            sort=sort,
            request=request,
        ),
        request,
    )


@router.post("/api/v1/personas", tags=["Personas"])
def create_persona(
    payload: PersonaCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_persona(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/personas/{id}", tags=["Personas"])
def get_persona(
    persona_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_persona(
            uow=unit_of_work, actor=current_user, persona_id=persona_id, request=request
        ),
        request,
    )


@router.put("/api/v1/personas/{id}", tags=["Personas"])
def update_persona(
    persona_id: Annotated[UUID, Path(alias="id")],
    payload: PersonaUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_persona(
            uow=unit_of_work,
            actor=current_user,
            persona_id=persona_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/personas/{id}", tags=["Personas"])
def delete_persona(
    persona_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_persona(
            uow=unit_of_work, actor=current_user, persona_id=persona_id, request=request
        ),
        request,
    )
