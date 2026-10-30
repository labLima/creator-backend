"""Persistence ports owned by the billing_provider capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderCustomerRecord:
    id: UUID
    billing_account_id: UUID
    provider: str
    provider_customer_id: str
    provider_code: str | None
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ProviderCustomerRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[ProviderCustomerRecord]: ...
    def get_for_user(self, *, user_id: UUID, record_id: UUID) -> ProviderCustomerRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> ProviderCustomerRecord: ...
    def update(self, *, record_id: UUID, fields: dict[str, object]) -> ProviderCustomerRecord: ...
    def soft_delete(self, *, record_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class ProviderSubscriptionRecord:
    id: UUID
    subscription_id: UUID
    provider: str
    provider_subscription_id: str
    provider_status: str | None
    payload: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ProviderSubscriptionRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[ProviderSubscriptionRecord]: ...
    def get_for_user(
        self, *, user_id: UUID, record_id: UUID
    ) -> ProviderSubscriptionRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> ProviderSubscriptionRecord: ...
    def update(
        self, *, record_id: UUID, fields: dict[str, object]
    ) -> ProviderSubscriptionRecord: ...
    def soft_delete(self, *, record_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class ProviderWebhookEventRecord:
    id: UUID
    provider: str
    provider_event_id: str
    dedupe_key: str
    event_type: str
    account_id: str | None
    resource_type: str | None
    resource_id: str | None
    payload: dict[str, object]
    signature_verified: bool
    status: str
    attempts: int
    last_error: str | None
    received_at: datetime
    processed_at: datetime | None


class ProviderWebhookEventRepository(Protocol):
    def list(self) -> list[ProviderWebhookEventRecord]: ...
    def get(self, *, event_id: UUID) -> ProviderWebhookEventRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> ProviderWebhookEventRecord: ...
    def update(
        self, *, event_id: UUID, fields: dict[str, object]
    ) -> ProviderWebhookEventRecord: ...


@dataclass(frozen=True, slots=True)
class ProviderIdempotencyKeyRecord:
    id: UUID
    provider: str
    idempotency_key: str
    request_hash: str | None
    resource_type: str | None
    resource_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ProviderIdempotencyKeyRepository(Protocol):
    def list(self) -> list[ProviderIdempotencyKeyRecord]: ...
    def get(self, *, key_id: UUID) -> ProviderIdempotencyKeyRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> ProviderIdempotencyKeyRecord: ...
    def update(
        self, *, key_id: UUID, fields: dict[str, object]
    ) -> ProviderIdempotencyKeyRecord: ...


@dataclass(frozen=True, slots=True)
class ProviderDisputeRecord:
    id: UUID
    billing_account_id: UUID
    charge_id: UUID | None
    code: str | None
    reason: str | None
    status: str
    opened_at: datetime | None
    deadline_at: datetime | None
    payload: dict[str, object]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ProviderDisputeRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[ProviderDisputeRecord]: ...
    def get_for_user(self, *, user_id: UUID, dispute_id: UUID) -> ProviderDisputeRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> ProviderDisputeRecord: ...
    def update(self, *, dispute_id: UUID, fields: dict[str, object]) -> ProviderDisputeRecord: ...
    def soft_delete(self, *, dispute_id: UUID) -> None: ...
