"""HTTP routes for the billing_provider capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated, Any
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
    _provider_customer_data,
    _provider_dispute_data,
    _provider_idempotency_key_data,
    _provider_subscription_data,
    _provider_webhook_event_data,
)
from creator.billing_provider.schemas import (
    ProviderCustomerCreateRequest,
    ProviderDisputeCreateRequest,
    ProviderDisputeUpdateRequest,
    ProviderSubscriptionCreateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/provider-customers", tags=["Billing"])
def list_provider_customers(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _provider_customer_data(x)
                for x in unit_of_work.provider_customers.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/provider-customers", tags=["Billing"])
def create_provider_customer(
    payload: ProviderCustomerCreateRequest,
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
    data["metadata_json"] = data.pop("metadata")
    item = unit_of_work.provider_customers.add(fields=data)
    unit_of_work.commit()
    return success_response(_provider_customer_data(item), request, status_code=201)


@router.get("/api/v1/provider-customers/{id}", tags=["Billing"])
def get_provider_customer(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.provider_customers.get_for_user(
        user_id=current_user.id, record_id=record_id
    )
    if item is None:
        raise not_found("Provider customer")
    return success_response(_provider_customer_data(item), request)


@router.delete("/api/v1/provider-customers/{id}", tags=["Billing"])
def delete_provider_customer(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.provider_customers.get_for_user(user_id=current_user.id, record_id=record_id)
        is None
    ):
        raise not_found("Provider customer")
    unit_of_work.provider_customers.soft_delete(record_id=record_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.put("/api/v1/provider-customers/{id}", tags=["Billing"])
def update_provider_customer(
    record_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.provider_customers.get_for_user(user_id=current_user.id, record_id=record_id)
        is None
    ):
        raise not_found("Provider customer")
    item = unit_of_work.provider_customers.update(record_id=record_id, fields=payload)
    unit_of_work.commit()
    return success_response(_provider_customer_data(item), request)


@router.get("/api/v1/provider-subscriptions", tags=["Billing"])
def list_provider_subscriptions(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _provider_subscription_data(x)
                for x in unit_of_work.provider_subscriptions.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/provider-subscriptions", tags=["Billing"])
def create_provider_subscription(
    payload: ProviderSubscriptionCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.subscriptions.get_for_user(
            user_id=current_user.id, subscription_id=payload.subscription_id
        )
        is None
    ):
        raise not_found("Subscription")
    data = payload.model_dump()
    data["payload"] = data.pop("payload")
    item = unit_of_work.provider_subscriptions.add(fields=data)
    unit_of_work.commit()
    return success_response(_provider_subscription_data(item), request, status_code=201)


@router.get("/api/v1/provider-subscriptions/{id}", tags=["Billing"])
def get_provider_subscription(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.provider_subscriptions.get_for_user(
        user_id=current_user.id, record_id=record_id
    )
    if item is None:
        raise not_found("Provider subscription")
    return success_response(_provider_subscription_data(item), request)


@router.delete("/api/v1/provider-subscriptions/{id}", tags=["Billing"])
def delete_provider_subscription(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.provider_subscriptions.get_for_user(
            user_id=current_user.id, record_id=record_id
        )
        is None
    ):
        raise not_found("Provider subscription")
    unit_of_work.provider_subscriptions.soft_delete(record_id=record_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)


@router.get("/api/v1/provider-webhook-events", tags=["Billing"])
def list_provider_webhook_events(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    return success_response(
        {
            "items": [
                _provider_webhook_event_data(x) for x in unit_of_work.provider_webhook_events.list()
            ]
        },
        request,
    )


@router.post("/api/v1/provider-webhook-events", tags=["Billing"])
def create_provider_webhook_event(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.provider_webhook_events.add(fields=payload)
    unit_of_work.commit()
    return success_response(_provider_webhook_event_data(item), request, status_code=201)


@router.get("/api/v1/provider-webhook-events/{id}", tags=["Billing"])
def get_provider_webhook_event(
    event_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.provider_webhook_events.get(event_id=event_id)
    if item is None:
        raise not_found("Provider webhook event")
    return success_response(_provider_webhook_event_data(item), request)


@router.put("/api/v1/provider-webhook-events/{id}", tags=["Billing"])
def update_provider_webhook_event(
    event_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.provider_webhook_events.get(event_id=event_id) is None:
        raise not_found("Provider webhook event")
    item = unit_of_work.provider_webhook_events.update(event_id=event_id, fields=payload)
    unit_of_work.commit()
    return success_response(_provider_webhook_event_data(item), request)


@router.delete("/api/v1/provider-webhook-events/{id}", tags=["Billing"])
def delete_provider_webhook_event(
    event_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.provider_webhook_events.get(event_id=event_id)
    if item is None:
        raise not_found("Provider webhook event")
    updated = unit_of_work.provider_webhook_events.update(
        event_id=event_id, fields={"status": "deleted"}
    )
    unit_of_work.commit()
    return success_response(_provider_webhook_event_data(updated), request)


@router.get("/api/v1/provider-idempotency-keys", tags=["Billing"])
def list_provider_idempotency_keys(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    return success_response(
        {
            "items": [
                _provider_idempotency_key_data(x)
                for x in unit_of_work.provider_idempotency_keys.list()
            ]
        },
        request,
    )


@router.post("/api/v1/provider-idempotency-keys", tags=["Billing"])
def create_provider_idempotency_key(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.provider_idempotency_keys.add(fields=payload)
    unit_of_work.commit()
    return success_response(_provider_idempotency_key_data(item), request, status_code=201)


@router.get("/api/v1/provider-idempotency-keys/{id}", tags=["Billing"])
def get_provider_idempotency_key(
    key_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    item = unit_of_work.provider_idempotency_keys.get(key_id=key_id)
    if item is None:
        raise not_found("Provider idempotency key")
    return success_response(_provider_idempotency_key_data(item), request)


@router.put("/api/v1/provider-idempotency-keys/{id}", tags=["Billing"])
def update_provider_idempotency_key(
    key_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.provider_idempotency_keys.get(key_id=key_id) is None:
        raise not_found("Provider idempotency key")
    item = unit_of_work.provider_idempotency_keys.update(key_id=key_id, fields=payload)
    unit_of_work.commit()
    return success_response(_provider_idempotency_key_data(item), request)


@router.delete("/api/v1/provider-idempotency-keys/{id}", tags=["Billing"])
def delete_provider_idempotency_key(
    key_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_global_billing_admin(current_user)
    if unit_of_work.provider_idempotency_keys.get(key_id=key_id) is None:
        raise not_found("Provider idempotency key")
    item = unit_of_work.provider_idempotency_keys.update(
        key_id=key_id, fields={"status": "deleted"}
    )
    unit_of_work.commit()
    return success_response(_provider_idempotency_key_data(item), request)


@router.put("/api/v1/provider-subscriptions/{id}", tags=["Billing"])
def update_provider_subscription(
    record_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.provider_subscriptions.get_for_user(
            user_id=current_user.id, record_id=record_id
        )
        is None
    ):
        raise not_found("Provider subscription")
    item = unit_of_work.provider_subscriptions.update(record_id=record_id, fields=payload)
    unit_of_work.commit()
    return success_response(_provider_subscription_data(item), request)


@router.get("/api/v1/provider-disputes", tags=["Billing"])
def list_provider_disputes(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        {
            "items": [
                _provider_dispute_data(x)
                for x in unit_of_work.provider_disputes.list_for_user(user_id=current_user.id)
            ]
        },
        request,
    )


@router.post("/api/v1/provider-disputes", tags=["Billing"])
def create_provider_dispute(
    payload: ProviderDisputeCreateRequest,
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
    data["status"] = "open"
    data["payload"] = {}
    item = unit_of_work.provider_disputes.add(fields=data)
    unit_of_work.commit()
    return success_response(_provider_dispute_data(item), request, status_code=201)


@router.get("/api/v1/provider-disputes/{id}", tags=["Billing"])
def get_provider_dispute(
    dispute_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.provider_disputes.get_for_user(
        user_id=current_user.id, dispute_id=dispute_id
    )
    if item is None:
        raise not_found("Provider dispute")
    return success_response(_provider_dispute_data(item), request)


@router.put("/api/v1/provider-disputes/{id}", tags=["Billing"])
def update_provider_dispute(
    dispute_id: Annotated[UUID, Path(alias="id")],
    payload: ProviderDisputeUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.provider_disputes.get_for_user(user_id=current_user.id, dispute_id=dispute_id)
        is None
    ):
        raise not_found("Provider dispute")
    item = unit_of_work.provider_disputes.update(
        dispute_id=dispute_id, fields=payload.model_dump(exclude_unset=True)
    )
    unit_of_work.commit()
    return success_response(_provider_dispute_data(item), request)


@router.delete("/api/v1/provider-disputes/{id}", tags=["Billing"])
def delete_provider_dispute(
    dispute_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.provider_disputes.get_for_user(user_id=current_user.id, dispute_id=dispute_id)
        is None
    ):
        raise not_found("Provider dispute")
    unit_of_work.provider_disputes.soft_delete(dispute_id=dispute_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
