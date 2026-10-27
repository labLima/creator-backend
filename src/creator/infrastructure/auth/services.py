from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from creator.application.auth import ExpiredTokenError, InvalidTokenError
from creator.application.auth_ports import (
    AccessTokenCodec,
    AuthTokenServices,
    Clock,
    CsrfTokenService,
    RefreshTokenGenerator,
)
from creator.config import Settings
from creator.domain.auth import Principal
from creator.infrastructure.auth.vendor.fastapi_jwt_auth import (
    ExpiredSignatureError,
)
from creator.infrastructure.auth.vendor.fastapi_jwt_auth import (
    InvalidTokenError as ProviderInvalidTokenError,
)
from creator.infrastructure.auth.vendor.fastapi_jwt_auth import (
    decode as provider_decode,
)
from creator.infrastructure.auth.vendor.fastapi_jwt_auth import (
    encode as provider_encode,
)


class PyJwtAccessTokenCodec:
    def issue(self, *, user_id: UUID, session_id: UUID, role: str, settings: Settings) -> str:
        now = datetime.now(UTC)
        payload = {
            "iss": settings.auth_jwt_issuer,
            "aud": settings.auth_jwt_audience,
            "sub": str(user_id),
            "session_id": str(session_id),
            "role": role,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + settings.auth_access_token_ttl_seconds,
            "jti": secrets.token_hex(16),
        }
        return provider_encode(payload, _secret(settings), algorithm="HS256")

    def principal(self, token: str, settings: Settings) -> Principal:
        try:
            claims = provider_decode(
                token,
                _secret(settings),
                algorithms=["HS256"],
                audience=settings.auth_jwt_audience,
                issuer=settings.auth_jwt_issuer,
                options={"require": ["iss", "aud", "exp", "iat", "sub", "session_id", "type"]},
            )
        except ExpiredSignatureError as error:
            raise ExpiredTokenError("access token is expired") from error
        except ProviderInvalidTokenError as error:
            raise InvalidTokenError("access token is invalid") from error
        if claims.get("type") != "access":
            raise InvalidTokenError("access token type is invalid")
        return Principal(
            subject=str(claims["sub"]),
            email=cast(str | None, claims.get("email")),
            role=cast(str | None, claims.get("role")),
            session_id=str(claims["session_id"]),
            claims=dict(claims),
        )


class SecureRefreshTokenGenerator:
    def generate(self) -> str:
        return secrets.token_urlsafe(48)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class SignedCsrfTokenService:
    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()

    def issue(self, *, session_id: UUID, settings: Settings) -> str:
        nonce = secrets.token_urlsafe(24)
        issued_at = int(self._clock.now().timestamp())
        value = f"{session_id}:{issued_at}:{nonce}"
        signature = _sign(value, _secret(settings))
        return f"{_b64(value.encode())}.{signature}"

    def verify(self, *, token: str, session_id: UUID, settings: Settings) -> bool:
        try:
            encoded, signature = token.split(".", 1)
            padded = encoded + "=" * (-len(encoded) % 4)
            value = base64.urlsafe_b64decode(padded.encode()).decode()
            token_session_id, issued_at_raw, _ = value.split(":", 2)
            issued_at = int(issued_at_raw)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            return False
        expected = _sign(value, _secret(settings))
        age_seconds = self._clock.now().timestamp() - issued_at
        return (
            token_session_id == str(session_id)
            and 0 <= age_seconds <= settings.auth_csrf_ttl_seconds
            and hmac.compare_digest(signature, expected)
        )


class DefaultAuthTokenServices:
    access: AccessTokenCodec = PyJwtAccessTokenCodec()
    refresh: RefreshTokenGenerator = SecureRefreshTokenGenerator()
    csrf: CsrfTokenService = SignedCsrfTokenService()
    clock: Clock = SystemClock()


def _secret(settings: Settings) -> str:
    if not settings.auth_jwt_secret:
        raise ValueError("AUTH_JWT_SECRET is required")
    return settings.auth_jwt_secret


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _sign(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def auth_token_services() -> AuthTokenServices:
    return DefaultAuthTokenServices()
