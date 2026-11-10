from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from PIL import Image

from creator.config import Settings
from creator.domain.generation import GenerationJobStatus
from creator.generation.ports import GenerationJobRecord, ImageGenerationWorkItem
from creator.generation.storage_service import GeneratedImage
from creator.image_models import DEFAULT_OPENAI_IMAGE_MODEL
from creator.integrations.gemini.exceptions import GeminiBlockedContentError, GeminiTimeoutError
from creator.integrations.gemini.image_generator import (
    GeminiImageGenerationRequest,
    GeminiImageGenerationResult,
)
from creator.services.agents.contracts import (
    AgentExecutionContext,
    AgentExecutionResult,
    ArtistOutput,
)
from creator.services.ai.image_provider import (
    ImageGenerationResult,
    ImageProviderInvalidResponseError,
)
from creator.services.ai.provider import ProviderNotConfiguredError
from creator.services.ai.reviewer import ImageReviewRequest, ImageReviewResult
from creator.services.storage.provider import StorageValidationError
from creator.user.ports import UserRecord
from creator.workers import image_generation

NOW = datetime(2026, 9, 1, tzinfo=UTC)
JOB_BRAND_ID = UUID("31000000-0000-0000-0000-000000000001")
OTHER_BRAND_ID = UUID("31000000-0000-0000-0000-000000000002")


def png_bytes(width: int, height: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return output.getvalue()


class FakeImageGenerator:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.requests: list[GeminiImageGenerationRequest] = []

    def generate(self, request: GeminiImageGenerationRequest) -> GeminiImageGenerationResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        try:
            width, height = (int(part) for part in request.size.split("x"))
        except (AttributeError, ValueError):
            width, height = 2, 3
        return GeminiImageGenerationResult(
            image_bytes=png_bytes(width, height),
            mime_type="image/png",
            width=width,
            height=height,
            model=request.model or "gemini-image",
            prompt=request.prompt,
            metadata={"provider": "gemini"},
        )


class FakeSpecialistExecutor:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.contexts: list[AgentExecutionContext] = []

    def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        self.contexts.append(context)
        if self.error is not None:
            raise self.error
        return AgentExecutionResult(
            output=ArtistOutput(visual_prompt="Artist composed visual prompt"),
            prompt="Artist specialist prompt",
            prompt_template_id=context.prompt_template_id,
            prompt_template_version=context.prompt_template_version,
            input_hash="a" * 64,
            output_hash="b" * 64,
            schema_name="ArtistOutput",
            schema_version="1.0",
            provider="fake-artist",
            model="artist-model",
        )


class FakeReviewer:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        result: ImageReviewResult | None = None,
    ) -> None:
        self.error = error
        self.result = result or ImageReviewResult(
            decision="APPROVED",
            score=0.94,
            feedback=("Brand context is respected",),
            provider="fake-reviewer",
            model="review-model",
        )
        self.requests: list[ImageReviewRequest] = []

    def review(self, request: ImageReviewRequest) -> ImageReviewResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


class FakeStorage:
    def download(self, path: str, *, max_bytes: int) -> bytes:
        assert path.startswith("users/")
        return png_bytes(1, 1)


class FakeImageGenerationRepository:
    def __init__(self, work_item: ImageGenerationWorkItem | None = None) -> None:
        self.work_item = work_item
        self.failed: list[dict[str, object]] = []
        self.stale_calls: list[dict[str, object]] = []
        self.brand_requests: list[UUID] = []
        self.brand_results: list[object | None] = []
        self.brand_settings: object | None = None
        self.brand_colors: list[object] = []

    def claim_pending_by_id(self, job_id: UUID) -> ImageGenerationWorkItem | None:
        return self.work_item

    def fail_job(
        self,
        job_id: UUID,
        *,
        failure_code: str,
        failure_message: str,
    ) -> GenerationJobRecord:
        self.failed.append(
            {
                "job_id": job_id,
                "failure_code": failure_code,
                "failure_message": failure_message,
            }
        )
        assert self.work_item is not None
        return self.work_item.job

    def fail_stale_processing(
        self,
        *,
        older_than: datetime,
        failure_code: str,
        failure_message: str,
    ) -> int:
        self.stale_calls.append(
            {
                "older_than": older_than,
                "failure_code": failure_code,
                "failure_message": failure_message,
            }
        )
        return 2


class FakeUnitOfWork:
    def __init__(self, repository: FakeImageGenerationRepository) -> None:
        self.repository = repository
        self.image_generations = repository
        self.generation = SimpleNamespace(image_jobs=repository)
        self.brand = SimpleNamespace(
            brands=self,
            settings=SimpleNamespace(get_for_user=self.get_brand_settings),
            colors=SimpleNamespace(list_for_user=self.list_brand_colors),
        )
        self.commits = 0

    def __enter__(self) -> FakeUnitOfWork:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        return None

    def get_for_user(self, *, user_id: UUID, brand_id: UUID) -> object | None:
        self.repository.brand_requests.append(brand_id)
        if self.repository.brand_results:
            return self.repository.brand_results.pop(0)
        assert self.repository.work_item is not None
        return brand(brand_id=brand_id, workspace_id=self.repository.work_item.job.workspace_id)

    def get_brand_settings(self, *, user_id: UUID, brand_id: UUID) -> object | None:
        return self.repository.brand_settings

    def list_brand_colors(self, *, user_id: UUID, brand_id: UUID) -> list[object]:
        return self.repository.brand_colors


def brand(*, brand_id: UUID, workspace_id: UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=brand_id,
        workspace_id=workspace_id,
        name="Test Brand",
        description="Brand description",
        brand_voice="Clear",
    )


def job_record(*, attempt_count: int = 1, max_attempts: int = 3) -> GenerationJobRecord:
    return GenerationJobRecord(
        id=UUID("50000000-0000-0000-0000-000000000001"),
        workspace_id=uuid4(),
        generation_id=uuid4(),
        content_id=uuid4(),
        status=GenerationJobStatus.PROCESSING,
        external_id=None,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        failure_code=None,
        failure_message=None,
        queued_at=NOW,
        started_at=NOW,
        completed_at=None,
        failed_at=None,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def user_record() -> UserRecord:
    return UserRecord(
        id=uuid4(),
        auth_provider_id="principal-123",
        email="principal@example.com",
        display_name="Principal Example",
        global_role="membro",
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def work_item(
    *,
    attempt_count: int = 1,
    max_attempts: int = 3,
    model: str = "gemini-image",
    parameters: dict[str, object] | None = None,
    brand_id: UUID | None = None,
) -> ImageGenerationWorkItem:
    return ImageGenerationWorkItem(
        job=job_record(attempt_count=attempt_count, max_attempts=max_attempts),
        model=model,
        prompt="Generate",
        parameters=parameters or {"style": "photographic"},
        requested_by_user=user_record(),
        brand_id=brand_id,
    )


def patch_worker(
    monkeypatch: pytest.MonkeyPatch,
    *,
    repository: FakeImageGenerationRepository,
    generator: FakeImageGenerator,
    persisted: list[object] | None = None,
    specialist: FakeSpecialistExecutor | None = None,
    reviewer: FakeReviewer | None = None,
) -> None:
    monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(image_generation, "get_settings", lambda: Settings(_env_file=None))
    monkeypatch.setattr(
        image_generation,
        "SqlAlchemyUnitOfWork",
        lambda: FakeUnitOfWork(repository),
    )
    monkeypatch.setattr(image_generation, "create_image_generator", lambda settings: generator)
    monkeypatch.setattr(
        image_generation,
        "create_specialist_executor",
        lambda settings: specialist or FakeSpecialistExecutor(),
    )
    if reviewer is not None:
        monkeypatch.setattr(image_generation, "create_image_reviewer", lambda settings: reviewer)
    monkeypatch.setattr(image_generation, "create_storage_provider", lambda settings: FakeStorage())

    def fake_persist_generated_image(**kwargs: object) -> object:
        if persisted is not None:
            persisted.append(kwargs)
        return object()

    monkeypatch.setattr(image_generation, "persist_generated_image", fake_persist_generated_image)


def test_run_image_generation_completes_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    persisted: list[object] = []
    repository = FakeImageGenerationRepository(work_item())
    generator = FakeImageGenerator()
    patch_worker(monkeypatch, repository=repository, generator=generator, persisted=persisted)

    image_generation.run_image_generation(
        "50000000-0000-0000-0000-000000000001",
        "70000000-0000-0000-0000-000000000001",
    )

    assert len(generator.requests) == 1
    assert persisted
    assert repository.failed == []


def test_transform_holds_edited_variation_for_human_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_input = image_request_input(operation="TRANSFORM")
    request_input["source_content_id"] = str(uuid4())
    request_input["source_image_id"] = str(uuid4())
    request_input["destination_preset"] = "1080x1350"
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={
                "request_input": request_input,
                "source_image": {
                    "storage_path": "users/principal/contents/id/versions/1/image.png",
                    "mime_type": "image/png",
                    "width": 1,
                    "height": 1,
                },
                "destination_preset": "1080x1350",
            },
        )
    )
    generator = FakeImageGenerator()
    persisted: list[object] = []
    held: list[ImageGenerationResult] = []
    patch_worker(monkeypatch, repository=repository, generator=generator, persisted=persisted)
    monkeypatch.setattr(image_generation, "_authorized_brand_context", lambda item: {})
    monkeypatch.setattr(
        image_generation,
        "_hold_scene_for_review",
        lambda item, result, settings: held.append(result),
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert len(generator.requests) == 1
    assert generator.requests[0].source_image == png_bytes(1, 1)
    assert generator.requests[0].size == "1080x1350"
    assert len(held) == 1
    assert held[0].width == 1080 and held[0].height == 1350
    assert persisted == []


def test_opt_in_composes_before_persistence_and_reviews_final_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_input = image_request_input()
    request_input.update({"compose_text": True, "headline": "Pão quentinho"})
    repository = FakeImageGenerationRepository(
        work_item(brand_id=JOB_BRAND_ID, parameters={"request_input": request_input})
    )
    generator = FakeImageGenerator()
    reviewer = FakeReviewer()
    persisted: list[object] = []
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=generator,
        reviewer=reviewer,
        persisted=persisted,
    )
    monkeypatch.setattr(image_generation, "_authorized_brand_context", lambda item: {})
    composed: list[dict[str, object]] = []

    def fake_compose(**kwargs: object) -> ImageGenerationResult:
        composed.append(kwargs)
        result = kwargs["result"]
        return ImageGenerationResult(
            image_bytes=b"composed",
            mime_type="image/png",
            width=result.width,
            height=result.height,
            model=result.model,
            prompt=result.prompt,
            metadata={"composition": {"approved_text": kwargs["approved"]}},
        )

    monkeypatch.setattr(image_generation, "compose_generated_image", fake_compose)
    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert generator.requests[0].prompt.endswith(image_generation.SCENE_SUFFIX)
    assert composed[0]["brand_id"] == JOB_BRAND_ID
    assert reviewer.requests[0].image_bytes == b"composed"
    assert persisted_metadata(persisted)["composition"]["approved_text"] == {
        "headline": "Pão quentinho"
    }


def test_run_image_generation_raises_retryable_failure_before_last_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeImageGenerationRepository(work_item(attempt_count=1, max_attempts=3))
    generator = FakeImageGenerator(error=GeminiTimeoutError("slow", retryable=True))
    patch_worker(monkeypatch, repository=repository, generator=generator)

    with pytest.raises(GeminiTimeoutError):
        image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed == []


def test_run_image_generation_marks_final_retryable_failure_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeImageGenerationRepository(work_item(attempt_count=3, max_attempts=3))
    generator = FakeImageGenerator(error=GeminiTimeoutError("slow", retryable=True))
    patch_worker(monkeypatch, repository=repository, generator=generator)

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "PROVIDER_TIMEOUT"


def test_run_image_generation_marks_permanent_failure_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeImageGenerationRepository(work_item(attempt_count=1, max_attempts=3))
    generator = FakeImageGenerator(error=GeminiBlockedContentError("blocked"))
    patch_worker(monkeypatch, repository=repository, generator=generator)

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "PROVIDER_CONTENT_BLOCKED"


def test_run_image_generation_marks_storage_validation_failure_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeImageGenerationRepository(work_item())
    generator = FakeImageGenerator()
    patch_worker(monkeypatch, repository=repository, generator=generator)
    monkeypatch.setattr(
        image_generation,
        "persist_generated_image",
        lambda **kwargs: (_ for _ in ()).throw(StorageValidationError("invalid image")),
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "STORAGE_UPLOAD_FAILED"


def test_run_image_generation_does_not_retry_unknown_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeImageGenerationRepository(work_item(attempt_count=1, max_attempts=3))
    generator = FakeImageGenerator()
    patch_worker(monkeypatch, repository=repository, generator=generator)
    monkeypatch.setattr(
        image_generation,
        "persist_generated_image",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("bug")),
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "IMAGE_GENERATION_FAILED"


def test_recover_stale_processing_jobs_marks_old_jobs_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeImageGenerationRepository()
    patch_worker(monkeypatch, repository=repository, generator=FakeImageGenerator())

    recovered = image_generation.recover_stale_processing_jobs()

    assert recovered == 2
    assert repository.stale_calls[0]["failure_code"] == "IMAGE_GENERATION_STALE_PROCESSING"


def image_request_input(
    *,
    brand_id: UUID | None = JOB_BRAND_ID,
    briefing: str | None = "Create a launch visual",
    direction: str | None = "Minimal studio composition",
    operation: str = "CREATE",
    review_image: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_type": "IMAGE",
        "operation": operation,
    }
    if brand_id is not None:
        payload["brand_id"] = str(brand_id)
    if briefing is not None:
        payload["briefing"] = briefing
    if direction is not None:
        payload["direction"] = direction
    if review_image:
        payload["review_image"] = True
    return payload


def persisted_metadata(persisted: list[object]) -> dict[str, object]:
    call = persisted[-1]
    assert isinstance(call, dict)
    image = call["image"]
    assert isinstance(image, GeneratedImage)
    return image.metadata


def test_run_image_generation_uses_job_brand_and_specialist_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specialist = FakeSpecialistExecutor()
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={
                "request_input": image_request_input(brand_id=OTHER_BRAND_ID),
            },
        )
    )
    generator = FakeImageGenerator()
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=generator,
        specialist=specialist,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.brand_requests == [JOB_BRAND_ID]
    assert len(specialist.contexts) == 1
    assert specialist.contexts[0].brand_id == JOB_BRAND_ID
    assert specialist.contexts[0].prompt_template_id == "agent.artist.v7"
    assert specialist.contexts[0].prompt_template_version == "7.0"
    assert specialist.contexts[0].inputs["briefing"] == "Create a launch visual"
    assert specialist.contexts[0].inputs["visual_direction"] == "Minimal studio composition"
    assert generator.requests[0].prompt == "Artist composed visual prompt"
    assert repository.failed == []


def test_artist_and_reviewer_receive_only_authorized_brand_settings_and_colors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = work_item(
        brand_id=JOB_BRAND_ID,
        parameters={"request_input": image_request_input(review_image=True)},
    )
    repository = FakeImageGenerationRepository(item)
    repository.brand_settings = SimpleNamespace(
        brand_id=JOB_BRAND_ID,
        workspace_id=item.job.workspace_id,
        voice_settings={"tone": "warm"},
        visual_settings={"typography": "bold sans", "style": "editorial"},
    )
    repository.brand_colors = [
        SimpleNamespace(
            id=uuid4(),
            brand_id=JOB_BRAND_ID,
            workspace_id=uuid4(),
            order=0,
            color_name="Other Workspace",
            hex_code="#000000",
        ),
        SimpleNamespace(
            id=uuid4(),
            brand_id=JOB_BRAND_ID,
            workspace_id=item.job.workspace_id,
            order=2,
            color_name="Orange",
            hex_code="#ff6600",
        ),
        SimpleNamespace(
            id=uuid4(),
            brand_id=JOB_BRAND_ID,
            workspace_id=item.job.workspace_id,
            order=1,
            color_name="Plum",
            hex_code="#770044",
        ),
    ]
    specialist = FakeSpecialistExecutor()
    reviewer = FakeReviewer()
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=FakeImageGenerator(),
        specialist=specialist,
        reviewer=reviewer,
    )

    image_generation.run_image_generation(str(item.job.id))

    context = specialist.contexts[0].inputs["brand_context"]
    assert isinstance(context, dict)
    assert context["visual_settings"] == {"typography": "bold sans", "style": "editorial"}
    assert context["voice_settings"] == {"tone": "warm"}
    assert context["colors"] == [
        {"name": "Plum", "hex": "#770044"},
        {"name": "Orange", "hex": "#ff6600"},
    ]
    assert reviewer.requests[0].brand_context == context


def test_brand_context_ignores_settings_from_another_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = work_item(brand_id=JOB_BRAND_ID)
    repository = FakeImageGenerationRepository(item)
    repository.brand_settings = SimpleNamespace(
        brand_id=JOB_BRAND_ID,
        workspace_id=uuid4(),
        voice_settings={"tone": "secret"},
        visual_settings={"style": "secret"},
    )
    monkeypatch.setattr(
        image_generation, "SqlAlchemyUnitOfWork", lambda: FakeUnitOfWork(repository)
    )

    context = image_generation._authorized_brand_context(item)

    assert context is not None
    assert "voice_settings" not in context
    assert "visual_settings" not in context


def test_run_image_generation_fails_without_job_brand_for_image_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specialist = FakeSpecialistExecutor()
    repository = FakeImageGenerationRepository(
        work_item(brand_id=None, parameters={"request_input": image_request_input()})
    )
    generator = FakeImageGenerator()
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=generator,
        specialist=specialist,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "BRAND_CONTEXT_UNAVAILABLE"
    assert repository.brand_requests == []
    assert specialist.contexts == []
    assert generator.requests == []


def test_run_image_generation_rejects_brand_from_other_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specialist = FakeSpecialistExecutor()
    item = work_item(brand_id=JOB_BRAND_ID, parameters={"request_input": image_request_input()})
    repository = FakeImageGenerationRepository(item)
    repository.brand_results = [brand(brand_id=JOB_BRAND_ID, workspace_id=uuid4())]
    generator = FakeImageGenerator()
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=generator,
        specialist=specialist,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "BRAND_CONTEXT_UNAVAILABLE"
    assert specialist.contexts == []
    assert generator.requests == []


def test_run_image_generation_uses_resolved_input_over_request_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specialist = FakeSpecialistExecutor()
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={
                "resolved_input": {
                    "briefing": "Resolved planning brief",
                    "direction": "Resolved planning direction",
                },
                "request_input": image_request_input(
                    briefing="Raw client brief",
                    direction="Raw client direction",
                ),
            },
        )
    )
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=FakeImageGenerator(),
        specialist=specialist,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert specialist.contexts[0].inputs["briefing"] == "Resolved planning brief"
    assert specialist.contexts[0].inputs["visual_direction"] == "Resolved planning direction"


def test_run_image_generation_falls_back_to_legacy_request_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specialist = FakeSpecialistExecutor()
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={
                "request_input": image_request_input(
                    briefing="Legacy brief",
                    direction="Legacy direction",
                ),
            },
        )
    )
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=FakeImageGenerator(),
        specialist=specialist,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert specialist.contexts[0].inputs["briefing"] == "Legacy brief"
    assert specialist.contexts[0].inputs["visual_direction"] == "Legacy direction"


def test_run_image_generation_fails_without_prompt_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specialist = FakeSpecialistExecutor()
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={
                "request_input": image_request_input(briefing=None, direction=None),
            },
        )
    )
    generator = FakeImageGenerator()
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=generator,
        specialist=specialist,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "PROMPT_CONTEXT_UNAVAILABLE"
    assert specialist.contexts == []
    assert generator.requests == []


def test_run_image_generation_review_uses_resolved_briefing_and_job_brand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted: list[object] = []
    reviewer = FakeReviewer()
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={
                "resolved_input": {
                    "briefing": "Resolved planning brief",
                    "direction": "Resolved planning direction",
                },
                "request_input": image_request_input(
                    briefing="Raw client brief",
                    direction="Raw client direction",
                    review_image=True,
                ),
            },
        )
    )
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=FakeImageGenerator(),
        persisted=persisted,
        reviewer=reviewer,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert reviewer.requests[0].briefing == "Resolved planning brief"
    assert reviewer.requests[0].brand_context["brand_id"] == str(JOB_BRAND_ID)
    assert persisted_metadata(persisted)["review"] == {
        "decision": "APPROVED",
        "score": 0.94,
        "feedback": ["Brand context is respected"],
        "safety_issues": [],
        "provider": "fake-reviewer",
        "model": "review-model",
    }
    assert repository.failed == []


@pytest.mark.parametrize(
    ("reviewer_error", "expected_code"),
    [
        (ImageProviderInvalidResponseError("invalid review"), "PROVIDER_INVALID_RESPONSE"),
        (ProviderNotConfiguredError("reviewer missing"), "PROVIDER_AUTHENTICATION_FAILED"),
        (RuntimeError("sdk transport failure"), "IMAGE_REVIEW_FAILED"),
    ],
)
def test_run_image_generation_review_failure_is_best_effort(
    monkeypatch: pytest.MonkeyPatch,
    reviewer_error: Exception,
    expected_code: str,
) -> None:
    persisted: list[object] = []
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={
                "request_input": image_request_input(review_image=True),
            },
        )
    )
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=FakeImageGenerator(),
        persisted=persisted,
        reviewer=FakeReviewer(error=reviewer_error),
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert persisted_metadata(persisted)["review"] == {
        "status": "failed",
        "error_code": expected_code,
    }
    assert repository.failed == []


def test_run_image_generation_skips_review_without_authorized_brand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted: list[object] = []
    reviewer = FakeReviewer()
    item = work_item(
        brand_id=JOB_BRAND_ID,
        parameters={"request_input": image_request_input(review_image=True)},
    )
    repository = FakeImageGenerationRepository(item)
    repository.brand_results = [
        brand(brand_id=JOB_BRAND_ID, workspace_id=item.job.workspace_id),
        None,
    ]
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=FakeImageGenerator(),
        persisted=persisted,
        reviewer=reviewer,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert reviewer.requests == []
    assert persisted_metadata(persisted)["review"] == {
        "status": "failed",
        "error_code": "BRAND_CONTEXT_UNAVAILABLE",
    }
    assert repository.failed == []


@pytest.mark.parametrize(
    ("requested_model", "expected_model"),
    [
        ("gemini-2.5-flash-image", DEFAULT_OPENAI_IMAGE_MODEL),
        ("imagen-3.0", DEFAULT_OPENAI_IMAGE_MODEL),
        ("gpt-image-2.6-flare", DEFAULT_OPENAI_IMAGE_MODEL),
        ("custom-image-model", "custom-image-model"),
    ],
)
def test_run_image_generation_normalizes_legacy_model(
    monkeypatch: pytest.MonkeyPatch,
    requested_model: str,
    expected_model: str,
) -> None:
    repository = FakeImageGenerationRepository(work_item(model=requested_model))
    generator = FakeImageGenerator()
    patch_worker(monkeypatch, repository=repository, generator=generator)

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert generator.requests[0].model == expected_model


def test_run_image_generation_maps_provider_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeImageGenerationRepository(work_item())
    generator = FakeImageGenerator(error=ProviderNotConfiguredError("missing key"))
    patch_worker(monkeypatch, repository=repository, generator=generator)

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "PROVIDER_AUTHENTICATION_FAILED"


def test_run_image_generation_maps_specialist_provider_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specialist = FakeSpecialistExecutor(error=ProviderNotConfiguredError("missing key"))
    repository = FakeImageGenerationRepository(
        work_item(
            brand_id=JOB_BRAND_ID,
            parameters={"request_input": image_request_input()},
        )
    )
    generator = FakeImageGenerator()
    patch_worker(
        monkeypatch,
        repository=repository,
        generator=generator,
        specialist=specialist,
    )

    image_generation.run_image_generation("50000000-0000-0000-0000-000000000001")

    assert repository.failed[0]["failure_code"] == "PROVIDER_AUTHENTICATION_FAILED"
    assert generator.requests == []
