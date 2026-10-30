"""Persistence ports owned by the user capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: UUID
    external_id: str
    email: str | None
    display_name: str | None
    global_role: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    password_hash: str | None = None


class UserRepository(Protocol):
    def add(
        self,
        *,
        external_id: str,
        email: str | None = None,
        display_name: str | None = None,
        global_role: str = "membro",
        password_hash: str | None = None,
    ) -> UserRecord: ...

    def get_by_id(self, user_id: UUID, *, include_deleted: bool = False) -> UserRecord | None: ...

    def get_by_external_id(
        self, external_id: str, *, include_deleted: bool = False
    ) -> UserRecord | None: ...

    def get_by_email(self, email: str, *, include_deleted: bool = False) -> UserRecord | None: ...

    def list(
        self, *, include_deleted: bool = False, page: PageRequest | None = None
    ) -> Page[UserRecord]: ...

    def update_profile(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> UserRecord: ...

    def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        display_name: str | None = None,
        global_role: str | None = None,
    ) -> UserRecord: ...

    def soft_delete(self, user_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class SettingsRecord:
    id: UUID
    user_id: UUID
    brand_name: str | None
    segment: str | None
    tone: str
    voice: str
    visual_style: str
    default_preferences: JsonObject
    created_at: datetime
    updated_at: datetime


class SettingsRepository(Protocol):
    def get_by_user_id(self, user_id: UUID) -> SettingsRecord | None: ...

    def get_or_create_for_user(self, user_id: UUID) -> SettingsRecord: ...

    def create_for_user(
        self,
        user_id: UUID,
        *,
        brand_name: str | None = None,
        segment: str | None = None,
        tone: str = "professional",
        voice: str = "Clear and useful",
        visual_style: str = "photographic",
        default_preferences: JsonObject | None = None,
    ) -> SettingsRecord: ...

    def update_partial(self, user_id: UUID, changes: JsonObject) -> SettingsRecord: ...
