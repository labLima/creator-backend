from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from creator.activity_event import service
from creator.api.dependencies import get_current_user, get_uow
from creator.api.responses import success_response
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get(
    "/api/v1/workspaces/{workspace_id}/activity-events",
    tags=["Workspaces"],
    operation_id="listActivityEvents",
    responses={
        403: {
            "$ref": "#/components/responses/WorkspaceAccessDenied",
            "x-error-codes": ["WORKSPACE_ACCESS_DENIED"],
        },
        422: {
            "$ref": "#/components/responses/ValidationFailed",
            "x-error-codes": ["VALIDATION_FAILED", "INVALID_CURSOR", "INVALID_ENTITY_FILTER"],
        },
    },
)
def list_activity_events(
    request: Request,
    workspace_id: UUID,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    user_id: UUID | None = None,
    brand_id: UUID | None = None,
    entity_type: Literal["brand"] | None = None,
    entity_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_events(
            uow=unit_of_work,
            actor=current_user,
            workspace_id=workspace_id,
            limit=limit,
            cursor=cursor,
            user_id=user_id,
            brand_id=brand_id,
            entity_type=entity_type,
            entity_id=entity_id,
        ),
        request,
    )
