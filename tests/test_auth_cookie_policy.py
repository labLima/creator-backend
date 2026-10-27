from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from starlette.responses import Response

from creator.api.auth_cookies import set_auth_cookies
from creator.config import Settings
from creator.domain.auth import IssuedSession, Principal
from creator.infrastructure.auth import auth_token_services
from creator.infrastructure.auth.services import SignedCsrfTokenService

SECRET = "test-cookie-policy-secret-with-at-least-32-bytes"


def test_production_rejects_insecure_cookie_and_weak_secret() -> None:
    with pytest.raises(ValueError, match="AUTH_COOKIE_SECURE"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_jwt_secret=SECRET,
            auth_cookie_secure=False,
        )
    with pytest.raises(ValueError, match="AUTH_JWT_SECRET"):
        Settings(_env_file=None, app_env="production", auth_jwt_secret="short")


def test_credentialed_cors_rejects_wildcard_and_insecure_none() -> None:
    with pytest.raises(ValueError, match="AUTH_CORS_ORIGINS"):
        Settings(_env_file=None, auth_cors_origins=["*"])
    with pytest.raises(ValueError, match="AUTH_COOKIE_SAME_SITE"):
        Settings(_env_file=None, auth_cookie_same_site="none", auth_cookie_secure=False)


def test_csrf_token_is_signed_and_bound_to_session() -> None:
    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)
    services = auth_token_services()
    session_id = uuid4()
    other_session_id = uuid4()
    token = services.csrf.issue(session_id=session_id, settings=settings)

    assert services.csrf.verify(token=token, session_id=session_id, settings=settings)
    assert not services.csrf.verify(token=token, session_id=other_session_id, settings=settings)
    assert not services.csrf.verify(token=f"{token}x", session_id=session_id, settings=settings)


def test_csrf_token_expires_using_the_clock_port() -> None:
    class FakeClock:
        current = datetime(2026, 1, 1, tzinfo=UTC)

        def now(self) -> datetime:
            return self.current

    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)
    clock = FakeClock()
    service = SignedCsrfTokenService(clock)
    session_id = uuid4()
    token = service.issue(session_id=session_id, settings=settings)

    clock.current += timedelta(seconds=settings.auth_csrf_ttl_seconds + 1)

    assert not service.verify(token=token, session_id=session_id, settings=settings)


def test_session_cookies_are_http_only_and_scoped() -> None:
    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)
    services = auth_token_services()
    session = IssuedSession(
        access_token="access",
        refresh_token="refresh",
        token_type="Bearer",
        expires_in=900,
        refresh_expires_in=3600,
        principal=Principal(subject=str(uuid4()), session_id=str(uuid4())),
        provider="local",
    )
    response = Response()
    csrf = services.csrf.issue(
        session_id=uuid4(),
        settings=settings,
    )
    set_auth_cookies(response, session, csrf_token=csrf, settings=settings)
    cookies = response.headers.getlist("set-cookie")
    assert any("creator_access=access" in cookie and "HttpOnly" in cookie for cookie in cookies)
    assert any(
        "creator_refresh=refresh" in cookie and "Path=/api/v1/auth" in cookie for cookie in cookies
    )
    assert any("creator_csrf=" in cookie and "HttpOnly" not in cookie for cookie in cookies)
