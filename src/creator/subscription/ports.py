"""Persistence ports owned by the subscription capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SubscriptionRecord:
    id: UUID
    billing_account_id: UUID
    workspace_id: UUID
    plan_id: UUID
    status: str
    payment_method: str | None
    billing_day: int | None
    start_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class SubscriptionRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[SubscriptionRecord]: ...
    def get_for_user(
        self, *, user_id: UUID, subscription_id: UUID
    ) -> SubscriptionRecord | None: ...
    def add(
        self,
        *,
        billing_account_id: UUID,
        workspace_id: UUID,
        plan_id: UUID,
        payment_method: str | None,
        billing_day: int | None,
        start_at: datetime | None,
    ) -> SubscriptionRecord: ...
    def update(self, *, subscription_id: UUID, fields: dict[str, object]) -> SubscriptionRecord: ...
    def soft_delete(self, *, subscription_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class SubscriptionHistoryRecord:
    id: UUID
    subscription_id: UUID
    change_type: str
    previous_plan_id: UUID | None
    plan_id: UUID | None
    previous_status: str | None
    status: str | None
    reason: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class SubscriptionHistoryRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[SubscriptionHistoryRecord]: ...
    def get_for_user(
        self, *, user_id: UUID, history_id: UUID
    ) -> SubscriptionHistoryRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> SubscriptionHistoryRecord: ...
    def update(
        self, *, history_id: UUID, fields: dict[str, object]
    ) -> SubscriptionHistoryRecord: ...
    def soft_delete(self, *, history_id: UUID) -> None: ...
