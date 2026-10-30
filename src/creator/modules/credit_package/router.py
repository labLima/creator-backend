"""HTTP routes for the credit_package capability.

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
    require_global_billing_admin,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _credit_package_data,
)
from creator.modules.credit_package.schemas import (
    CreditPackageCreateRequest,
    CreditPackageUpdateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

router = APIRouter()


@router.get("/api/v1/credit-packages", tags=["Billing"])
def list_credit_packages(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    return success_response(
        {"items": [_credit_package_data(x) for x in unit_of_work.credit_packages.list()]},
        request,
    )


@router.post("/api/v1/credit-packages", tags=["Billing"])
def create_credit_package(
    payload: CreditPackageCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.credit_packages.add(fields=payload.model_dump())
    unit_of_work.commit()
    return success_response(_credit_package_data(item), request, status_code=201)


@router.get("/api/v1/credit-packages/{id}", tags=["Billing"])
def get_credit_package(
    package_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.credit_packages.get(package_id=package_id)
    if item is None:
        raise not_found("Credit package")
    return success_response(_credit_package_data(item), request)


@router.put("/api/v1/credit-packages/{id}", tags=["Billing"])
def update_credit_package(
    package_id: Annotated[UUID, Path(alias="id")],
    payload: CreditPackageUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.credit_packages.get(package_id=package_id) is None:
        raise not_found("Credit package")
    item = unit_of_work.credit_packages.update(
        package_id=package_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_credit_package_data(item), request)


@router.delete("/api/v1/credit-packages/{id}", tags=["Billing"])
def delete_credit_package(
    package_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.credit_packages.get(package_id=package_id) is None:
        raise not_found("Credit package")
    unit_of_work.credit_packages.soft_delete(package_id=package_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
