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
from creator.api.responses import (
    success_response,
)
from creator.billing_provider import service
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
        service.list_provider_customers(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/provider-customers", tags=["Billing"])
def create_provider_customer(
    payload: ProviderCustomerCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_provider_customer(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/provider-customers/{id}", tags=["Billing"])
def get_provider_customer(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_provider_customer(
            uow=unit_of_work, actor=current_user, record_id=record_id, request=request
        ),
        request,
    )


@router.delete("/api/v1/provider-customers/{id}", tags=["Billing"])
def delete_provider_customer(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_provider_customer(
            uow=unit_of_work, actor=current_user, record_id=record_id, request=request
        ),
        request,
    )


@router.put("/api/v1/provider-customers/{id}", tags=["Billing"])
def update_provider_customer(
    record_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_provider_customer(
            uow=unit_of_work,
            actor=current_user,
            record_id=record_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.get("/api/v1/provider-subscriptions", tags=["Billing"])
def list_provider_subscriptions(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_provider_subscriptions(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/provider-subscriptions", tags=["Billing"])
def create_provider_subscription(
    payload: ProviderSubscriptionCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_provider_subscription(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/provider-subscriptions/{id}", tags=["Billing"])
def get_provider_subscription(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_provider_subscription(
            uow=unit_of_work, actor=current_user, record_id=record_id, request=request
        ),
        request,
    )


@router.delete("/api/v1/provider-subscriptions/{id}", tags=["Billing"])
def delete_provider_subscription(
    record_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_provider_subscription(
            uow=unit_of_work, actor=current_user, record_id=record_id, request=request
        ),
        request,
    )


@router.get("/api/v1/provider-webhook-events", tags=["Billing"])
def list_provider_webhook_events(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_provider_webhook_events(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/provider-webhook-events", tags=["Billing"])
def create_provider_webhook_event(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_provider_webhook_event(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/provider-webhook-events/{id}", tags=["Billing"])
def get_provider_webhook_event(
    event_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_provider_webhook_event(
            uow=unit_of_work, actor=current_user, event_id=event_id, request=request
        ),
        request,
    )


@router.put("/api/v1/provider-webhook-events/{id}", tags=["Billing"])
def update_provider_webhook_event(
    event_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_provider_webhook_event(
            uow=unit_of_work,
            actor=current_user,
            event_id=event_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/provider-webhook-events/{id}", tags=["Billing"])
def delete_provider_webhook_event(
    event_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_provider_webhook_event(
            uow=unit_of_work, actor=current_user, event_id=event_id, request=request
        ),
        request,
    )


@router.get("/api/v1/provider-idempotency-keys", tags=["Billing"])
def list_provider_idempotency_keys(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_provider_idempotency_keys(
            uow=unit_of_work, actor=current_user, request=request
        ),
        request,
    )


@router.post("/api/v1/provider-idempotency-keys", tags=["Billing"])
def create_provider_idempotency_key(
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_provider_idempotency_key(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/provider-idempotency-keys/{id}", tags=["Billing"])
def get_provider_idempotency_key(
    key_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_provider_idempotency_key(
            uow=unit_of_work, actor=current_user, key_id=key_id, request=request
        ),
        request,
    )


@router.put("/api/v1/provider-idempotency-keys/{id}", tags=["Billing"])
def update_provider_idempotency_key(
    key_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_provider_idempotency_key(
            uow=unit_of_work, actor=current_user, key_id=key_id, payload=payload, request=request
        ),
        request,
    )


@router.delete("/api/v1/provider-idempotency-keys/{id}", tags=["Billing"])
def delete_provider_idempotency_key(
    key_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_provider_idempotency_key(
            uow=unit_of_work, actor=current_user, key_id=key_id, request=request
        ),
        request,
    )


@router.put("/api/v1/provider-subscriptions/{id}", tags=["Billing"])
def update_provider_subscription(
    record_id: Annotated[UUID, Path(alias="id")],
    payload: dict[str, Any],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_provider_subscription(
            uow=unit_of_work,
            actor=current_user,
            record_id=record_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.get("/api/v1/provider-disputes", tags=["Billing"])
def list_provider_disputes(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.list_provider_disputes(uow=unit_of_work, actor=current_user, request=request),
        request,
    )


@router.post("/api/v1/provider-disputes", tags=["Billing"])
def create_provider_dispute(
    payload: ProviderDisputeCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_provider_dispute(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/provider-disputes/{id}", tags=["Billing"])
def get_provider_dispute(
    dispute_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_provider_dispute(
            uow=unit_of_work, actor=current_user, dispute_id=dispute_id, request=request
        ),
        request,
    )


@router.put("/api/v1/provider-disputes/{id}", tags=["Billing"])
def update_provider_dispute(
    dispute_id: Annotated[UUID, Path(alias="id")],
    payload: ProviderDisputeUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.update_provider_dispute(
            uow=unit_of_work,
            actor=current_user,
            dispute_id=dispute_id,
            payload=payload,
            request=request,
        ),
        request,
    )


@router.delete("/api/v1/provider-disputes/{id}", tags=["Billing"])
def delete_provider_dispute(
    dispute_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_provider_dispute(
            uow=unit_of_work, actor=current_user, dispute_id=dispute_id, request=request
        ),
        request,
    )
