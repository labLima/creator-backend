from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.e2e.conftest import signup_payload

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
