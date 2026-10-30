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
from creator.api.dtos import (
    PersonaCreateRequest,
    PersonaUpdateRequest,
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
    _persona_data,
)
from creator.application.unit_of_work import UnitOfWork
from creator.core.pagination import page_request
from creator.repositories import (
    UserRecord,
)

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
    result = unit_of_work.personas.list_for_user(
        user_id=current_user.id,
        brand_id=brand_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(result, _persona_data), request)


@router.post("/api/v1/personas", tags=["Personas"])
def create_persona(
    payload: PersonaCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    brand = unit_of_work.brands.get_for_user(user_id=current_user.id, brand_id=payload.brand_id)
    if brand is None:
        raise not_found("Brand")
    require_workspace_write(unit_of_work, user_id=current_user.id, workspace_id=brand.workspace_id)
    persona = unit_of_work.personas.add(
        created_by=current_user.id,
        **payload.model_dump(),
    )
    unit_of_work.commit()
    return success_response(_persona_data(persona), request, status_code=201)


@router.get("/api/v1/personas/{id}", tags=["Personas"])
def get_persona(
    persona_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    persona = unit_of_work.personas.get_for_user(user_id=current_user.id, persona_id=persona_id)
    if persona is None:
        raise not_found("Persona")
    return success_response(_persona_data(persona), request)


@router.put("/api/v1/personas/{id}", tags=["Personas"])
def update_persona(
    persona_id: Annotated[UUID, Path(alias="id")],
    payload: PersonaUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.personas.get_for_user(user_id=current_user.id, persona_id=persona_id)
    if existing is None:
        raise not_found("Persona")
    brand = unit_of_work.brands.get_for_user(user_id=current_user.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Persona")
    require_workspace_write(unit_of_work, user_id=current_user.id, workspace_id=brand.workspace_id)
    updated = unit_of_work.personas.update(
        persona_id=persona_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_persona_data(updated), request)


@router.delete("/api/v1/personas/{id}", tags=["Personas"])
def delete_persona(
    persona_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.personas.get_for_user(user_id=current_user.id, persona_id=persona_id)
    if existing is None:
        raise not_found("Persona")
    brand = unit_of_work.brands.get_for_user(user_id=current_user.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Persona")
    require_workspace_write(unit_of_work, user_id=current_user.id, workspace_id=brand.workspace_id)
    unit_of_work.personas.soft_delete(persona_id=persona_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
