from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.repositories.auth import AuthSessionRecord
from tests.e2e.conftest import SECRET, signup_payload

pytestmark = pytest.mark.e2e


def _assert_session_cookies(response: object) -> None:
    headers = response.headers.get_list("set-cookie")
    assert len(headers) == 3
    cookies = {header.split("=", 1)[0]: header for header in headers}
    access = cookies["creator_access"]
    assert "HttpOnly" in access
    assert "Path=/api/v1" in access
    assert "SameSite=lax" in access
    refresh = cookies["creator_refresh"]
    assert "HttpOnly" in refresh
    assert "Path=/api/v1/auth" in refresh
    assert "SameSite=strict" in refresh
    csrf = cookies["creator_csrf"]
    assert "Path=/" in csrf
    assert "SameSite=lax" in csrf
    assert "HttpOnly" not in csrf
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_signup_login_refresh_logout_flow(e2e: tuple[object, object]) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        signup = await client.post("/api/v1/auth/signup", json=signup_payload("owner@example.com"))
        assert signup.status_code == 201, signup.text
        signup_data = signup.json()["data"]
        assert signup_data["provider"] == "local"
        assert signup_data["session"]["provider"] == "local"
        assert signup_data["workspace"]["name"] == "Creator Workspace"
        assert signup_data["session"]["csrf_token"]
        assert signup_data["session"]["access_token"]
        assert signup_data["session"]["refresh_token"]
        _assert_session_cookies(signup)

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "correct-password"},
        )
        assert login.status_code == 200, login.text
        session = login.json()["data"]
        assert session["csrf_token"]
        assert session["access_token"]
        assert session["refresh_token"]
        _assert_session_cookies(login)

        me = await client.get("/api/v1/users/me")
        assert me.status_code == 200, me.text
        assert me.json()["data"]["email"] == "owner@example.com"

        csrf = client.cookies.get("creator_csrf")
        rotated = await client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": "http://test", "X-CSRF-Token": csrf or ""},
        )
        assert rotated.status_code == 200, rotated.text
        assert rotated.json()["data"]["refresh_token"]

        csrf = client.cookies.get("creator_csrf")
        logout = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://test", "X-CSRF-Token": csrf or ""},
        )
        assert logout.status_code == 200, logout.text

        after_logout = await client.post(
            "/api/v1/auth/refresh",
        )
        assert after_logout.status_code == 401


@pytest.mark.anyio
async def test_signup_login_cookie_only_mode_and_auth_errors_are_not_cached(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    settings = application.state.e2e_settings
    settings.auth_token_body_enabled = False
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        signup = await client.post(
            "/api/v1/auth/signup", json=signup_payload("cookie-only@example.com")
        )
        assert signup.status_code == 201, signup.text
        signup_data = signup.json()["data"]["session"]
        assert signup_data["csrf_token"]
        assert "access_token" not in signup_data
        assert "refresh_token" not in signup_data
        _assert_session_cookies(signup)

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "cookie-only@example.com", "password": "correct-password"},
        )
        assert login.status_code == 200, login.text
        login_data = login.json()["data"]
        assert login_data["csrf_token"]
        assert "access_token" not in login_data
        assert "refresh_token" not in login_data
        _assert_session_cookies(login)

        duplicate_signup = await client.post(
            "/api/v1/auth/signup", json=signup_payload("cookie-only@example.com")
        )
        invalid_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "cookie-only@example.com", "password": "wrong-password"},
        )
        invalid_signup = await client.post("/api/v1/auth/signup", json={})

    assert duplicate_signup.status_code == 409
    assert invalid_login.status_code == 401
    assert invalid_signup.status_code == 422
    for response in (duplicate_signup, invalid_login, invalid_signup):
        assert response.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_logout_uses_valid_refresh_when_access_token_is_expired(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        signup = await client.post(
            "/api/v1/auth/signup", json=signup_payload("expired-access@example.com")
        )
        assert signup.status_code == 201, signup.text
        csrf = client.cookies.get("creator_csrf")
        refresh_token = client.cookies.get("creator_refresh")
        access_token = client.cookies.get("creator_access")
        assert access_token is not None
        claims = jwt.decode(
            access_token,
            SECRET,
            algorithms=["HS256"],
            audience="creator-api",
            issuer="creator",
        )
        claims["exp"] = int(datetime.now(UTC).timestamp()) - 1
        client.cookies.set(
            "creator_access",
            jwt.encode(claims, SECRET, algorithm="HS256"),
            path="/api/v1",
        )

        logout = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://test", "X-CSRF-Token": csrf or ""},
        )
        assert logout.status_code == 200, logout.text
        assert logout.json()["data"] == {"logged_out": True}

        assert refresh_token is not None
        with SqlAlchemyUnitOfWork(application.state.e2e_factory) as unit_of_work:
            record: AuthSessionRecord | None = unit_of_work.auth_sessions.get_by_refresh_hash(
                hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
            )
            assert record is not None
            assert record.revoked_at is not None
