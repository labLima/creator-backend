from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


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
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    principal: Principal
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class AuthSignupResult:
    principal: Principal
    session: AuthSession | None
    confirmation_required: bool
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)
