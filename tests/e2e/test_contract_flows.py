from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response
from PIL import Image

from creator.api.dependencies import get_rate_limiter
from creator.domain.agent_workflow import AgentWorkflowStatus
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.infrastructure.runtime import image_composition
from creator.infrastructure.runtime.metrics import MetricsRegistry
from creator.infrastructure.runtime.rate_limit import InMemoryRateLimitBackend, RateLimiter
from creator.services.agents.contracts import AgentExecutionResult, ArtistOutput, WriterOutput
from creator.services.ai.image_provider import ImageGenerationResult
from creator.services.ai.reviewer import ImageReviewResult
from creator.workers import agent_workflow as workflow_worker
from creator.workers import image_generation as image_generation_worker
from tests.e2e.conftest import FakeGenerationQueue, signup_payload

pytestmark = pytest.mark.e2e


@pytest.mark.anyio
async def test_composition_resolves_real_brand_assets_and_local_storage(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    state = application.state
    font_path = next(
        (
            path
            for path in (
                Path("C:/Windows/Fonts/arial.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            )
            if path.exists()
        ),
        None,
    )
    if font_path is None:
        pytest.skip("No TrueType font available")
    storage_root = Path(state.e2e_settings.local_storage_root)
    (storage_root / "brand-assets").mkdir(parents=True, exist_ok=True)
    (storage_root / "brand-assets" / "font.ttf").write_bytes(font_path.read_bytes())
    logo_buffer = BytesIO()
    Image.new("RGBA", (80, 40), "#FFFFFF").save(logo_buffer, format="PNG")
    (storage_root / "brand-assets" / "logo.png").write_bytes(logo_buffer.getvalue())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "composition-brand@example.com")
        brand_response = await client.post(
            "/api/v1/brands",
            headers=token,
            json={"workspace_id": workspace_id, "name": "Bakery"},
        )
        assert brand_response.status_code == 201, brand_response.text
        brand = brand_response.json()["data"]
        font_response = await client.post(
            "/api/v1/brand-assets",
            headers=token,
            json={
                "brand_id": brand["id"],
                "type": "FONT",
                "file_url": "storage://brand-assets/font.ttf",
            },
        )
        logo_response = await client.post(
            "/api/v1/brand-assets",
            headers=token,
            json={
                "brand_id": brand["id"],
                "type": "LOGO",
                "file_url": "storage://brand-assets/logo.png",
            },
        )
        assert font_response.status_code == logo_response.status_code == 201
        settings_response = await client.put(
            f"/api/v1/brands/{brand['id']}/settings",
            headers=token,
            json={
                "workspace_id": workspace_id,
                "visual_settings": {
                    "font_asset_id": font_response.json()["data"]["id"],
                    "logo_asset_id": logo_response.json()["data"]["id"],
                    "text_color": "#FFFFFF",
                    "safe_margin": 0.06,
                },
            },
        )
        assert settings_response.status_code == 200, settings_response.text
    monkeypatch.setattr(
        image_composition,
        "SqlAlchemyUnitOfWork",
        lambda: SqlAlchemyUnitOfWork(state.e2e_factory),
    )
    monkeypatch.setattr(
        image_composition,
        "create_image_reviewer",
        lambda settings: type(
            "Reviewer", (), {"review": lambda self, request: ImageReviewResult("APPROVED", 0.99)}
        )(),
    )
    scene_buffer = BytesIO()
    Image.new("RGB", (1024, 1024), "#8B5A2B").save(scene_buffer, format="PNG")
    result = image_composition.compose_generated_image(
        result=ImageGenerationResult(
            scene_buffer.getvalue(), "image/png", 1024, 1024, "test", "clean bakery scene", {}
        ),
        approved={"headline": "Pão quentinho", "call_to_action": "Peça já"},
        workspace_id=UUID(workspace_id),
        brand_id=UUID(brand["id"]),
        user_id=UUID(brand["created_by_user_id"]),
        settings=state.e2e_settings,
    )
    assert Image.open(BytesIO(result.image_bytes)).size == (1024, 1024)
    assert result.metadata["composition"]["font_asset_id"] == font_response.json()["data"]["id"]

    # Exercise the durable scene candidate, human decision, and resumed composition.
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        workflow_response = await client.post(
            "/api/v1/generations/image-workflows",
            headers={**token, "Idempotency-Key": "integrated-scene-review"},
            json={
                "brand_id": brand["id"],
                "campaign": "Bakery",
                "persona": "Adults",
                "compose_text": True,
                "headline": "Pão quentinho",
            },
        )
        assert workflow_response.status_code == 202, workflow_response.text
        run_id = UUID(workflow_response.json()["data"]["id"])
    writer = WriterOutput(
        caption="Café",
        direction={"briefing": "Bakery", "copy": "Pão", "visual_prompt": "Clean bakery scene"},
    )
    generated_calls: list[str] = []

    class Generator:
        def generate(self, request: object) -> ImageGenerationResult:
            generated_calls.append("generated")
            return ImageGenerationResult(
                scene_buffer.getvalue(),
                "image/png",
                1024,
                1024,
                "test",
                "Clean bakery scene",
                {},
            )

    monkeypatch.setattr(
        workflow_worker,
        "SqlAlchemyUnitOfWork",
        lambda: SqlAlchemyUnitOfWork(state.e2e_factory),
    )
    monkeypatch.setattr(workflow_worker, "create_image_generator", lambda settings: Generator())
    monkeypatch.setattr(workflow_worker, "_persist_artist_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        image_composition,
        "create_image_reviewer",
        lambda settings: type(
            "Reviewer", (), {"review": lambda self, request: ImageReviewResult("REFINE", 0.5)}
        )(),
    )
    with SqlAlchemyUnitOfWork(state.e2e_factory) as uow:
        uow.agent_workflow.workflows.transition(
            run_id, AgentWorkflowStatus.RUNNING, current_step="ARTIST"
        )
        uow.commit()
        run = uow.agent_workflow.workflows.get_internal(run_id)
        user = uow.user.users.get_by_id(UUID(brand["created_by_user_id"]))
    assert run is not None and user is not None
    candidate, _ = workflow_worker._generate_workflow_image(
        run=run,
        user=user,
        writer=writer,
        index=1,
        refinement_count=0,
        settings=state.e2e_settings,
    )
    assert candidate.metadata["scene_review_pending"] is True
    with SqlAlchemyUnitOfWork(state.e2e_factory) as uow:
        waiting = uow.agent_workflow.workflows.get_internal(run_id)
    assert waiting is not None and waiting.status == AgentWorkflowStatus.WAITING_FOR_HUMAN_REVIEW
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        decision = await client.post(
            f"/api/v1/generations/image-workflows/{run_id}/decision",
            headers=token,
            json={"decision": "APPROVE"},
        )
    assert decision.status_code == 200, decision.text
    with SqlAlchemyUnitOfWork(state.e2e_factory) as uow:
        resumed = uow.agent_workflow.workflows.get_internal(run_id)
    assert resumed is not None
    composed_image, _ = workflow_worker._generate_workflow_image(
        run=resumed,
        user=user,
        writer=writer,
        index=1,
        refinement_count=0,
        settings=state.e2e_settings,
    )
    assert len(generated_calls) == 1
    assert (
        composed_image.metadata["composition"]["scene_text_check"]["decision"] == "HUMAN_APPROVED"
    )
    assert composed_image.metadata["scene_review_source_image_id"] == str(candidate.id)


@pytest.mark.anyio
async def test_scene_review_decision_resumes_artist_through_http(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "scene-review@example.com")
        brand_response = await client.post(
            "/api/v1/brands",
            headers=token,
            json={"workspace_id": workspace_id, "name": "Scene Review Brand"},
        )
        brand_id = brand_response.json()["data"]["id"]
        created = await client.post(
            "/api/v1/generations/image-workflows",
            headers={**token, "Idempotency-Key": "scene-review-test"},
            json={
                "brand_id": brand_id,
                "campaign": "Bakery",
                "persona": "Adults",
                "compose_text": True,
                "headline": "Pão quentinho",
            },
        )
        assert created.status_code == 202, created.text
        run_id = UUID(created.json()["data"]["id"])
        scene_id = str(uuid4())
        with SqlAlchemyUnitOfWork(application.state.e2e_factory) as uow:
            run = uow.agent_workflow.workflows.get_internal(run_id)
            assert run is not None
            updated_input = dict(run.input)
            updated_input["pending_scenes"] = {"1": scene_id}
            updated_input["scene_review_reason"] = "COMPOSITION_TEXT_CHECK_INCONCLUSIVE"
            uow.agent_workflow.workflows.update_input(run_id, updated_input)
            uow.agent_workflow.workflows.transition(run_id, AgentWorkflowStatus.RUNNING)
            uow.agent_workflow.workflows.transition(
                run_id,
                AgentWorkflowStatus.WAITING_FOR_HUMAN_REVIEW,
                current_step="SCENE_REVIEW",
            )
            uow.commit()
        decision = await client.post(
            f"/api/v1/generations/image-workflows/{run_id}/decision",
            headers=token,
            json={"decision": "APPROVE"},
        )
        assert decision.status_code == 200, decision.text
        data = decision.json()["data"]
        assert data["status"] == "REFINING"
        assert data["current_step"] == "ARTIST"
        assert data["input"]["approved_scenes"] == {"1": scene_id}


@pytest.mark.anyio
async def test_independent_scene_review_resumes_same_scene(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    state = application.state
    _patch_worker_to_test_database(monkeypatch, application)
    monkeypatch.setattr(
        image_composition, "SqlAlchemyUnitOfWork", lambda: SqlAlchemyUnitOfWork(state.e2e_factory)
    )
    monkeypatch.setattr(
        image_composition, "create_storage_provider", lambda settings: state.e2e_storage
    )
    font_path = next(
        (
            path
            for path in (
                Path("C:/Windows/Fonts/arial.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            )
            if path.exists()
        ),
        None,
    )
    if font_path is None:
        pytest.skip("No TrueType font available")
    state.e2e_storage.objects["assets/font.ttf"] = font_path.read_bytes()
    logo_buffer = BytesIO()
    Image.new("RGBA", (80, 40), "#FFFFFF").save(logo_buffer, format="PNG")
    state.e2e_storage.objects["assets/logo.png"] = logo_buffer.getvalue()
    scene_buffer = BytesIO()
    Image.new("RGB", (1024, 1024), "#8B5A2B").save(scene_buffer, format="PNG")
    generated: list[str] = []

    class Generator:
        def generate(self, request: object) -> ImageGenerationResult:
            generated.append("scene")
            return ImageGenerationResult(
                scene_buffer.getvalue(), "image/png", 1024, 1024, "test", "clean scene", {}
            )

    class Artist:
        def execute(self, context: object) -> AgentExecutionResult:
            return AgentExecutionResult(
                output=ArtistOutput(visual_prompt="Clean bakery scene"),
                prompt="artist",
                prompt_template_id="agent.artist.v7",
                prompt_template_version="7.0",
                input_hash="a" * 64,
                output_hash="b" * 64,
                schema_name="ArtistOutput",
                schema_version="1.0",
                provider="fake",
                model="fake",
            )

    monkeypatch.setattr(
        image_generation_worker, "create_image_generator", lambda settings: Generator()
    )
    monkeypatch.setattr(
        image_generation_worker, "create_specialist_executor", lambda settings: Artist()
    )
    monkeypatch.setattr(
        image_composition,
        "create_image_reviewer",
        lambda settings: type(
            "Reviewer", (), {"review": lambda self, request: ImageReviewResult("REFINE", 0.5)}
        )(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "independent-review@example.com")
        other_token, _ = await _signup(client, "independent-review-other@example.com")
        brand_response = await client.post(
            "/api/v1/brands", headers=token, json={"workspace_id": workspace_id, "name": "Bakery"}
        )
        brand_id = brand_response.json()["data"]["id"]
        font_response = await client.post(
            "/api/v1/brand-assets",
            headers=token,
            json={"brand_id": brand_id, "type": "FONT", "file_url": "storage://assets/font.ttf"},
        )
        logo_response = await client.post(
            "/api/v1/brand-assets",
            headers=token,
            json={"brand_id": brand_id, "type": "LOGO", "file_url": "storage://assets/logo.png"},
        )
        assert font_response.status_code == logo_response.status_code == 201
        settings_response = await client.put(
            f"/api/v1/brands/{brand_id}/settings",
            headers=token,
            json={
                "workspace_id": workspace_id,
                "visual_settings": {
                    "font_asset_id": font_response.json()["data"]["id"],
                    "logo_asset_id": logo_response.json()["data"]["id"],
                },
            },
        )
        assert settings_response.status_code == 200
        created = await client.post(
            "/api/v1/generation-jobs",
            headers={**token, "Idempotency-Key": "review-scene-1"},
            json={
                "brand_id": brand_id,
                "artifact_type": "IMAGE",
                "operation": "CREATE",
                "briefing": "Bakery",
                "direction": "Clean scene",
                "compose_text": True,
                "headline": "Pão quentinho",
            },
        )
        assert created.status_code == 202, created.text
        job_id = created.json()["data"]["id"]
        image_generation_worker.run_image_generation(job_id)
        pending = await client.get(f"/api/v1/generation-jobs/{job_id}", headers=token)
        assert pending.json()["data"]["scene_review"]["status"] == "PENDING"
        assert "scene-reviews/" in pending.json()["data"]["scene_review"]["image_url"]
        image_generation_worker.run_image_generation(job_id)
        assert len(generated) == 1
        assert image_generation_worker.recover_stale_processing_jobs() == 0
        hidden = await client.post(
            f"/api/v1/generation-jobs/{job_id}/scene-decision",
            headers=other_token,
            json={"decision": "APPROVE"},
        )
        assert hidden.status_code == 404
        approved = await client.post(
            f"/api/v1/generation-jobs/{job_id}/scene-decision",
            headers=token,
            json={"decision": "APPROVE"},
        )
        assert approved.status_code == 200, approved.text
        queued_after_approval = len(state.e2e_queue.calls)
        approved_again = await client.post(
            f"/api/v1/generation-jobs/{job_id}/scene-decision",
            headers=token,
            json={"decision": "APPROVE"},
        )
        assert approved_again.status_code == 200, approved_again.text
        assert len(state.e2e_queue.calls) == queued_after_approval
        image_generation_worker.run_image_generation(job_id)
        completed = await client.get(f"/api/v1/generation-jobs/{job_id}", headers=token)
        assert completed.json()["data"]["status"] == "COMPLETED"
        assert "scene_review" not in completed.json()["data"]
        assert len(generated) == 1
        assert (
            completed.json()["data"]["image"]["metadata"]["composition"]["scene_text_check"][
                "decision"
            ]
            == "HUMAN_APPROVED"
        )
        rejected_job = await client.post(
            "/api/v1/generation-jobs",
            headers={**token, "Idempotency-Key": "review-scene-reject"},
            json={
                "brand_id": brand_id,
                "artifact_type": "IMAGE",
                "operation": "CREATE",
                "briefing": "Bakery",
                "direction": "Clean scene",
                "compose_text": True,
                "headline": "Pão quentinho",
            },
        )
        rejected_id = rejected_job.json()["data"]["id"]
        image_generation_worker.run_image_generation(rejected_id)
        rejected_scene_path = next(
            path for path in state.e2e_storage.objects if f"/{rejected_id}-intermediate." in path
        )
        real_delete = state.e2e_storage.delete
        delete_failures_left = 1

        def fail_first_delete(path: str) -> None:
            nonlocal delete_failures_left
            if path == rejected_scene_path and delete_failures_left:
                delete_failures_left -= 1
                raise RuntimeError("temporary storage outage")
            real_delete(path)

        monkeypatch.setattr(state.e2e_storage, "delete", fail_first_delete)
        rejected = await client.post(
            f"/api/v1/generation-jobs/{rejected_id}/scene-decision",
            headers=token,
            json={"decision": "REJECT"},
        )
        assert rejected.status_code == 200, rejected.text
        assert rejected.json()["data"]["status"] == "FAILED"
        assert rejected.json()["data"]["failure_code"] == "COMPOSITION_SCENE_REJECTED"
        assert rejected_scene_path in state.e2e_storage.objects
        assert image_generation_worker.cleanup_rejected_scene_objects() == 1
        assert rejected_scene_path not in state.e2e_storage.objects


def _assert_envelope(response: Response, *, success: bool) -> dict[str, Any]:
    body = response.json()
    assert body["success"] is success
    assert body["meta"]["request_id"] == response.headers["X-Request-ID"]
    if success:
        assert "data" in body
    else:
        assert set(body["error"]) == {"code", "message"}
    return body


async def _signup(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    response = await client.post(
        "/api/v1/auth/signup", json=signup_payload(email, f"Workspace {email}")
    )
    assert response.status_code == 201, response.text
    data = _assert_envelope(response, success=True)["data"]
    access = client.cookies.get("creator_access")
    csrf = client.cookies.get("creator_csrf")
    assert access is not None and csrf is not None
    client.cookies.clear()
    return {
        "Cookie": f"creator_access={access}; creator_csrf={csrf}",
        "Origin": "http://test",
        "X-CSRF-Token": csrf,
    }, data["workspace"]["id"]


def _auth(token: dict[str, str]) -> dict[str, str]:
    return token


async def _generate_content(
    client: AsyncClient, token: dict[str, str], workspace_id: str, *, topic: str = "Launch campaign"
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
async def test_workflow_content_reads_use_current_status_and_preserve_workspace_isolation(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "workflow-content@example.com")
        other_token, _ = await _signup(client, "workflow-content-other@example.com")
        brand = await client.post(
            "/api/v1/brands",
            headers=_auth(token),
            json={"workspace_id": workspace_id, "name": "Workflow Brand"},
        )
        assert brand.status_code == 201, brand.text
        run = await client.post(
            "/api/v1/generations/image-workflows",
            headers={**_auth(token), "Idempotency-Key": "workflow-status-test"},
            json={
                "brand_id": brand.json()["data"]["id"],
                "campaign": "Launch",
                "persona": "Adults",
            },
        )
        assert run.status_code == 202, run.text
        run_data = run.json()["data"]
        content_id = run_data["content_id"]
        with SqlAlchemyUnitOfWork(application.state.e2e_factory) as uow:
            uow.agent_workflow.workflows.transition(
                UUID(run_data["id"]), AgentWorkflowStatus.RUNNING
            )
            uow.agent_workflow.workflows.transition(
                UUID(run_data["id"]), AgentWorkflowStatus.WAITING_FOR_HUMAN_REVIEW
            )
            uow.commit()

        detail = await client.get(f"/api/v1/contents/{content_id}", headers=_auth(token))
        listing = await client.get("/api/v1/content?type=IMAGE", headers=_auth(token))
        hidden = await client.get(f"/api/v1/contents/{content_id}", headers=_auth(other_token))
        assert detail.status_code == 200, detail.text
        assert detail.json()["data"]["payload"]["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"
        listed = next(item for item in listing.json()["data"]["items"] if item["id"] == content_id)
        assert listed["payload"]["workflow_status"] == "WAITING_FOR_HUMAN_REVIEW"
        assert hidden.status_code == 404

        unrelated = await client.post(
            "/api/v1/contents",
            headers=_auth(token),
            json={
                "workspace_id": workspace_id,
                "type": "IMAGE",
                "payload": {"workflow_status": "custom"},
            },
        )
        unrelated_detail = await client.get(
            f"/api/v1/contents/{unrelated.json()['data']['id']}", headers=_auth(token)
        )
        assert unrelated_detail.json()["data"]["payload"]["workflow_status"] == "custom"


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


@pytest.mark.anyio
async def test_independent_generation_job_is_idempotent_and_workspace_scoped(
    e2e: tuple[object, object],
) -> None:
    application, _ = e2e
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "independent-generation@example.com")
        other_token, _ = await _signup(client, "independent-other@example.com")
        brand_response = await client.post(
            "/api/v1/brands",
            headers=_auth(token),
            json={
                "workspace_id": workspace_id,
                "name": "Generation Brand",
                "brand_voice": "Clear and direct",
            },
        )
        assert brand_response.status_code == 201, brand_response.text
        brand_id = _assert_envelope(brand_response, success=True)["data"]["id"]
        payload = {
            "brand_id": brand_id,
            "artifact_type": "COPY",
            "operation": "CREATE",
            "briefing": "Write concise launch copy",
        }
        headers = {**_auth(token), "Idempotency-Key": "independent-copy-1"}
        created = await client.post("/api/v1/generation-jobs", headers=headers, json=payload)
        repeated = await client.post("/api/v1/generation-jobs", headers=headers, json=payload)
        job_id = _assert_envelope(created, success=True)["data"]["id"]
        fetched = await client.get(f"/api/v1/generation-jobs/{job_id}", headers=_auth(token))
        hidden = await client.get(f"/api/v1/generation-jobs/{job_id}", headers=_auth(other_token))

    assert created.status_code == 202
    assert repeated.status_code == 202
    assert _assert_envelope(repeated, success=True)["data"]["id"] == job_id
    assert fetched.status_code == 200
    fetched_data = _assert_envelope(fetched, success=True)["data"]
    assert fetched_data["artifact_type"] == "COPY"
    assert fetched_data["operation"] == "CREATE"
    assert fetched_data["status"] == "PENDING"
    queue: FakeGenerationQueue = application.state.e2e_queue
    assert len(queue.generation_calls) == 1
    assert hidden.status_code == 404


@pytest.mark.anyio
async def test_independent_image_job_runs_artist_and_returns_reviewed_image(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    _patch_worker_to_test_database(monkeypatch, application)

    class FakeArtist:
        def execute(self, context: object) -> AgentExecutionResult:
            assert context.inputs["visual_direction"] == "Minimal studio composition"
            assert context.inputs["brand_context"]["visual_settings"] == {
                "typography": "bold sans serif"
            }
            assert context.inputs["brand_context"]["colors"] == [{"name": "Plum", "hex": "#770044"}]
            return AgentExecutionResult(
                output=ArtistOutput(visual_prompt="Artist composed visual prompt"),
                prompt="Artist specialist prompt",
                prompt_template_id="agent.artist.v3",
                prompt_template_version="3.0",
                input_hash="a" * 64,
                output_hash="b" * 64,
                schema_name="ArtistOutput",
                schema_version="1.0",
                provider="fake-artist",
                model="artist-model",
            )

    class FakeReviewer:
        def review(self, request: object) -> ImageReviewResult:
            assert request.prompt == "Artist composed visual prompt"
            assert request.brand_context["visual_settings"] == {"typography": "bold sans serif"}
            assert request.brand_context["colors"] == [{"name": "Plum", "hex": "#770044"}]
            return ImageReviewResult(
                decision="APPROVED",
                score=0.94,
                feedback=("Brand context is respected",),
                provider="fake-reviewer",
                model="review-model",
            )

    monkeypatch.setattr(
        image_generation_worker,
        "create_specialist_executor",
        lambda _settings: FakeArtist(),
    )
    monkeypatch.setattr(
        image_generation_worker,
        "create_image_reviewer",
        lambda _settings: FakeReviewer(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "independent-image@example.com")
        brand_response = await client.post(
            "/api/v1/brands",
            headers=_auth(token),
            json={"workspace_id": workspace_id, "name": "Image Brand"},
        )
        brand_id = _assert_envelope(brand_response, success=True)["data"]["id"]
        settings_response = await client.put(
            f"/api/v1/brands/{brand_id}/settings",
            headers=_auth(token),
            json={
                "workspace_id": workspace_id,
                "visual_settings": {"typography": "bold sans serif"},
            },
        )
        assert settings_response.status_code == 200, settings_response.text
        color_response = await client.post(
            "/api/v1/brand-colors",
            headers=_auth(token),
            json={
                "workspace_id": workspace_id,
                "brand_id": brand_id,
                "color_name": "Plum",
                "hex_code": "#770044",
            },
        )
        assert color_response.status_code == 201, color_response.text
        accepted = await client.post(
            "/api/v1/generation-jobs",
            headers={**_auth(token), "Idempotency-Key": "independent-image-1"},
            json={
                "brand_id": brand_id,
                "artifact_type": "IMAGE",
                "operation": "CREATE",
                "briefing": "Create a launch visual",
                "direction": "Minimal studio composition",
                "restrictions": ["No third-party marks"],
                "review_image": True,
            },
        )
        assert accepted.status_code == 202, accepted.text
        accepted_data = _assert_envelope(accepted, success=True)["data"]
        image_generation_worker.run_image_generation(
            accepted_data["id"], _assert_envelope(accepted, success=True)["meta"]["request_id"]
        )
        completed = await client.get(
            f"/api/v1/generation-jobs/{accepted_data['id']}", headers=_auth(token)
        )

    assert completed.status_code == 200, completed.text
    result = _assert_envelope(completed, success=True)["data"]
    assert result["status"] == "COMPLETED"
    assert result["image"]["prompt"] == "Artist composed visual prompt"
    assert result["image"]["metadata"]["artist"]["provider"] == "fake-artist"
    assert result["image"]["metadata"]["review"]["decision"] == "APPROVED"
    assert result["image"]["metadata"]["review"]["feedback"] == ["Brand context is respected"]


@pytest.mark.anyio
async def test_image_transform_uses_exact_version_and_appends_after_review(
    e2e: tuple[object, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _ = e2e
    state = application.state
    _patch_worker_to_test_database(monkeypatch, application)

    class Artist:
        def execute(self, context: object) -> AgentExecutionResult:
            return AgentExecutionResult(
                output=ArtistOutput(visual_prompt="Preserve the original campaign concept"),
                prompt="Artist prompt",
                prompt_template_id="agent.artist.v3",
                prompt_template_version="3.0",
                input_hash="a" * 64,
                output_hash="b" * 64,
                schema_name="ArtistOutput",
                schema_version="1.0",
                provider="test-artist",
                model="test-artist-model",
            )

    class Generator:
        def generate(self, request: object) -> ImageGenerationResult:
            requested = getattr(request, "size", None) or "640x480"
            width, height = (int(part) for part in requested.split("x"))
            output = BytesIO()
            Image.new("RGB", (width, height), "#704060").save(output, format="PNG")
            return ImageGenerationResult(
                image_bytes=output.getvalue(),
                mime_type="image/png",
                width=width,
                height=height,
                model="test-image-model",
                prompt="test prompt",
                metadata={"provider": "test-image"},
            )

    state.e2e_image_generator = Generator()
    monkeypatch.setattr(
        image_generation_worker,
        "create_specialist_executor",
        lambda _settings: Artist(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        token, workspace_id = await _signup(client, "image-transform@example.com")
        outsider, _ = await _signup(client, "image-transform-outsider@example.com")
        brand_response = await client.post(
            "/api/v1/brands",
            headers=_auth(token),
            json={"workspace_id": workspace_id, "name": "Transform Brand"},
        )
        brand_id = _assert_envelope(brand_response, success=True)["data"]["id"]
        created = await client.post(
            "/api/v1/generation-jobs",
            headers={**_auth(token), "Idempotency-Key": "transform-source-create"},
            json={
                "brand_id": brand_id,
                "artifact_type": "IMAGE",
                "operation": "CREATE",
                "briefing": "Create the source campaign visual",
                "direction": "A centered product on a plum background",
            },
        )
        assert created.status_code == 202, created.text
        source_job = _assert_envelope(created, success=True)["data"]
        image_generation_worker.run_image_generation(source_job["id"])
        source_result = await client.get(
            f"/api/v1/generation-jobs/{source_job['id']}", headers=_auth(token)
        )
        source_data = _assert_envelope(source_result, success=True)["data"]
        source_image = source_data["image"]

        transformed = await client.post(
            "/api/v1/generation-jobs",
            headers={**_auth(token), "Idempotency-Key": "transform-source-to-story"},
            json={
                "brand_id": brand_id,
                "artifact_type": "IMAGE",
                "operation": "TRANSFORM",
                "briefing": "Adapt this campaign to stories",
                "direction": "Preserve the product and perceived scale",
                "source_content_id": source_data["content_id"],
                "source_image_id": source_image["id"],
                "destination_preset": "1080x1920",
            },
        )
        assert transformed.status_code == 202, transformed.text
        transform_job = _assert_envelope(transformed, success=True)["data"]
        hidden = await client.get(
            f"/api/v1/generation-jobs/{transform_job['id']}", headers=_auth(outsider)
        )
        image_generation_worker.run_image_generation(transform_job["id"])
        pending = await client.get(
            f"/api/v1/generation-jobs/{transform_job['id']}", headers=_auth(token)
        )
        pending_data = _assert_envelope(pending, success=True)["data"]
        approved = await client.post(
            f"/api/v1/generation-jobs/{transform_job['id']}/scene-decision",
            headers=_auth(token),
            json={"decision": "APPROVE"},
        )
        assert approved.status_code == 200, approved.text
        image_generation_worker.run_image_generation(transform_job["id"])
        completed = await client.get(
            f"/api/v1/generation-jobs/{transform_job['id']}", headers=_auth(token)
        )

    assert hidden.status_code == 404
    assert pending_data["status"] == "PROCESSING"
    assert pending_data["scene_review"]["status"] == "PENDING"
    result = _assert_envelope(completed, success=True)["data"]
    assert result["status"] == "COMPLETED"
    assert result["image"]["version_number"] == source_image["version_number"] + 1
    assert result["image"]["metadata"]["source_image_id"] == source_image["id"]
    assert result["image"]["metadata"]["source_version_number"] == source_image["version_number"]
    assert result["image"]["width"] == 1080 and result["image"]["height"] == 1920
