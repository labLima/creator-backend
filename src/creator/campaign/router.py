"""HTTP routes for the campaign capability.

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
from creator.campaign import service
from creator.campaign.schemas import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/campaigns", tags=["Campaigns"])
def list_campaigns(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    return success_response(
        service.list_campaigns(
            uow=unit_of_work,
            actor=current_user,
            workspace_id=workspace_id,
            page=page,
            limit=limit,
            sort=sort,
            request=request,
        ),
        request,
    )


@router.post("/api/v1/campaigns", tags=["Campaigns"])
def create_campaign(
    payload: CampaignCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_campaign(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/campaigns/{id}", tags=["Campaigns"])
def get_campaign(
    campaign_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_campaign(
            uow=unit_of_work, actor=current_user, campaign_id=campaign_id, request=request
        ),
        request,
    )


@router.put("/api/v1/campaigns/{id}", tags=["Campaigns"])
def update_campaign(
    campaign_id: Annotated[UUID, Path(alias="id")],
    payload: CampaignUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_campaign(
            uow=unit_of_work,
            actor=current_user,
            campaign_id=campaign_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/campaigns/{id}", tags=["Campaigns"])
def delete_campaign(
    campaign_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_campaign(
            uow=unit_of_work, actor=current_user, campaign_id=campaign_id, request=request
        ),
        request,
    )
