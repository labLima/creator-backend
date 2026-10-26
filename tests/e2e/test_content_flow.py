from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.e2e.conftest import signup_payload

pytestmark = pytest.mark.e2e


async def _signup(client: AsyncClient, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/signup", json=signup_payload(email, f"Workspace {email}")
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    return data["session"]["access_token"], data["workspace"]["id"]


@pytest.mark.anyio
async def test_content_generation_is_workspace_scoped(e2e: tuple[object, object]) -> None:
    application, llm = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        owner_token, owner_workspace = await _signup(client, "owner@example.com")
        other_token, other_workspace = await _signup(client, "other@example.com")

        generated = await client.post(
            "/api/v1/content/generate",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "workspace_id": owner_workspace,
                "topic": "Launch campaign",
                "audience": "marketing managers",
                "tone": "professional",
                "content_type": "email",
                "brand_voice": "Clear and useful",
            },
        )
        assert generated.status_code == 200, generated.text
        assert generated.json()["data"]["payload"]["text"] == "Generated launch copy"
        assert llm.prompts

        denied = await client.post(
            "/api/v1/content/generate",
            headers={"Authorization": f"Bearer {other_token}"},
            json={
                "workspace_id": owner_workspace,
                "topic": "Launch campaign",
                "audience": "marketing managers",
                "tone": "professional",
                "content_type": "email",
                "brand_voice": "Clear and useful",
            },
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "WORKSPACE_ACCESS_DENIED"

        own = await client.post(
            "/api/v1/content/generate",
            headers={"Authorization": f"Bearer {other_token}"},
            json={
                "workspace_id": other_workspace,
                "topic": "Own campaign",
                "audience": "marketing managers",
                "tone": "professional",
                "content_type": "email",
                "brand_voice": "Clear and useful",
            },
        )
        assert own.status_code == 200, own.text
