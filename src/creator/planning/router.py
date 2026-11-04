"""HTTP routes for the planning capability.

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
from creator.planning import service
from creator.planning.schemas import (
    PlanningCreateRequest,
    PlanningUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/planning", tags=["Planning"], operation_id="listPlanning")
def list_planning(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    campaign_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_planning(
            uow=unit_of_work,
            actor=current_user,
            campaign_id=campaign_id,
            page=page,
            limit=limit,
            sort=sort,
            request=request,
        ),
        request,
    )


@router.post(
    "/api/v1/planning", tags=["Planning"], operation_id="create_planning_api_v1_planning_post"
)
def create_planning(
    payload: PlanningCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_planning(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/planning/{id}", tags=["Planning"], operation_id="getPlanning")
def get_planning(
    planning_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_planning(
            uow=unit_of_work, actor=current_user, planning_id=planning_id, request=request
        ),
        request,
    )


@router.put("/api/v1/planning/{id}", tags=["Planning"], operation_id="updatePlanning")
def update_planning(
    planning_id: Annotated[UUID, Path(alias="id")],
    payload: PlanningUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_planning(
            uow=unit_of_work,
            actor=current_user,
            planning_id=planning_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/planning/{id}", tags=["Planning"], operation_id="deletePlanning")
def delete_planning(
    planning_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_planning(
            uow=unit_of_work, actor=current_user, planning_id=planning_id, request=request
        ),
        request,
    )
