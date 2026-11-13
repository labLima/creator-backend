"""HTTP routes for the subscription capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.

`subscription_history` is append-only (ADR-019), so only the two reads are
published: a plan or status change is a new event, never a rewrite, and the T20
trigger refuses the UPDATE/DELETE a write handler would perform.
"""

from __future__ import annotations

from typing import Annotated
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
from creator.subscription import service
from creator.subscription.schemas import (
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get(
    "/api/v1/subscription-history",
    tags=["Billing"],
    operation_id="list_subscription_history_api_v1_subscription_history_get",
)
def list_subscription_history(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_subscription_history(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.get(
    "/api/v1/subscription-history/{id}",
    tags=["Billing"],
    operation_id="get_subscription_history_api_v1_subscription_history__id__get",
)
def get_subscription_history(
    history_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_subscription_history(
            uow=unit_of_work, actor=current_user, history_id=history_id, request=request
        ),
        request,
    )


@router.get(
    "/api/v1/subscriptions",
    tags=["Billing"],
    operation_id="list_subscriptions_api_v1_subscriptions_get",
)
def list_subscriptions(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_subscriptions(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post(
    "/api/v1/subscriptions",
    tags=["Billing"],
    operation_id="create_subscription_api_v1_subscriptions_post",
)
def create_subscription(
    payload: SubscriptionCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_subscription(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/subscriptions/{id}",
    tags=["Billing"],
    operation_id="get_subscription_api_v1_subscriptions__id__get",
)
def get_subscription(
    subscription_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_subscription(
            uow=unit_of_work, actor=current_user, subscription_id=subscription_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/subscriptions/{id}",
    tags=["Billing"],
    operation_id="update_subscription_api_v1_subscriptions__id__put",
)
def update_subscription(
    subscription_id: Annotated[UUID, Path(alias="id")],
    payload: SubscriptionUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_subscription(
            uow=unit_of_work,
            actor=current_user,
            subscription_id=subscription_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/subscriptions/{id}",
    tags=["Billing"],
    operation_id="delete_subscription_api_v1_subscriptions__id__delete",
)
def delete_subscription(
    subscription_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_subscription(
            uow=unit_of_work, actor=current_user, subscription_id=subscription_id, request=request
        ),
        request,
    )
