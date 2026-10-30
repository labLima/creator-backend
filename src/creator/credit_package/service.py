"""Use cases for the credit_package capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_global_billing_admin
from creator.api.serializers import _credit_package_data
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_credit_packages(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
) -> Any:
    require_global_billing_admin(actor)

    return {"items": [_credit_package_data(x) for x in uow.credit_packages.list()]}


def create_credit_package(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.credit_packages.add(fields=payload.model_dump())
    uow.commit()

    return _credit_package_data(item)


def get_credit_package(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    package_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    item = uow.credit_packages.get(package_id=package_id)
    if item is None:
        raise not_found("Credit package")

    return _credit_package_data(item)


def update_credit_package(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    package_id: Any,
    payload: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.credit_packages.get(package_id=package_id) is None:
        raise not_found("Credit package")
    item = uow.credit_packages.update(
        package_id=package_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _credit_package_data(item)


def delete_credit_package(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    package_id: Any,
) -> Any:
    require_global_billing_admin(actor)
    if uow.credit_packages.get(package_id=package_id) is None:
        raise not_found("Credit package")
    uow.credit_packages.soft_delete(package_id=package_id)
    uow.commit()

    return {"deleted": True}
