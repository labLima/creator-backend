"""HTTP routes for the order capability.

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
from creator.order import service
from creator.order.schemas import (
    OrderCreateRequest,
    OrderUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/orders", tags=["Billing"])
def list_orders(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_orders(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/orders", tags=["Billing"])
def create_order(
    payload: OrderCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_order(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/orders/{id}", tags=["Billing"])
def get_order(
    order_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_order(uow=unit_of_work, actor=current_user, order_id=order_id, request=request),
        request,
    )


@router.put("/api/v1/orders/{id}", tags=["Billing"])
def update_order(
    order_id: Annotated[UUID, Path(alias="id")],
    payload: OrderUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_order(
            uow=unit_of_work,
            actor=current_user,
            order_id=order_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/orders/{id}", tags=["Billing"])
def delete_order(
    order_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_order(
            uow=unit_of_work, actor=current_user, order_id=order_id, request=request
        ),
        request,
    )
