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
from creator.api.responses import (
    success_response,
)
from creator.refund import service
from creator.refund.schemas import (
    RefundCreateRequest,
    RefundUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/refunds", tags=["Billing"])
def list_refunds(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_refunds(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/refunds", tags=["Billing"])
def create_refund(
    payload: RefundCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_refund(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/refunds/{id}", tags=["Billing"])
def get_refund(
    refund_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_refund(
            uow=unit_of_work, actor=current_user, refund_id=refund_id, request=request
        ),
        request,
    )


@router.put("/api/v1/refunds/{id}", tags=["Billing"])
def update_refund(
    refund_id: Annotated[UUID, Path(alias="id")],
    payload: RefundUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_refund(
            uow=unit_of_work,
            actor=current_user,
            refund_id=refund_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/refunds/{id}", tags=["Billing"])
def delete_refund(
    refund_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_refund(
            uow=unit_of_work, actor=current_user, refund_id=refund_id, request=request
        ),
        request,
    )
