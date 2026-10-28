from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from creator.domain.auth import Principal


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """Application result containing credentials ready for an API adapter."""

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
