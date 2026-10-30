"""HTTP routes for the design_structure capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_uow,
)
from creator.api.responses import (
    success_response,
)
from creator.design_structure import service
from creator.design_structure.schemas import (
    DesignStructureCreateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/design-structures", tags=["Post Structures"])
def list_design_structures(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_design_structures(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/design-structures", tags=["Post Structures"])
def create_design_structure(
    payload: DesignStructureCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_design_structure(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/design-structures/{id}", tags=["Post Structures"])
def get_design_structure(
    design_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_design_structure(
            uow=unit_of_work, actor=current_user, design_id=design_id, request=request
        ),
        request,
    )


@router.put("/api/v1/design-structures/{id}", tags=["Post Structures"])
def update_design_structure(
    design_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_design_structure(
            uow=unit_of_work,
            actor=current_user,
            design_id=design_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/design-structures/{id}", tags=["Post Structures"])
def delete_design_structure(
    design_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_design_structure(
            uow=unit_of_work, actor=current_user, design_id=design_id, request=request
        ),
        request,
    )
