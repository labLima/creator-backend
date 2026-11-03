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
from creator.api.responses import (
    success_response,
)
from creator.credit_package import service
from creator.credit_package.schemas import (
    CreditPackageCreateRequest,
    CreditPackageUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/credit-packages", tags=["Billing"])
def list_credit_packages(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_credit_packages(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/credit-packages", tags=["Billing"])
def create_credit_package(
    payload: CreditPackageCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_credit_package(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/credit-packages/{id}", tags=["Billing"])
def get_credit_package(
    package_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_credit_package(
            uow=unit_of_work, actor=current_user, package_id=package_id, request=request
        ),
        request,
    )


@router.put("/api/v1/credit-packages/{id}", tags=["Billing"])
def update_credit_package(
    package_id: Annotated[UUID, Path(alias="id")],
    payload: CreditPackageUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_credit_package(
            uow=unit_of_work,
            actor=current_user,
            package_id=package_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/credit-packages/{id}", tags=["Billing"])
def delete_credit_package(
    package_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_credit_package(
            uow=unit_of_work, actor=current_user, package_id=package_id, request=request
        ),
        request,
    )
