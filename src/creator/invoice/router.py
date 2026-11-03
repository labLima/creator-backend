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
from creator.api.responses import (
    success_response,
)
from creator.invoice import service
from creator.invoice.schemas import (
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/invoices", tags=["Billing"])
def list_invoices(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_invoices(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/invoices", tags=["Billing"])
def create_invoice(
    payload: InvoiceCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_invoice(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/invoices/{id}", tags=["Billing"])
def get_invoice(
    invoice_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_invoice(
            uow=unit_of_work, actor=current_user, invoice_id=invoice_id, request=request
        ),
        request,
    )


@router.put("/api/v1/invoices/{id}", tags=["Billing"])
def update_invoice(
    invoice_id: Annotated[UUID, Path(alias="id")],
    payload: InvoiceUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_invoice(
            uow=unit_of_work,
            actor=current_user,
            invoice_id=invoice_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/invoices/{id}", tags=["Billing"])
def delete_invoice(
    invoice_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_invoice(
            uow=unit_of_work, actor=current_user, invoice_id=invoice_id, request=request
        ),
        request,
    )
