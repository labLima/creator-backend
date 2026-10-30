from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from creator.auth import router as auth_routes
from creator.auth.service import RefreshInProgressError
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
        repeated_logout = await client.post("/api/v1/auth/logout")
        assert repeated_logout.status_code == 200, repeated_logout.text

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


@pytest.mark.anyio
async def test_login_succeeds_with_expired_access_cookie(e2e: tuple[object, object]) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        signup = await client.post(
            "/api/v1/auth/signup", json=signup_payload("expired-cookie-login@example.com")
        )
        assert signup.status_code == 201, signup.text
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

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "expired-cookie-login@example.com", "password": "correct-password"},
        )

    assert login.status_code == 200, login.text


@pytest.mark.anyio
async def test_refresh_body_is_rejected_and_csrf_can_be_rehydrated_from_refresh(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        signup = await client.post(
            "/api/v1/auth/signup", json=signup_payload("csrf-refresh@example.com")
        )
        refresh_token = client.cookies.get("creator_refresh")
        assert signup.status_code == 201
        assert refresh_token is not None

        access_csrf = await client.get("/api/v1/auth/csrf")
        assert access_csrf.status_code == 200, access_csrf.text
        assert access_csrf.headers["cache-control"] == "no-store"
        assert access_csrf.json()["data"]["csrf_token"]

        body_only = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"Cookie": ""},
        )
        assert body_only.status_code == 401
        assert body_only.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"

        rehydrated = await client.get(
            "/api/v1/auth/csrf", headers={"Cookie": f"creator_refresh={refresh_token}"}
        )
        assert rehydrated.status_code == 200, rehydrated.text
        assert rehydrated.headers["cache-control"] == "no-store"
        assert rehydrated.json()["data"]["csrf_token"]


@pytest.mark.anyio
async def test_cookie_mutations_enforce_csrf_origin_and_bearer_exemption(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        signup = await client.post(
            "/api/v1/auth/signup", json=signup_payload("csrf-origin@example.com")
        )
        assert signup.status_code == 201, signup.text
        session = signup.json()["data"]["session"]
        csrf = client.cookies.get("creator_csrf")
        assert csrf is not None

        missing = await client.post("/api/v1/auth/logout", headers={"Origin": "http://test"})
        assert missing.status_code == 403
        assert missing.json()["error"]["code"] == "CSRF_TOKEN_MISSING"

        wrong = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://test", "X-CSRF-Token": "wrong-token"},
        )
        assert wrong.status_code == 403
        assert wrong.json()["error"]["code"] == "CSRF_TOKEN_INVALID"

        for origin in ("null", "https://unknown.example"):
            rejected = await client.post(
                "/api/v1/auth/logout",
                headers={"Origin": origin, "X-CSRF-Token": csrf},
            )
            assert rejected.status_code == 403
            assert rejected.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"

        bearer_logout = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {session['access_token']}"},
        )
        assert bearer_logout.status_code == 200, bearer_logout.text


@pytest.mark.anyio
async def test_csrf_token_from_another_auth_session_is_rejected(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with (
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as first,
        AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as second,
    ):
        first_signup = await first.post(
            "/api/v1/auth/signup", json=signup_payload("csrf-first@example.com")
        )
        second_signup = await second.post(
            "/api/v1/auth/signup", json=signup_payload("csrf-second@example.com")
        )
        assert first_signup.status_code == second_signup.status_code == 201
        other_csrf = second.cookies.get("creator_csrf")
        assert other_csrf is not None
        first.cookies.set("creator_csrf", other_csrf, domain="test.local", path="/")

        rejected = await first.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://test", "X-CSRF-Token": other_csrf},
        )

    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "CSRF_TOKEN_INVALID"


@pytest.mark.anyio
async def test_refresh_rotation_in_progress_maps_to_409(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        signup = await client.post(
            "/api/v1/auth/signup", json=signup_payload("refresh-conflict@example.com")
        )
        assert signup.status_code == 201, signup.text
        csrf = client.cookies.get("creator_csrf")
        assert csrf is not None

        def raise_refresh_in_progress(**_: object) -> None:
            raise RefreshInProgressError("refresh rotation is already in progress")

        monkeypatch.setattr(auth_routes, "refresh_local", raise_refresh_in_progress)
        response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": "http://test", "X-CSRF-Token": csrf},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REFRESH_IN_PROGRESS"
