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
from creator.api.responses import (
    success_response,
)
from creator.plan import service
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
    return success_response(
        service.list_plans(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/plans", tags=["Billing"])
def create_plan(
    payload: PlanCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_plan(uow=unit_of_work, actor=current_user, payload=payload, request=request),
        request,
        status_code=201,
    )


@router.get("/api/v1/plans/{id}", tags=["Billing"])
def get_plan(
    plan_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_plan(uow=unit_of_work, actor=current_user, plan_id=plan_id, request=request),
        request,
    )


@router.put("/api/v1/plans/{id}", tags=["Billing"])
def update_plan(
    plan_id: Annotated[UUID, Path(alias="id")],
    payload: PlanUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_plan(
            uow=unit_of_work, actor=current_user, plan_id=plan_id, payload=payload, request=request
        ),
        request,
    )


@router.delete("/api/v1/plans/{id}", tags=["Billing"])
def delete_plan(
    plan_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_plan(uow=unit_of_work, actor=current_user, plan_id=plan_id, request=request),
        request,
    )


@router.get("/api/v1/plan-items", tags=["Billing"])
def list_plan_items(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    plan_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_plan_items(
            uow=unit_of_work, actor=current_user, plan_id=plan_id, request=request
        ),
        request,
    )


@router.post("/api/v1/plan-items", tags=["Billing"])
def create_plan_item(
    payload: PlanItemCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_plan_item(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/plan-items/{id}", tags=["Billing"])
def get_plan_item(
    item_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_plan_item(
            uow=unit_of_work, actor=current_user, item_id=item_id, request=request
        ),
        request,
    )


@router.put("/api/v1/plan-items/{id}", tags=["Billing"])
def update_plan_item(
    item_id: Annotated[UUID, Path(alias="id")],
    payload: PlanItemUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_plan_item(
            uow=unit_of_work, actor=current_user, item_id=item_id, payload=payload, request=request
        ),
        request,
    )


@router.delete("/api/v1/plan-items/{id}", tags=["Billing"])
def delete_plan_item(
    item_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_plan_item(
            uow=unit_of_work, actor=current_user, item_id=item_id, request=request
        ),
        request,
    )
