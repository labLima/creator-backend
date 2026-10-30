"""Use cases for the coupon capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_global_billing_admin
from creator.api.serializers import _coupon_data, _coupon_redemption_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_coupon_redemptions(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    return {
        "items": [
            _coupon_redemption_data(x)
            for x in uow.coupon_redemptions.list_for_user(user_id=actor.id)
        ]
    }


def create_coupon_redemption(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    if (
        uow.billing_accounts.get_for_user(user_id=actor.id, account_id=payload.billing_account_id)
        is None
    ):
        raise not_found("Billing account")
    data = payload.model_dump()
    data["status"] = "applied"
    item = uow.coupon_redemptions.add(fields=data)
    uow.commit()

    return _coupon_redemption_data(item)


def get_coupon_redemption(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    redemption_id: Any,
) -> Any:
    item = uow.coupon_redemptions.get_for_user(user_id=actor.id, redemption_id=redemption_id)
    if item is None:
        raise not_found("Coupon redemption")

    return _coupon_redemption_data(item)


def update_coupon_redemption(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    redemption_id: Any,
    payload: Any,
) -> Any:
    if uow.coupon_redemptions.get_for_user(user_id=actor.id, redemption_id=redemption_id) is None:
        raise not_found("Coupon redemption")
    item = uow.coupon_redemptions.update(
        redemption_id=redemption_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _coupon_redemption_data(item)


def delete_coupon_redemption(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    redemption_id: Any,
) -> Any:
    if uow.coupon_redemptions.get_for_user(user_id=actor.id, redemption_id=redemption_id) is None:
        raise not_found("Coupon redemption")
    uow.coupon_redemptions.soft_delete(redemption_id=redemption_id)
    uow.commit()

    return {"deleted": True}


def list_coupons(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    require_global_billing_admin(actor)

    return {"items": [_coupon_data(x) for x in uow.coupons.list()]}


def create_coupon(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    data = payload.model_dump()
    data["created_by"] = actor.id
    item = uow.coupons.add(fields=data)
    uow.commit()

    return _coupon_data(item)


def get_coupon(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    coupon_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.coupons.get(coupon_id=coupon_id)
    if item is None:
        raise not_found("Coupon")

    return _coupon_data(item)


def update_coupon(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    coupon_id: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.coupons.get(coupon_id=coupon_id) is None:
        raise not_found("Coupon")
    item = uow.coupons.update(coupon_id=coupon_id, fields=payload.model_dump(exclude_unset=True))
    uow.commit()

    return _coupon_data(item)


def delete_coupon(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    coupon_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.coupons.get(coupon_id=coupon_id) is None:
        raise not_found("Coupon")
    uow.coupons.soft_delete(coupon_id=coupon_id)
    uow.commit()

    return {"deleted": True}
