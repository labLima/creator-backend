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
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _order_data,
)
from creator.order.schemas import (
    OrderCreateRequest,
    OrderUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

router = APIRouter()


@router.get("/api/v1/orders", tags=["Billing"])
def list_orders(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _order_data(x) for x in unit_of_work.orders.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/orders", tags=["Billing"])
def create_order(
    payload: OrderCreateRequest,
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
    data = payload.model_dump()
    data["status"] = "pending"
    item = unit_of_work.orders.add(fields=data)
    unit_of_work.commit()
    return success_response(_order_data(item), request, status_code=201)


@router.get("/api/v1/orders/{id}", tags=["Billing"])
def get_order(
    order_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.orders.get_for_user(user_id=current_user.id, order_id=order_id)
    if item is None:
        raise not_found("Order")
    return success_response(_order_data(item), request)


@router.put("/api/v1/orders/{id}", tags=["Billing"])
def update_order(
    order_id: Annotated[UUID, Path(alias="id")],
    payload: OrderUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.orders.get_for_user(user_id=current_user.id, order_id=order_id) is None:
        raise not_found("Order")
    item = unit_of_work.orders.update(
        order_id=order_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_order_data(item), request)


@router.delete("/api/v1/orders/{id}", tags=["Billing"])
def delete_order(
    order_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.orders.get_for_user(user_id=current_user.id, order_id=order_id) is None:
        raise not_found("Order")
    unit_of_work.orders.soft_delete(order_id=order_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
