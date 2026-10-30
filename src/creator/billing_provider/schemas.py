"""Request payloads for the billing_provider capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProviderCustomerCreateRequest(BaseModel):
    billing_account_id: UUID
    provider: str
    provider_customer_id: str
    provider_code: str | None = None
    metadata: dict[str, object] = {}


class ProviderDisputeCreateRequest(BaseModel):
    billing_account_id: UUID
    charge_id: UUID | None = None
    code: str | None = None
    reason: str | None = None
    opened_at: datetime | None = None
    deadline_at: datetime | None = None


class ProviderDisputeUpdateRequest(BaseModel):
    reason: str | None = None
    status: str | None = None


class ProviderSubscriptionCreateRequest(BaseModel):
    subscription_id: UUID
    provider: str
    provider_subscription_id: str
    provider_status: str | None = None
    payload: dict[str, object] = {}
