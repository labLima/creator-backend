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
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    page_payload,
    success_response,
)
from creator.api.serializers import (
    _campaign_data,
)
from creator.core.pagination import page_request
from creator.modules.campaign.schemas import (
    CampaignCreateRequest,
    CampaignUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

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
    campaigns = unit_of_work.campaigns.list_for_user(
        user_id=current_user.id,
        workspace_id=workspace_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(campaigns, _campaign_data), request)


@router.post("/api/v1/campaigns", tags=["Campaigns"])
def create_campaign(
    payload: CampaignCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    campaign = unit_of_work.campaigns.add(
        workspace_id=payload.workspace_id,
        created_by=current_user.id,
        name=payload.name,
        description=payload.description,
        target_audience=payload.target_audience,
        objectives=payload.objectives,
        voice=payload.voice,
        start_at=payload.start_at,
        end_at=payload.end_at,
    )
    unit_of_work.commit()
    return success_response(_campaign_data(campaign), request, status_code=201)


@router.get("/api/v1/campaigns/{id}", tags=["Campaigns"])
def get_campaign(
    campaign_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    campaign = unit_of_work.campaigns.get_for_user(user_id=current_user.id, campaign_id=campaign_id)
    if campaign is None:
        raise not_found("Campaign")
    return success_response(_campaign_data(campaign), request)


@router.put("/api/v1/campaigns/{id}", tags=["Campaigns"])
def update_campaign(
    campaign_id: Annotated[UUID, Path(alias="id")],
    payload: CampaignUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.campaigns.get_for_user(user_id=current_user.id, campaign_id=campaign_id)
    if existing is None:
        raise not_found("Campaign")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    updated = unit_of_work.campaigns.update(
        campaign_id=campaign_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_campaign_data(updated), request)


@router.delete("/api/v1/campaigns/{id}", tags=["Campaigns"])
def delete_campaign(
    campaign_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.campaigns.get_for_user(user_id=current_user.id, campaign_id=campaign_id)
    if existing is None:
        raise not_found("Campaign")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    unit_of_work.campaigns.soft_delete(campaign_id=campaign_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
