from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from starlette.responses import Response

from creator.api.auth import FastApiCookieTransport, clear_auth_cookies, set_auth_cookies
from creator.auth_cookie_policy import AuthCookiePolicy
from creator.config import Settings
from creator.domain.auth import Principal
from creator.infrastructure.auth import auth_token_services
from creator.infrastructure.auth.services import SignedCsrfTokenService
from creator.modules.auth.ports import CookieSpec
from creator.modules.auth.types import IssuedSession

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
    with pytest.raises(ValueError, match="AUTH_COOKIE_SECURE"):
        Settings(_env_file=None, app_env="prod", auth_jwt_secret=SECRET, auth_cookie_secure=False)
    with pytest.raises(ValueError, match="AUTH_JWT_SECRET"):
        Settings(_env_file=None, app_env="prod", auth_jwt_secret="a" * 32)


def test_credentialed_cors_rejects_wildcard_and_insecure_none() -> None:
    with pytest.raises(ValueError, match="AUTH_CORS_ORIGINS"):
        Settings(_env_file=None, auth_cors_origins=["*"])
    with pytest.raises(ValueError, match="AUTH_COOKIE_SAME_SITE"):
        Settings(_env_file=None, auth_cookie_same_site="none", auth_cookie_secure=False)


def test_default_cookie_policy_is_explicit_and_fastapi_free() -> None:
    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)

    policy = settings.auth_cookie_policy

    assert isinstance(policy, AuthCookiePolicy)
    assert (policy.access_name, policy.refresh_name) == ("creator_access", "creator_refresh")
    assert policy.access_same_site == "lax"
    assert policy.refresh_same_site == "strict"
    assert policy.access_http_only is True
    assert policy.refresh_http_only is True
    assert policy.csrf_http_only is False
    assert policy.domain is None
    assert policy.access_path == "/api/v1"
    assert policy.refresh_path == "/api/v1/auth"
    assert policy.csrf_path == "/"
    assert policy.access_max_age(3600) == 900
    assert policy.refresh_max_age(60 * 60 * 24 * 90) == 60 * 60 * 24 * 30


def test_cookie_policy_caps_all_max_age_values_at_absolute_session_ttl() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret=SECRET,
        auth_access_token_ttl_seconds=3600 * 24 * 2,
        auth_session_absolute_ttl_days=1,
        auth_refresh_token_ttl_days=30,
        auth_csrf_ttl_seconds=3600,
    )

    policy = settings.auth_cookie_policy

    assert policy.access_max_age(3600 * 24 * 2) == 3600 * 24
    assert policy.refresh_max_age(3600 * 24 * 2) == 3600 * 24
    assert policy.csrf_max_age() == 3600


def test_access_cookie_does_not_outlive_remaining_session_ttl() -> None:
    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)
    session = IssuedSession(
        access_token="access",
        refresh_token="refresh",
        token_type="Bearer",
        expires_in=900,
        refresh_expires_in=120,
        principal=Principal(subject=str(uuid4()), session_id=str(uuid4())),
        provider="local",
    )
    response = Response()

    set_auth_cookies(
        FastApiCookieTransport(response), session, csrf_token="csrf", settings=settings
    )

    access_cookie = next(
        cookie for cookie in response.headers.getlist("set-cookie") if "creator_access=" in cookie
    )
    assert "Max-Age=120" in access_cookie


def test_cookie_serialization_uses_transport_port() -> None:
    class FakeCookieTransport:
        def __init__(self) -> None:
            self.cookies: list[CookieSpec] = []
            self.deleted: list[tuple[str, str]] = []

        def set(self, cookie: CookieSpec) -> None:
            self.cookies.append(cookie)

        def delete(self, *, name: str, path: str) -> None:
            self.deleted.append((name, path))

    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)
    session = IssuedSession(
        access_token="access",
        refresh_token="refresh",
        token_type="Bearer",
        expires_in=900,
        refresh_expires_in=3600,
        principal=Principal(subject=str(uuid4()), session_id=str(uuid4())),
        provider="local",
    )
    transport = FakeCookieTransport()

    set_auth_cookies(transport, session, csrf_token="csrf", settings=settings)

    assert [cookie.name for cookie in transport.cookies] == [
        "creator_access",
        "creator_refresh",
        "creator_csrf",
    ]
    assert transport.cookies[0].http_only is True
    assert transport.cookies[2].http_only is False

    clear_auth_cookies(transport, settings=settings)

    assert transport.deleted == [
        ("creator_access", "/api/v1"),
        ("creator_refresh", "/api/v1/auth"),
        ("creator_csrf", "/"),
    ]


def test_cookie_names_must_not_collide() -> None:
    with pytest.raises(ValueError, match="names must be distinct"):
        Settings(
            _env_file=None,
            auth_cookie_access_name="same",
            auth_cookie_refresh_name="same",
        )


def test_csrf_token_is_signed_and_bound_to_session() -> None:
    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)
    services = auth_token_services()
    session_id = uuid4()
    other_session_id = uuid4()
    token = services.csrf.issue(session_id=session_id, settings=settings)

    assert services.csrf.verify(token=token, session_id=session_id, settings=settings)
    assert not services.csrf.verify(token=token, session_id=other_session_id, settings=settings)
    assert not services.csrf.verify(token=f"{token}x", session_id=session_id, settings=settings)


def test_jwt_adapter_round_trips_pyjwt_two_string_contract() -> None:
    settings = Settings(_env_file=None, auth_jwt_secret=SECRET)
    services = auth_token_services()
    user_id = uuid4()
    session_id = uuid4()

    token = services.access.issue(
        user_id=user_id,
        session_id=session_id,
        role="owner",
        settings=settings,
    )

    assert isinstance(token, str)
    principal = services.access.principal(token, settings)
    assert principal.subject == str(user_id)
    assert principal.session_id == str(session_id)


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
    set_auth_cookies(FastApiCookieTransport(response), session, csrf_token=csrf, settings=settings)
    cookies = response.headers.getlist("set-cookie")
    access_cookie = next(cookie for cookie in cookies if "creator_access=access" in cookie)
    refresh_cookie = next(cookie for cookie in cookies if "creator_refresh=refresh" in cookie)
    assert "HttpOnly" in access_cookie
    assert "SameSite=lax" in access_cookie
    assert "Max-Age=900" in access_cookie
    assert any(
        "creator_refresh=refresh" in cookie
        and "Path=/api/v1/auth" in cookie
        and "HttpOnly" in cookie
        and "SameSite=strict" in cookie
        and "Max-Age=3600" in cookie
        for cookie in cookies
    )
    assert "Domain=" not in access_cookie
    assert "Domain=" not in refresh_cookie
    assert any(
        "creator_csrf=" in cookie and "Path=/;" in cookie and "HttpOnly" not in cookie
        for cookie in cookies
    )
