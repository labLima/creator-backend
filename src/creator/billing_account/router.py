"""HTTP routes for the billing_account capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request
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
    _billing_account_data,
    _billing_address_data,
)
from creator.billing_account.schemas import (
    BillingAccountCreateRequest,
    BillingAccountUpdateRequest,
    BillingAddressCreateRequest,
    BillingAddressUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

router = APIRouter()


@router.get("/api/v1/billing-addresses", tags=["Billing"])
def list_billing_addresses(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    billing_account_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _billing_address_data(x)
                for x in unit_of_work.billing_addresses.list_for_user(
                    user_id=current_user.id, account_id=billing_account_id
                )
            ]
        },
        request,
    )


@router.post("/api/v1/billing-addresses", tags=["Billing"])
def create_billing_address(
    payload: BillingAddressCreateRequest,
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
    item = unit_of_work.billing_addresses.add(billing_account_id=account_id, fields=data)
    unit_of_work.commit()
    return success_response(_billing_address_data(item), request, status_code=201)


@router.get("/api/v1/billing-addresses/{id}", tags=["Billing"])
def get_billing_address(
    address_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.billing_addresses.get_for_user(
        user_id=current_user.id, address_id=address_id
    )
    if item is None:
        raise not_found("Billing address")
    return success_response(_billing_address_data(item), request)


@router.put("/api/v1/billing-addresses/{id}", tags=["Billing"])
def update_billing_address(
    address_id: Annotated[UUID, Path(alias="id")],
    payload: BillingAddressUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.billing_addresses.get_for_user(user_id=current_user.id, address_id=address_id)
        is None
    ):
        raise not_found("Billing address")
    item = unit_of_work.billing_addresses.update(
        address_id=address_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_billing_address_data(item), request)


@router.delete("/api/v1/billing-addresses/{id}", tags=["Billing"])
def delete_billing_address(
    address_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.billing_addresses.get_for_user(user_id=current_user.id, address_id=address_id)
        is None
    ):
        raise not_found("Billing address")
    unit_of_work.billing_addresses.soft_delete(address_id=address_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/billing-accounts", tags=["Billing"])
def list_billing_accounts(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    items = unit_of_work.billing_accounts.list_for_user(user_id=current_user.id)
    return success_response({"items": [_billing_account_data(item) for item in items]}, request)


@router.post("/api/v1/billing-accounts", tags=["Billing"])
def create_billing_account(
    payload: BillingAccountCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if payload.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Billing account belongs to another Principal")
    item = unit_of_work.billing_accounts.add(
        user_id=current_user.id,
        payer_type=payload.payer_type,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        document=payload.document,
        document_type=payload.document_type,
    )
    unit_of_work.commit()
    return success_response(_billing_account_data(item), request, status_code=201)


@router.get("/api/v1/billing-accounts/{id}", tags=["Billing"])
def get_billing_account(
    account_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.billing_accounts.get_for_user(
        user_id=current_user.id, account_id=account_id
    )
    if item is None:
        raise not_found("Billing account")
    return success_response(_billing_account_data(item), request)


@router.put("/api/v1/billing-accounts/{id}", tags=["Billing"])
def update_billing_account(
    account_id: Annotated[UUID, Path(alias="id")],
    payload: BillingAccountUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.billing_accounts.get_for_user(user_id=current_user.id, account_id=account_id)
        is None
    ):
        raise not_found("Billing account")
    item = unit_of_work.billing_accounts.update(
        user_id=current_user.id,
        account_id=account_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    unit_of_work.commit()
    return success_response(_billing_account_data(item), request)


@router.delete("/api/v1/billing-accounts/{id}", tags=["Billing"])
def delete_billing_account(
    account_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.billing_accounts.get_for_user(user_id=current_user.id, account_id=account_id)
        is None
    ):
        raise not_found("Billing account")
    unit_of_work.billing_accounts.soft_delete(user_id=current_user.id, account_id=account_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
