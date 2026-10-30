"""HTTP routes for the plan capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
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
from creator.api.errors import (
    not_found,
    require_global_billing_admin,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _plan_data,
    _plan_item_data,
)
from creator.plan.schemas import (
    PlanCreateRequest,
    PlanItemCreateRequest,
    PlanItemUpdateRequest,
    PlanUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/plans", tags=["Billing"])
def list_plans(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    return success_response(
        {"items": [_plan_data(item) for item in unit_of_work.plans.list()]}, request
    )


@router.post("/api/v1/plans", tags=["Billing"])
def create_plan(
    payload: PlanCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.plans.add(**payload.model_dump())
    unit_of_work.commit()
    return success_response(_plan_data(item), request, status_code=201)


@router.get("/api/v1/plans/{id}", tags=["Billing"])
def get_plan(
    plan_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.plans.get(plan_id=plan_id)
    if item is None:
        raise not_found("Plan")
    return success_response(_plan_data(item), request)


@router.put("/api/v1/plans/{id}", tags=["Billing"])
def update_plan(
    plan_id: Annotated[UUID, Path(alias="id")],
    payload: PlanUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.plans.get(plan_id=plan_id) is None:
        raise not_found("Plan")
    item = unit_of_work.plans.update(plan_id=plan_id, fields=payload.model_dump(exclude_unset=True))
    unit_of_work.commit()
    return success_response(_plan_data(item), request)


@router.delete("/api/v1/plans/{id}", tags=["Billing"])
def delete_plan(
    plan_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.plans.get(plan_id=plan_id) is None:
        raise not_found("Plan")
    unit_of_work.plans.soft_delete(plan_id=plan_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/plan-items", tags=["Billing"])
def list_plan_items(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    plan_id: UUID | None = None,
) -> JSONResponse:
    require_global_billing_admin(current_user)
    items = unit_of_work.plan_items.list(plan_id=plan_id)
    return success_response({"items": [_plan_item_data(item) for item in items]}, request)


@router.post("/api/v1/plan-items", tags=["Billing"])
def create_plan_item(
    payload: PlanItemCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.plans.get(plan_id=payload.plan_id) is None:
        raise not_found("Plan")
    item = unit_of_work.plan_items.add(**payload.model_dump())
    unit_of_work.commit()
    return success_response(_plan_item_data(item), request, status_code=201)


@router.get("/api/v1/plan-items/{id}", tags=["Billing"])
def get_plan_item(
    item_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.plan_items.get(item_id=item_id)
    if item is None:
        raise not_found("Plan item")
    return success_response(_plan_item_data(item), request)


@router.put("/api/v1/plan-items/{id}", tags=["Billing"])
def update_plan_item(
    item_id: Annotated[UUID, Path(alias="id")],
    payload: PlanItemUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.plan_items.get(item_id=item_id) is None:
        raise not_found("Plan item")
    item = unit_of_work.plan_items.update(
        item_id=item_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_plan_item_data(item), request)


@router.delete("/api/v1/plan-items/{id}", tags=["Billing"])
def delete_plan_item(
    item_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.plan_items.get(item_id=item_id) is None:
        raise not_found("Plan item")
    unit_of_work.plan_items.soft_delete(item_id=item_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
