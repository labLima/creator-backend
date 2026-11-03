"""HTTP routes for the coupon capability.

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
from creator.coupon import service
from creator.coupon.schemas import (
    CouponCreateRequest,
    CouponRedemptionCreateRequest,
    CouponRedemptionUpdateRequest,
    CouponUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/coupon-redemptions", tags=["Billing"])
def list_coupon_redemptions(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_coupon_redemptions(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/coupon-redemptions", tags=["Billing"])
def create_coupon_redemption(
    payload: CouponRedemptionCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_coupon_redemption(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/coupon-redemptions/{id}", tags=["Billing"])
def get_coupon_redemption(
    redemption_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_coupon_redemption(
            uow=unit_of_work, actor=current_user, redemption_id=redemption_id, request=request
        ),
        request,
    )


@router.put("/api/v1/coupon-redemptions/{id}", tags=["Billing"])
def update_coupon_redemption(
    redemption_id: Annotated[UUID, Path(alias="id")],
    payload: CouponRedemptionUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_coupon_redemption(
            uow=unit_of_work,
            actor=current_user,
            redemption_id=redemption_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/coupon-redemptions/{id}", tags=["Billing"])
def delete_coupon_redemption(
    redemption_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_coupon_redemption(
            uow=unit_of_work, actor=current_user, redemption_id=redemption_id, request=request
        ),
        request,
    )


@router.get("/api/v1/coupons", tags=["Billing"])
def list_coupons(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_coupons(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/coupons", tags=["Billing"])
def create_coupon(
    payload: CouponCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_coupon(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/coupons/{id}", tags=["Billing"])
def get_coupon(
    coupon_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_coupon(
            uow=unit_of_work, actor=current_user, coupon_id=coupon_id, request=request
        ),
        request,
    )


@router.put("/api/v1/coupons/{id}", tags=["Billing"])
def update_coupon(
    coupon_id: Annotated[UUID, Path(alias="id")],
    payload: CouponUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_coupon(
            uow=unit_of_work,
            actor=current_user,
            coupon_id=coupon_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/coupons/{id}", tags=["Billing"])
def delete_coupon(
    coupon_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_coupon(
            uow=unit_of_work, actor=current_user, coupon_id=coupon_id, request=request
        ),
        request,
    )
