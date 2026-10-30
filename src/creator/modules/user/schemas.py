"""Request payloads for the user capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from creator.core.schemas import CreatorDTO


class SettingsUpdateRequest(CreatorDTO):
    brand_name: str | None = Field(default=None, max_length=255)
    segment: str | None = Field(default=None, max_length=255)
    tone: (
        Literal["professional", "friendly", "persuasive", "educational", "formal", "casual"] | None
    ) = None
    voice: str | None = Field(default=None, min_length=1, max_length=1_000)
    visual_style: Literal["photographic", "illustration", "product_render"] | None = None
    default_preferences: dict[str, object] | None = None


class UserCreateRequest(CreatorDTO):
    external_id: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=50)
    display_name: str | None = Field(default=None, max_length=50)
    global_role: Literal["admin", "gestor", "membro"] = "membro"


class UserUpdateRequest(CreatorDTO):
    email: str | None = Field(default=None, max_length=50)
    display_name: str | None = Field(default=None, max_length=50)
    global_role: Literal["admin", "gestor", "membro"] | None = None
