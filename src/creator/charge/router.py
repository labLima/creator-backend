"""HTTP routes for the charge capability.

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
from creator.charge import service
from creator.charge.schemas import (
    ChargeCreateRequest,
    ChargeUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/charges", tags=["Billing"], operation_id="list_charges_api_v1_charges_get")
def list_charges(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_charges(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/charges", tags=["Billing"], operation_id="create_charge_api_v1_charges_post")
def create_charge(
    payload: ChargeCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_charge(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get(
    "/api/v1/charges/{id}", tags=["Billing"], operation_id="get_charge_api_v1_charges__id__get"
)
def get_charge(
    charge_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_charge(
            uow=unit_of_work, actor=current_user, charge_id=charge_id, request=request
        ),
        request,
    )


@router.put(
    "/api/v1/charges/{id}", tags=["Billing"], operation_id="update_charge_api_v1_charges__id__put"
)
def update_charge(
    charge_id: Annotated[UUID, Path(alias="id")],
    payload: ChargeUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_charge(
            uow=unit_of_work,
            actor=current_user,
            charge_id=charge_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete(
    "/api/v1/charges/{id}",
    tags=["Billing"],
    operation_id="delete_charge_api_v1_charges__id__delete",
)
def delete_charge(
    charge_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_charge(
            uow=unit_of_work, actor=current_user, charge_id=charge_id, request=request
        ),
        request,
    )
