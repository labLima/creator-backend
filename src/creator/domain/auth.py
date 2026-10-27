from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    email: str | None = None
    role: str | None = None
    session_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class AuthSession:
    id: UUID
    family_id: UUID
    principal: Principal
    expires_at: datetime
    absolute_expires_at: datetime
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_expires_in: int
    principal: Principal
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class AuthSignupResult:
    principal: Principal
    session: IssuedSession | None
    confirmation_required: bool
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
