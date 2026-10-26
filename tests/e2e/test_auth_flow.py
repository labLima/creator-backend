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

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "correct-password"},
        )
        assert login.status_code == 200, login.text
        session = login.json()["data"]
        access = session["access_token"]
        refresh = session["refresh_token"]

        me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200, me.text
        assert me.json()["data"]["email"] == "owner@example.com"

        rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert rotated.status_code == 200, rotated.text
        assert rotated.json()["data"]["refresh_token"] != refresh

        rotated_access = rotated.json()["data"]["access_token"]
        logout = await client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {rotated_access}"}
        )
        assert logout.status_code == 200, logout.text

        after_logout = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": rotated.json()["data"]["refresh_token"]},
        )
        assert after_logout.status_code == 401
