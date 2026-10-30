"""HTTP routes for the payment_method capability.

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
    _payment_method_data,
)
from creator.modules.payment_method.schemas import (
    PaymentMethodCreateRequest,
    PaymentMethodUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

router = APIRouter()


@router.get("/api/v1/billing-payment-methods", tags=["Billing"])
def list_payment_methods(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    billing_account_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _payment_method_data(x)
                for x in unit_of_work.billing_payment_methods.list_for_user(
                    user_id=current_user.id, account_id=billing_account_id
                )
            ]
        },
        request,
    )


@router.post("/api/v1/billing-payment-methods", tags=["Billing"])
def create_payment_method(
    payload: PaymentMethodCreateRequest,
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
    account_id = data.pop("billing_account_id")
    item = unit_of_work.billing_payment_methods.add(billing_account_id=account_id, fields=data)
    unit_of_work.commit()
    return success_response(_payment_method_data(item), request, status_code=201)


@router.get("/api/v1/billing-payment-methods/{id}", tags=["Billing"])
def get_payment_method(
    method_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.billing_payment_methods.get_for_user(
        user_id=current_user.id, method_id=method_id
    )
    if item is None:
        raise not_found("Billing payment method")
    return success_response(_payment_method_data(item), request)


@router.put("/api/v1/billing-payment-methods/{id}", tags=["Billing"])
def update_payment_method(
    method_id: Annotated[UUID, Path(alias="id")],
    payload: PaymentMethodUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.billing_payment_methods.get_for_user(
            user_id=current_user.id, method_id=method_id
        )
        is None
    ):
        raise not_found("Billing payment method")
    item = unit_of_work.billing_payment_methods.update(
        method_id=method_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_payment_method_data(item), request)


@router.delete("/api/v1/billing-payment-methods/{id}", tags=["Billing"])
def delete_payment_method(
    method_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.billing_payment_methods.get_for_user(
            user_id=current_user.id, method_id=method_id
        )
        is None
    ):
        raise not_found("Billing payment method")
    unit_of_work.billing_payment_methods.soft_delete(method_id=method_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
