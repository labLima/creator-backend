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
from creator.api.errors import (
    not_found,
    require_global_billing_admin,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _coupon_data,
    _coupon_redemption_data,
)
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
        {
            "items": [
                _coupon_redemption_data(x)
                for x in unit_of_work.coupon_redemptions.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/coupon-redemptions", tags=["Billing"])
def create_coupon_redemption(
    payload: CouponRedemptionCreateRequest,
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
    data["status"] = "applied"
    item = unit_of_work.coupon_redemptions.add(fields=data)
    unit_of_work.commit()
    return success_response(_coupon_redemption_data(item), request, status_code=201)


@router.get("/api/v1/coupon-redemptions/{id}", tags=["Billing"])
def get_coupon_redemption(
    redemption_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.coupon_redemptions.get_for_user(
        user_id=current_user.id, redemption_id=redemption_id
    )
    if item is None:
        raise not_found("Coupon redemption")
    return success_response(_coupon_redemption_data(item), request)


@router.put("/api/v1/coupon-redemptions/{id}", tags=["Billing"])
def update_coupon_redemption(
    redemption_id: Annotated[UUID, Path(alias="id")],
    payload: CouponRedemptionUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.coupon_redemptions.get_for_user(
            user_id=current_user.id, redemption_id=redemption_id
        )
        is None
    ):
        raise not_found("Coupon redemption")
    item = unit_of_work.coupon_redemptions.update(
        redemption_id=redemption_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_coupon_redemption_data(item), request)


@router.delete("/api/v1/coupon-redemptions/{id}", tags=["Billing"])
def delete_coupon_redemption(
    redemption_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.coupon_redemptions.get_for_user(
            user_id=current_user.id, redemption_id=redemption_id
        )
        is None
    ):
        raise not_found("Coupon redemption")
    unit_of_work.coupon_redemptions.soft_delete(redemption_id=redemption_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/coupons", tags=["Billing"])
def list_coupons(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    return success_response(
        {"items": [_coupon_data(x) for x in unit_of_work.coupons.list()]}, request
    )


@router.post("/api/v1/coupons", tags=["Billing"])
def create_coupon(
    payload: CouponCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    data = payload.model_dump()
    data["created_by"] = current_user.id
    item = unit_of_work.coupons.add(fields=data)
    unit_of_work.commit()
    return success_response(_coupon_data(item), request, status_code=201)


@router.get("/api/v1/coupons/{id}", tags=["Billing"])
def get_coupon(
    coupon_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.coupons.get(coupon_id=coupon_id)
    if item is None:
        raise not_found("Coupon")
    return success_response(_coupon_data(item), request)


@router.put("/api/v1/coupons/{id}", tags=["Billing"])
def update_coupon(
    coupon_id: Annotated[UUID, Path(alias="id")],
    payload: CouponUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.coupons.get(coupon_id=coupon_id) is None:
        raise not_found("Coupon")
    item = unit_of_work.coupons.update(
        coupon_id=coupon_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_coupon_data(item), request)


@router.delete("/api/v1/coupons/{id}", tags=["Billing"])
def delete_coupon(
    coupon_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.coupons.get(coupon_id=coupon_id) is None:
        raise not_found("Coupon")
    unit_of_work.coupons.soft_delete(coupon_id=coupon_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
