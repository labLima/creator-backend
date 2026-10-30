"""HTTP routes for the invoice capability.

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
    _invoice_data,
)
from creator.invoice.schemas import (
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

router = APIRouter()


@router.get("/api/v1/invoices", tags=["Billing"])
def list_invoices(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _invoice_data(x)
                for x in unit_of_work.invoices.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/invoices", tags=["Billing"])
def create_invoice(
    payload: InvoiceCreateRequest,
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
    item = unit_of_work.invoices.add(**payload.model_dump())
    unit_of_work.commit()
    return success_response(_invoice_data(item), request, status_code=201)


@router.get("/api/v1/invoices/{id}", tags=["Billing"])
def get_invoice(
    invoice_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.invoices.get_for_user(user_id=current_user.id, invoice_id=invoice_id)
    if item is None:
        raise not_found("Invoice")
    return success_response(_invoice_data(item), request)


@router.put("/api/v1/invoices/{id}", tags=["Billing"])
def update_invoice(
    invoice_id: Annotated[UUID, Path(alias="id")],
    payload: InvoiceUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.invoices.get_for_user(user_id=current_user.id, invoice_id=invoice_id) is None:
        raise not_found("Invoice")
    item = unit_of_work.invoices.update(
        invoice_id=invoice_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_invoice_data(item), request)


@router.delete("/api/v1/invoices/{id}", tags=["Billing"])
def delete_invoice(
    invoice_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.invoices.get_for_user(user_id=current_user.id, invoice_id=invoice_id) is None:
        raise not_found("Invoice")
    unit_of_work.invoices.soft_delete(invoice_id=invoice_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
