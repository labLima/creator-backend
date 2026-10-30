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
from creator.api.errors import (
    not_found,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _charge_data,
)
from creator.charge.schemas import (
    ChargeCreateRequest,
    ChargeUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/charges", tags=["Billing"])
def list_charges(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _charge_data(x) for x in unit_of_work.charges.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/charges", tags=["Billing"])
def create_charge(
    payload: ChargeCreateRequest,
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
    item = unit_of_work.charges.add(**payload.model_dump())
    unit_of_work.commit()
    return success_response(_charge_data(item), request, status_code=201)


@router.get("/api/v1/charges/{id}", tags=["Billing"])
def get_charge(
    charge_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.charges.get_for_user(user_id=current_user.id, charge_id=charge_id)
    if item is None:
        raise not_found("Charge")
    return success_response(_charge_data(item), request)


@router.put("/api/v1/charges/{id}", tags=["Billing"])
def update_charge(
    charge_id: Annotated[UUID, Path(alias="id")],
    payload: ChargeUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.charges.get_for_user(user_id=current_user.id, charge_id=charge_id) is None:
        raise not_found("Charge")
    item = unit_of_work.charges.update(
        charge_id=charge_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_charge_data(item), request)


@router.delete("/api/v1/charges/{id}", tags=["Billing"])
def delete_charge(
    charge_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if unit_of_work.charges.get_for_user(user_id=current_user.id, charge_id=charge_id) is None:
        raise not_found("Charge")
    unit_of_work.charges.soft_delete(charge_id=charge_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
