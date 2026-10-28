from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response

from creator.api.dependencies import get_rate_limiter
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.infrastructure.runtime.metrics import MetricsRegistry
from creator.infrastructure.runtime.rate_limit import InMemoryRateLimitBackend, RateLimiter
from creator.workers import image_generation as image_generation_worker
from tests.e2e.conftest import FakeGenerationQueue, signup_payload

pytestmark = pytest.mark.e2e


def _assert_envelope(response: Response, *, success: bool) -> dict[str, Any]:
    body = response.json()
    assert body["success"] is success
    assert body["meta"]["request_id"] == response.headers["X-Request-ID"]
    if success:
        assert "data" in body
    else:
        assert set(body["error"]) == {"code", "message"}
    return body


async def _signup(client: AsyncClient, email: str) -> tuple[str, str]:
    response = await client.post(
        "/api/v1/auth/signup", json=signup_payload(email, f"Workspace {email}")
    )
    assert response.status_code == 201, response.text
    data = _assert_envelope(response, success=True)["data"]
    return data["session"]["access_token"], data["workspace"]["id"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _generate_content(
    client: AsyncClient, token: str, workspace_id: str, *, topic: str = "Launch campaign"
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/content/generate",
        headers=_auth(token),
        json={
            "workspace_id": workspace_id,
            "topic": topic,
            "audience": "marketing managers",
            "tone": "professional",
            "content_type": "email",
            "brand_voice": "Clear and useful",
        },
    )
    assert response.status_code == 200, response.text
    return _assert_envelope(response, success=True)["data"]


def _patch_worker_to_test_database(monkeypatch: pytest.MonkeyPatch, application: object) -> None:
    state = application.state
    monkeypatch.setattr(image_generation_worker, "get_settings", lambda: state.e2e_settings)
    monkeypatch.setattr(
        image_generation_worker,
        "SqlAlchemyUnitOfWork",
        lambda: SqlAlchemyUnitOfWork(state.e2e_factory),
    )
    monkeypatch.setattr(
        image_generation_worker,
        "create_image_generator",
        lambda _settings: state.e2e_image_generator,
    )
    monkeypatch.setattr(
        image_generation_worker,
        "create_storage_provider",
        lambda _settings: state.e2e_storage,
    )


@pytest.mark.anyio
async def test_health_auth_and_error_envelopes(e2e: tuple[object, object]) -> None:
    application, _ = e2e
    request_id = str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        health = await client.get("/health", headers={"X-Request-ID": request_id})
        live = await client.get("/health/live")
        unauthorized = await client.get("/api/v1/settings")
        invalid_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )

    assert health.status_code == 200
    assert _assert_envelope(health, success=True)["data"] == {"status": "ok"}
    assert health.headers["X-Request-ID"] == request_id
    assert live.status_code == 200
    assert _assert_envelope(live, success=True)["data"] == {"status": "ok"}
    assert unauthorized.status_code == 401
    assert _assert_envelope(unauthorized, success=False)["error"]["code"] == (
        "AUTHENTICATION_INVALID"
    )
    assert invalid_login.status_code == 401
    assert _assert_envelope(invalid_login, success=False)["error"]["code"] == "LOGIN_REJECTED"


@pytest.mark.anyio
async def test_settings_improvement_history_isolation_and_soft_delete(
    e2e: tuple[object, object],
) -> None:
    application, llm = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "settings-owner@example.com")
        other_token, _ = await _signup(client, "settings-other@example.com")

        initial_settings = await client.get("/api/v1/settings", headers=_auth(token))
        updated_settings = await client.patch(
            "/api/v1/settings",
            headers=_auth(token),
            json={
                "brand_name": "Creator Brand",
                "tone": "friendly",
                "visual_style": "illustration",
                "default_preferences": {"language": "pt-BR"},
            },
        )
        content = await _generate_content(client, token, workspace_id)
        improvement = await client.post(
            "/api/v1/content/improve",
            headers=_auth(token),
            json={
                "workspace_id": workspace_id,
                "content_id": content["id"],
                "objective": "persuasive",
                "context": {"campaign": "launch"},
            },
        )
        invalid_improvement = await client.post(
            "/api/v1/content/improve",
            headers=_auth(token),
            json={"workspace_id": workspace_id, "objective": "persuasive"},
        )
        history = await client.get("/api/v1/content?type=TEXT", headers=_auth(token))
        detail = await client.get(f"/api/v1/contents/{content['id']}", headers=_auth(token))
        hidden_detail = await client.get(
            f"/api/v1/contents/{content['id']}", headers=_auth(other_token)
        )
        deleted = await client.delete(f"/api/v1/contents/{content['id']}", headers=_auth(token))
        repeated_delete = await client.delete(
            f"/api/v1/contents/{content['id']}", headers=_auth(token)
        )
        after_delete = await client.get(f"/api/v1/contents/{content['id']}", headers=_auth(token))
        history_after_delete = await client.get("/api/v1/content?type=TEXT", headers=_auth(token))

    assert initial_settings.status_code == 200
    assert _assert_envelope(initial_settings, success=True)["data"]["tone"] == "professional"
    assert updated_settings.status_code == 200
    updated_data = _assert_envelope(updated_settings, success=True)["data"]
    assert updated_data["brand_name"] == "Creator Brand"
    assert updated_data["tone"] == "friendly"
    assert updated_data["visual_style"] == "illustration"
    assert updated_data["default_preferences"] == {"language": "pt-BR"}

    assert content["type"] == "TEXT"
    assert content["payload"]["text"] == "Generated launch copy"
    assert llm.prompts
    assert improvement.status_code == 200
    improvement_data = _assert_envelope(improvement, success=True)["data"]
    assert improvement_data["text"] == "Improved launch copy"
    assert improvement_data["persistence"] == "preview_only"
    assert invalid_improvement.status_code == 422
    assert _assert_envelope(invalid_improvement, success=False)["error"]["code"] == (
        "VALIDATION_FAILED"
    )

    assert history.status_code == 200
    history_data = _assert_envelope(history, success=True)["data"]
    assert history_data["pagination"]["total"] == 1
    assert history_data["items"][0]["id"] == content["id"]
    assert detail.status_code == 200
    assert _assert_envelope(detail, success=True)["data"]["images"] == []
    assert hidden_detail.status_code == 404
    assert _assert_envelope(hidden_detail, success=False)["error"]["code"] == ("CONTENT_NOT_FOUND")

    assert deleted.status_code == 200
    assert _assert_envelope(deleted, success=True)["data"] == {"deleted": True}
    assert repeated_delete.status_code == 200
    assert after_delete.status_code == 404
    assert history_after_delete.status_code == 200
    assert _assert_envelope(history_after_delete, success=True)["data"]["items"] == []


@pytest.mark.anyio
async def test_content_image_worker_polling_generation_history_regeneration_and_delete(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    _patch_worker_to_test_database(monkeypatch, application)
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "image-owner@example.com")
        other_token, _ = await _signup(client, "image-other@example.com")
        content = await _generate_content(client, token, workspace_id)
        accepted = await client.post(
            "/api/v1/images/generate",
            headers={**_auth(token), "Idempotency-Key": "image-create-1"},
            json={"content_id": content["id"], "style": "photographic"},
        )
        accepted_data = _assert_envelope(accepted, success=True)["data"]
        job_id = accepted_data["id"]
        queue: FakeGenerationQueue = application.state.e2e_queue
        assert accepted.status_code == 202
        assert accepted_data["status"] == "PENDING"
        assert queue.calls[-1]["job_id"] == UUID(job_id)

        image_generation_worker.run_image_generation(
            job_id, _assert_envelope(accepted, success=True)["meta"]["request_id"]
        )
        completed = await client.get(f"/api/v1/images/{job_id}", headers=_auth(token))
        completed_data = _assert_envelope(completed, success=True)["data"]
        content_detail = await client.get(f"/api/v1/contents/{content['id']}", headers=_auth(token))
        generation_history = await client.get(
            f"/api/v1/generations?content_id={content['id']}", headers=_auth(token)
        )

        image_id = completed_data["image"]["id"]
        regenerated = await client.post(
            f"/api/v1/images/{image_id}/regenerate",
            headers={**_auth(token), "Idempotency-Key": "image-regenerate-1"},
            json={"style": "illustration"},
        )
        regenerated_data = _assert_envelope(regenerated, success=True)["data"]
        regenerated_request_id = _assert_envelope(regenerated, success=True)["meta"]["request_id"]
        image_generation_worker.run_image_generation(regenerated_data["id"], regenerated_request_id)
        regenerated_completed = await client.get(
            f"/api/v1/images/{regenerated_data['id']}", headers=_auth(token)
        )
        regenerated_detail = await client.get(
            f"/api/v1/contents/{content['id']}", headers=_auth(token)
        )

        other_image = await client.get(f"/api/v1/images/{job_id}", headers=_auth(other_token))
        other_content = await client.get(
            f"/api/v1/contents/{content['id']}", headers=_auth(other_token)
        )
        deleted = await client.delete(f"/api/v1/content/{content['id']}", headers=_auth(token))
        hidden_after_delete = await client.get(f"/api/v1/images/{job_id}", headers=_auth(token))
        generation_history_after_delete = await client.get(
            f"/api/v1/generations?content_id={content['id']}", headers=_auth(token)
        )
        history_after_delete = await client.get("/api/v1/content?type=TEXT", headers=_auth(token))

    assert completed.status_code == 200
    assert completed_data["status"] == "COMPLETED"
    assert completed_data["image"]["public_url"].startswith("https://storage.test/")
    assert content_detail.status_code == 200
    assert len(_assert_envelope(content_detail, success=True)["data"]["images"]) == 1
    assert generation_history.status_code == 200
    history_items = _assert_envelope(generation_history, success=True)["data"]["items"]
    assert any(item["type"] == "IMAGE" for item in history_items)

    assert regenerated.status_code == 202
    assert regenerated_data["status"] == "PENDING"
    assert regenerated_completed.status_code == 200
    assert _assert_envelope(regenerated_completed, success=True)["data"]["status"] == ("COMPLETED")
    assert regenerated_detail.status_code == 200
    assert len(_assert_envelope(regenerated_detail, success=True)["data"]["images"]) == 2

    assert other_image.status_code == 404
    assert _assert_envelope(other_image, success=False)["error"]["code"] == (
        "IMAGE_GENERATION_NOT_FOUND"
    )
    assert other_content.status_code == 404
    assert deleted.status_code == 200
    assert _assert_envelope(deleted, success=True)["data"] == {"deleted": True}
    assert hidden_after_delete.status_code == 404
    assert generation_history_after_delete.status_code == 200
    assert _assert_envelope(generation_history_after_delete, success=True)["data"]["items"] == []
    assert history_after_delete.status_code == 200
    assert _assert_envelope(history_after_delete, success=True)["data"]["items"] == []


@pytest.mark.anyio
async def test_image_generation_queue_failure_is_a_partial_failure_without_orphan_job(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "queue-failure@example.com")
        content = await _generate_content(client, token, workspace_id)
        queue: FakeGenerationQueue = application.state.e2e_queue
        queue.error = RuntimeError("redis unavailable")
        response = await client.post(
            "/api/v1/images/generate",
            headers={**_auth(token), "Idempotency-Key": "queue-failure-1"},
            json={"content_id": content["id"]},
        )
        detail = await client.get(f"/api/v1/contents/{content['id']}", headers=_auth(token))
        history = await client.get(
            f"/api/v1/generations?content_id={content['id']}", headers=_auth(token)
        )

    assert response.status_code == 503
    assert _assert_envelope(response, success=False)["error"]["code"] == "QUEUE_ENQUEUE_FAILED"
    assert detail.status_code == 200
    assert _assert_envelope(detail, success=True)["data"]["images"] == []
    assert history.status_code == 200
    assert all(
        item["type"] != "IMAGE" for item in _assert_envelope(history, success=True)["data"]["items"]
    )


@pytest.mark.anyio
async def test_rate_limit_contract_is_scoped_to_authenticated_principal(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, _ = await _signup(client, "rate-limit@example.com")
        limiter = RateLimiter(
            InMemoryRateLimitBackend(),
            limit=1,
            window_seconds=60.0,
            key_prefix="creator:e2e-rate-limit",
            metrics=MetricsRegistry(),
        )
        application.dependency_overrides[get_rate_limiter] = lambda: limiter
        first = await client.get("/api/v1/settings", headers=_auth(token))
        second = await client.get("/api/v1/settings", headers=_auth(token))

    assert first.status_code == 200
    assert second.status_code == 429
    body = _assert_envelope(second, success=False)
    assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert second.headers["Retry-After"] == "60"
    assert second.headers["RateLimit-Limit"] == "1"
