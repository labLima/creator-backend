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
from creator.api.dtos import (
    PlanningCreateRequest,
    PlanningUpdateRequest,
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
    _planning_data,
)
from creator.application.unit_of_work import UnitOfWork
from creator.core.pagination import page_request
from creator.repositories import (
    UserRecord,
)

router = APIRouter()


@router.get("/api/v1/planning", tags=["Planning"])
def list_planning(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    campaign_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    result = unit_of_work.planning.list_for_user(
        user_id=current_user.id,
        campaign_id=campaign_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(result, _planning_data), request)


@router.post("/api/v1/planning", tags=["Planning"])
def create_planning(
    payload: PlanningCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    campaign = unit_of_work.campaigns.get_for_user(
        user_id=current_user.id, campaign_id=payload.campaign_id
    )
    if campaign is None:
        raise not_found("Campaign")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=campaign.workspace_id
    )
    planning = unit_of_work.planning.add(
        created_by=current_user.id,
        **payload.model_dump(),
    )
    unit_of_work.commit()
    return success_response(_planning_data(planning), request, status_code=201)


@router.get("/api/v1/planning/{id}", tags=["Planning"])
def get_planning(
    planning_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    planning = unit_of_work.planning.get_for_user(user_id=current_user.id, planning_id=planning_id)
    if planning is None:
        raise not_found("Planning")
    return success_response(_planning_data(planning), request)


@router.put("/api/v1/planning/{id}", tags=["Planning"])
def update_planning(
    planning_id: Annotated[UUID, Path(alias="id")],
    payload: PlanningUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.planning.get_for_user(user_id=current_user.id, planning_id=planning_id)
    if existing is None:
        raise not_found("Planning")
    campaign = unit_of_work.campaigns.get_for_user(
        user_id=current_user.id, campaign_id=existing.campaign_id
    )
    if campaign is None:
        raise not_found("Planning")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=campaign.workspace_id
    )
    updated = unit_of_work.planning.update(
        planning_id=planning_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_planning_data(updated), request)


@router.delete("/api/v1/planning/{id}", tags=["Planning"])
def delete_planning(
    planning_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.planning.get_for_user(user_id=current_user.id, planning_id=planning_id)
    if existing is None:
        raise not_found("Planning")
    campaign = unit_of_work.campaigns.get_for_user(
        user_id=current_user.id, campaign_id=existing.campaign_id
    )
    if campaign is None:
        raise not_found("Planning")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=campaign.workspace_id
    )
    unit_of_work.planning.soft_delete(planning_id=planning_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
