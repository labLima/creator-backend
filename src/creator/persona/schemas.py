"""Request payloads for the persona capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from creator.core.schemas import CreatorDTO

AgeRange = Literal[
    "UP_TO_17",
    "FROM_18_TO_24",
    "FROM_25_TO_34",
    "FROM_35_TO_44",
    "FROM_45_TO_54",
    "FROM_55_TO_64",
    "FROM_65_PLUS",
]
PersonaGender = Literal["MALE", "FEMALE", "NON_BINARY", "OTHER", "PREFER_NOT_TO_SAY"]


class PersonaCreateRequest(CreatorDTO):
    brand_id: UUID
    name: str = Field(min_length=1, max_length=100)
    age_range: AgeRange | None = None
    gender: PersonaGender | None = None
    main_goal: str | None = Field(default=None, max_length=60)
    challenge: str | None = Field(default=None, max_length=50)
    routine: str | None = Field(default=None, max_length=300)
    journey: str | None = Field(default=None, max_length=250)
    trigger_event: str | None = Field(default=None, max_length=200)


class PersonaUpdateRequest(CreatorDTO):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    age_range: AgeRange | None = None
    gender: PersonaGender | None = None
    main_goal: str | None = Field(default=None, max_length=60)
    challenge: str | None = Field(default=None, max_length=50)
    routine: str | None = Field(default=None, max_length=300)
    journey: str | None = Field(default=None, max_length=250)
    trigger_event: str | None = Field(default=None, max_length=200)
