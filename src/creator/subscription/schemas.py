"""Request payloads for the subscription capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class SubscriptionCreateRequest(CreatorDTO):
    billing_account_id: UUID
    workspace_id: UUID
    plan_id: UUID
    payment_method: str | None = None
    billing_day: int | None = Field(default=None, ge=1, le=31)
    start_at: datetime | None = None


class SubscriptionUpdateRequest(CreatorDTO):
    payment_method: str | None = None
    billing_day: int | None = Field(default=None, ge=1, le=31)
    start_at: datetime | None = None
