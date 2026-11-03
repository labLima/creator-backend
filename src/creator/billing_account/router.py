"""HTTP routes for the billing_account capability.

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
from creator.billing_account import service
from creator.billing_account.schemas import (
    BillingAccountCreateRequest,
    BillingAccountUpdateRequest,
    BillingAddressCreateRequest,
    BillingAddressUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/billing-addresses", tags=["Billing"])
def list_billing_addresses(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    billing_account_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_billing_addresses(
            uow=unit_of_work,
            actor=current_user,
            billing_account_id=billing_account_id,
            request=request,
        ),
        request,
    )


@router.post("/api/v1/billing-addresses", tags=["Billing"])
def create_billing_address(
    payload: BillingAddressCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_billing_address(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/billing-addresses/{id}", tags=["Billing"])
def get_billing_address(
    address_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_billing_address(
            uow=unit_of_work, actor=current_user, address_id=address_id, request=request
        ),
        request,
    )


@router.put("/api/v1/billing-addresses/{id}", tags=["Billing"])
def update_billing_address(
    address_id: Annotated[UUID, Path(alias="id")],
    payload: BillingAddressUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_billing_address(
            uow=unit_of_work,
            actor=current_user,
            address_id=address_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/billing-addresses/{id}", tags=["Billing"])
def delete_billing_address(
    address_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_billing_address(
            uow=unit_of_work, actor=current_user, address_id=address_id, request=request
        ),
        request,
    )


@router.get("/api/v1/billing-accounts", tags=["Billing"])
def list_billing_accounts(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_billing_accounts(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/billing-accounts", tags=["Billing"])
def create_billing_account(
    payload: BillingAccountCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_billing_account(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/billing-accounts/{id}", tags=["Billing"])
def get_billing_account(
    account_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_billing_account(
            uow=unit_of_work, actor=current_user, account_id=account_id, request=request
        ),
        request,
    )


@router.put("/api/v1/billing-accounts/{id}", tags=["Billing"])
def update_billing_account(
    account_id: Annotated[UUID, Path(alias="id")],
    payload: BillingAccountUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_billing_account(
            uow=unit_of_work,
            actor=current_user,
            account_id=account_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/billing-accounts/{id}", tags=["Billing"])
def delete_billing_account(
    account_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_billing_account(
            uow=unit_of_work, actor=current_user, account_id=account_id, request=request
        ),
        request,
    )
