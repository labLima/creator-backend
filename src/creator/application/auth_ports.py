from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

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


class AuthTokenServices(Protocol):
    access: AccessTokenCodec
    refresh: RefreshTokenGenerator
    csrf: CsrfTokenService
    clock: Clock
