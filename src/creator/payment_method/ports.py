"""Persistence ports owned by the payment_method capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BillingPaymentMethodRecord:
    id: UUID
    billing_account_id: UUID
    holder_name: str | None
    holder_document: str | None
    card_brand: str | None
    card_last_four: str | None
    exp_month: int | None
    exp_year: int | None
    card_type: str | None
    card_status: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class BillingPaymentMethodRepository(Protocol):
    def list_for_user(
        self, *, user_id: UUID, account_id: UUID | None = None
    ) -> list[BillingPaymentMethodRecord]: ...
    def get_for_user(
        self, *, user_id: UUID, method_id: UUID
    ) -> BillingPaymentMethodRecord | None: ...
    def add(
        self, *, billing_account_id: UUID, fields: dict[str, object]
    ) -> BillingPaymentMethodRecord: ...
    def update(
        self, *, method_id: UUID, fields: dict[str, object]
    ) -> BillingPaymentMethodRecord: ...
    def soft_delete(self, *, method_id: UUID) -> None: ...
