from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from creator.auth_cookie_policy import CookieSameSite
from creator.config import Settings
from creator.domain.auth import Principal


class Clock(Protocol):
    def now(self) -> datetime: ...


class AccessTokenCodec(Protocol):
    def issue(self, *, user_id: UUID, session_id: UUID, role: str, settings: Settings) -> str: ...

    def principal(self, token: str, settings: Settings) -> Principal: ...


class RefreshTokenGenerator(Protocol):
    def generate(self) -> str: ...


class CsrfTokenService(Protocol):
    def issue(self, *, session_id: UUID, settings: Settings) -> str: ...

    def verify(self, *, token: str, session_id: UUID, settings: Settings) -> bool: ...


@dataclass(frozen=True, slots=True)
class CookieSpec:
    name: str
    value: str
    max_age: int
    http_only: bool
    secure: bool
    same_site: CookieSameSite
    path: str
    domain: str | None = None


class CookieTransport(Protocol):
    def set(self, cookie: CookieSpec) -> None: ...

    def delete(self, *, name: str, path: str) -> None: ...


class AuthTokenServices(Protocol):
    access: AccessTokenCodec
    refresh: RefreshTokenGenerator
    csrf: CsrfTokenService
    clock: Clock
