"""Request payloads for the plan capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO


class PlanCreateRequest(CreatorDTO):
    code: str = Field(min_length=1, max_length=32)
    type: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=64)
    description: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    is_active: bool = True


class PlanItemCreateRequest(CreatorDTO):
    plan_id: UUID
    name: str = Field(min_length=1, max_length=64)
    description: str | None = None
    quantity: int = Field(default=1, ge=1)
    cycles: int | None = Field(default=None, ge=1)
    pricing_scheme_type: str | None = Field(default=None, max_length=20)
    price_cents: int = Field(ge=0)
    price_brackets: dict[str, object] | None = None
    status: str | None = Field(default=None, max_length=20)


class PlanItemUpdateRequest(CreatorDTO):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    cycles: int | None = Field(default=None, ge=1)
    pricing_scheme_type: str | None = Field(default=None, max_length=20)
    price_cents: int | None = Field(default=None, ge=0)
    price_brackets: dict[str, object] | None = None
    status: str | None = Field(default=None, max_length=20)


class PlanUpdateRequest(CreatorDTO):
    type: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    metadata: dict[str, object] | None = None
    is_active: bool | None = None
