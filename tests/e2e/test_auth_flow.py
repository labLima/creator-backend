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
        assert "creator_access" in signup.headers.get("set-cookie", "")
        assert "creator_refresh" in signup.headers.get("set-cookie", "")
        assert "creator_csrf" in signup.headers.get("set-cookie", "")

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "correct-password"},
        )
        assert login.status_code == 200, login.text
        session = login.json()["data"]
        assert session["csrf_token"]

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
