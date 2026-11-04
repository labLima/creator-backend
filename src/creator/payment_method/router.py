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
from creator.api.responses import (
    success_response,
)
from creator.payment_method import service
from creator.payment_method.schemas import (
    PaymentMethodCreateRequest,
    PaymentMethodUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get(
    "/api/v1/billing-payment-methods",
    tags=["Billing"],
    operation_id="list_payment_methods_api_v1_billing_payment_methods_get",
)
def list_payment_methods(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    billing_account_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_payment_methods(
            uow=unit_of_work,
            actor=current_user,
            billing_account_id=billing_account_id,
            request=request,
        ),
        request,
    )


@router.post(
    "/api/v1/billing-payment-methods",
    tags=["Billing"],
    operation_id="create_payment_method_api_v1_billing_payment_methods_post",
)
def create_payment_method(
    payload: PaymentMethodCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_payment_method(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/billing-payment-methods/{id}",
    tags=["Billing"],
    operation_id="get_payment_method_api_v1_billing_payment_methods__id__get",
)
def get_payment_method(
    method_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_payment_method(
            uow=unit_of_work, actor=current_user, method_id=method_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/billing-payment-methods/{id}",
    tags=["Billing"],
    operation_id="update_payment_method_api_v1_billing_payment_methods__id__put",
)
def update_payment_method(
    method_id: Annotated[UUID, Path(alias="id")],
    payload: PaymentMethodUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_payment_method(
            uow=unit_of_work,
            actor=current_user,
            method_id=method_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/billing-payment-methods/{id}",
    tags=["Billing"],
    operation_id="delete_payment_method_api_v1_billing_payment_methods__id__delete",
)
def delete_payment_method(
    method_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_payment_method(
            uow=unit_of_work, actor=current_user, method_id=method_id, request=request
        ),
        request,
    )
