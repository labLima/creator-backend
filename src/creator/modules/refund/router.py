"""HTTP routes for the refund capability.

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
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _refund_data,
)
from creator.modules.refund.schemas import (
    RefundCreateRequest,
    RefundUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

router = APIRouter()


@router.get("/api/v1/refunds", tags=["Billing"])
def list_refunds(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _refund_data(x) for x in unit_of_work.refunds.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/refunds", tags=["Billing"])
def create_refund(
    payload: RefundCreateRequest,
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
    data = payload.model_dump()
    data["status"] = "pending"
    item = unit_of_work.refunds.add(fields=data)
    unit_of_work.commit()
    return success_response(_refund_data(item), request, status_code=201)


@router.get("/api/v1/refunds/{id}", tags=["Billing"])
def get_refund(
    refund_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.refunds.get_for_user(user_id=current_user.id, refund_id=refund_id)
    if item is None:
        raise not_found("Refund")
    return success_response(_refund_data(item), request)


@router.put("/api/v1/refunds/{id}", tags=["Billing"])
def update_refund(
    refund_id: Annotated[UUID, Path(alias="id")],
    payload: RefundUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.refunds.get_for_user(user_id=current_user.id, refund_id=refund_id) is None:
        raise not_found("Refund")
    item = unit_of_work.refunds.update(
        refund_id=refund_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_refund_data(item), request)


@router.delete("/api/v1/refunds/{id}", tags=["Billing"])
def delete_refund(
    refund_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.refunds.get_for_user(user_id=current_user.id, refund_id=refund_id) is None:
        raise not_found("Refund")
    unit_of_work.refunds.soft_delete(refund_id=refund_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
