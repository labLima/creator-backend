"""HTTP routes for the subscription capability.

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
    require_workspace_write,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _subscription_data,
    _subscription_history_data,
)
from creator.subscription.schemas import (
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/subscription-history", tags=["Billing"])
def list_subscription_history(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _subscription_history_data(x)
                for x in unit_of_work.subscription_history.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/subscription-history", tags=["Billing"])
def create_subscription_history(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    subscription_id = payload.get("subscription_id")
    if (
        subscription_id is None
        or unit_of_work.subscriptions.get_for_user(
            user_id=current_user.id, subscription_id=subscription_id
        )
        is None
    ):
        raise not_found("Subscription")
    item = unit_of_work.subscription_history.add(fields=payload)
    unit_of_work.commit()
    return success_response(_subscription_history_data(item), request, status_code=201)


@router.get("/api/v1/subscription-history/{id}", tags=["Billing"])
def get_subscription_history(
    history_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.subscription_history.get_for_user(
        user_id=current_user.id, history_id=history_id
    )
    if item is None:
        raise not_found("Subscription history")
    return success_response(_subscription_history_data(item), request)


@router.put("/api/v1/subscription-history/{id}", tags=["Billing"])
def update_subscription_history(
    history_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.subscription_history.get_for_user(
            user_id=current_user.id, history_id=history_id
        )
        is None
    ):
        raise not_found("Subscription history")
    item = unit_of_work.subscription_history.update(history_id=history_id, fields=payload)
    unit_of_work.commit()
    return success_response(_subscription_history_data(item), request)


@router.delete("/api/v1/subscription-history/{id}", tags=["Billing"])
def delete_subscription_history(
    history_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.subscription_history.get_for_user(
            user_id=current_user.id, history_id=history_id
        )
        is None
    ):
        raise not_found("Subscription history")
    unit_of_work.subscription_history.soft_delete(history_id=history_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/subscriptions", tags=["Billing"])
def list_subscriptions(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _subscription_data(x)
                for x in unit_of_work.subscriptions.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/subscriptions", tags=["Billing"])
def create_subscription(
    payload: SubscriptionCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.billing_accounts.get_for_user(
            user_id=current_user.id, account_id=payload.billing_account_id
        )
        is None
    ):
        raise not_found("Billing account")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    if unit_of_work.plans.get(plan_id=payload.plan_id) is None:
        raise not_found("Plan")
    item = unit_of_work.subscriptions.add(**payload.model_dump())
    unit_of_work.commit()
    return success_response(_subscription_data(item), request, status_code=201)


@router.get("/api/v1/subscriptions/{id}", tags=["Billing"])
def get_subscription(
    subscription_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.subscriptions.get_for_user(
        user_id=current_user.id, subscription_id=subscription_id
    )
    if item is None:
        raise not_found("Subscription")
    return success_response(_subscription_data(item), request)


@router.put("/api/v1/subscriptions/{id}", tags=["Billing"])
def update_subscription(
    subscription_id: Annotated[UUID, Path(alias="id")],
    payload: SubscriptionUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.subscriptions.get_for_user(
            user_id=current_user.id, subscription_id=subscription_id
        )
        is None
    ):
        raise not_found("Subscription")
    item = unit_of_work.subscriptions.update(
        subscription_id=subscription_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_subscription_data(item), request)


@router.delete("/api/v1/subscriptions/{id}", tags=["Billing"])
def delete_subscription(
    subscription_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.subscriptions.get_for_user(
            user_id=current_user.id, subscription_id=subscription_id
        )
        is None
    ):
        raise not_found("Subscription")
    unit_of_work.subscriptions.soft_delete(subscription_id=subscription_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
