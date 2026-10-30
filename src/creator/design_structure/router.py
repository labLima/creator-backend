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
from creator.api.errors import (
    not_found,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _design_structure_data,
)
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
        {
            "items": [
                _design_structure_data(x)
                for x in unit_of_work.design_structures.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/design-structures", tags=["Post Structures"])
def create_design_structure(
    payload: DesignStructureCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.post_structures.get_for_user(
        user_id=current_user.id, post_structure_id=payload.post_structure_id
    )
    if item is None:
        raise not_found("Post structure")
    result = unit_of_work.design_structures.add(post_structure_id=payload.post_structure_id)
    unit_of_work.commit()
    return success_response(_design_structure_data(result), request, status_code=201)


@router.get("/api/v1/design-structures/{id}", tags=["Post Structures"])
def get_design_structure(
    design_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.design_structures.get_for_user(user_id=current_user.id, design_id=design_id)
    if item is None:
        raise not_found("Design structure")
    return success_response(_design_structure_data(item), request)


@router.put("/api/v1/design-structures/{id}", tags=["Post Structures"])
def update_design_structure(
    design_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.design_structures.get_for_user(user_id=current_user.id, design_id=design_id)
        is None
    ):
        raise not_found("Design structure")
    item = unit_of_work.design_structures.update(design_id=design_id, fields=payload)
    unit_of_work.commit()
    return success_response(_design_structure_data(item), request)


@router.delete("/api/v1/design-structures/{id}", tags=["Post Structures"])
def delete_design_structure(
    design_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.design_structures.get_for_user(user_id=current_user.id, design_id=design_id)
        is None
    ):
        raise not_found("Design structure")
    unit_of_work.design_structures.soft_delete(design_id=design_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
