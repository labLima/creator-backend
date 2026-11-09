from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from creator.config import Settings
from creator.content.ports import ContentRecord, ImageRecord
from creator.domain.exceptions import EntityNotFoundError
from creator.domain.generation import GenerationJobStatus
from creator.generation.ports import GenerationJobRecord
from creator.generation.schemas import IndependentGenerationRequest
from creator.generation.service import (
    IdempotencyConflictError,
    submit_image_regeneration,
    submit_independent_generation,
)
from creator.image_models import DEFAULT_OPENAI_IMAGE_MODEL
from creator.planning.ports import PlanningRecord
from creator.post_structure.ports import PostStructureRecord
from creator.services.ai.image_provider import normalize_image_model
from creator.user.ports import UserRecord

NOW = datetime(2026, 11, 5, tzinfo=UTC)
USER = UserRecord(
    id=UUID("10000000-0000-0000-0000-000000000001"),
    external_id="principal-1",
    email=None,
    display_name="Test",
    global_role="membro",
    created_at=NOW,
    updated_at=NOW,
    deleted_at=None,
)
BRAND_ID = UUID("20000000-0000-0000-0000-000000000001")
WORKSPACE_ID = UUID("30000000-0000-0000-0000-000000000001")
CONTENT_ID = UUID("40000000-0000-0000-0000-000000000001")


def content_record() -> ContentRecord:
    return ContentRecord(
        id=CONTENT_ID,
        workspace_id=WORKSPACE_ID,
        created_by_user_id=USER.id,
        content_type="TEXT",
        title="Launch",
        payload={"text": "Existing caption"},
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
        brand_id=BRAND_ID,
    )


class FakeUnitOfWork:
    def __init__(
        self,
        *,
        brand: object | None = None,
        existing=None,
        source=None,
        planning: PlanningRecord | None = None,
        post_structure: PostStructureRecord | None = None,
        image: ImageRecord | None = None,
    ) -> None:
        self.brand_record = brand
        self.existing = existing
        self.source = source if source is not None else content_record()
        self.image = image
        self.created: list[dict[str, object]] = []
        self.commits = 0
        self.rollbacks = 0
        self.brand = SimpleNamespace(brands=SimpleNamespace(get_for_user=self.get_brand))
        self.planning = SimpleNamespace(get_for_user=lambda **_: planning)
        self.post_structures = SimpleNamespace(get_for_user=lambda **_: post_structure)
        self.user = SimpleNamespace(settings=SimpleNamespace(get_by_user_id=lambda *_: None))
        self.contents = SimpleNamespace(
            user_has_workspace_access=lambda **_: True,
            get_by_id_for_user=lambda **_: self.source,
            get_detail_by_id_for_user=lambda **_: SimpleNamespace(
                content=self.source, images=[self.image] if self.image is not None else []
            ),
            list_text_versions=lambda **_: [
                SimpleNamespace(artifact_type="COPY", text="Earlier copy"),
                SimpleNamespace(artifact_type="CAPTION", text="Earlier caption"),
            ],
            add=lambda **kwargs: content_record(),
        )
        image_jobs = SimpleNamespace(
            get_job_by_external_id_for_user=lambda **_: self.existing,
            get_status_for_user=lambda **_: SimpleNamespace(
                parameters={"idempotency_fingerprint": self.fingerprint}
            ),
            get_status_by_external_id_for_user=lambda **_: None,
            get_image_for_user=lambda **_: self.image,
            create_image_generation=self.create_job,
        )
        self.generation = SimpleNamespace(image_jobs=image_jobs)
        self.fingerprint: str | None = None

    def get_brand(self, **_: object) -> object | None:
        return self.brand_record

    def create_job(self, **kwargs: object) -> GenerationJobRecord:
        self.created.append(kwargs)
        parameters = kwargs["parameters"]
        assert isinstance(parameters, dict)
        fingerprint = parameters.get("idempotency_fingerprint")
        if not isinstance(fingerprint, str):
            idempotency = parameters.get("idempotency")
            candidate = (
                idempotency.get("request_fingerprint") if isinstance(idempotency, dict) else None
            )
            fingerprint = candidate if isinstance(candidate, str) else None
        self.fingerprint = fingerprint
        return GenerationJobRecord(
            id=uuid4(),
            workspace_id=WORKSPACE_ID,
            generation_id=uuid4(),
            content_id=CONTENT_ID,
            status=GenerationJobStatus.PENDING,
            external_id=kwargs["external_id"],
            attempt_count=0,
            max_attempts=kwargs["max_attempts"],
            failure_code=None,
            failure_message=None,
            queued_at=NOW,
            started_at=None,
            completed_at=None,
            failed_at=None,
            created_at=NOW,
            updated_at=NOW,
            deleted_at=None,
            artifact_type=kwargs.get("artifact_type", "IMAGE"),
            operation=kwargs.get("operation", "CREATE"),
            idempotency_key=kwargs.get("idempotency_key"),
        )

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeQueue:
    def __init__(self) -> None:
        self.images: list[UUID] = []
        self.generations: list[UUID] = []

    def enqueue_image_generation(self, *, job_id: UUID, request_id: UUID) -> object:
        self.images.append(job_id)
        return object()

    def enqueue_generation_job(self, *, job_id: UUID, request_id: UUID) -> object:
        self.generations.append(job_id)
        return object()


def brand() -> object:
    return SimpleNamespace(
        id=BRAND_ID,
        workspace_id=WORKSPACE_ID,
        name="Example",
        brand_voice="Direct",
        description="",
    )


def test_submit_copy_uses_writer_and_enqueues_idempotently() -> None:
    uow = FakeUnitOfWork(brand=brand())
    queue = FakeQueue()
    payload = IndependentGenerationRequest(
        brand_id=BRAND_ID,
        artifact_type="COPY",
        briefing="Write a launch message",
    )
    job = submit_independent_generation(
        unit_of_work=uow,
        queue=queue,
        settings=Settings(_env_file=None),
        user=USER,
        payload=payload,
        idempotency_key="copy-1",
        request_id=uuid4(),
    )

    assert job.artifact_type == "COPY"
    assert uow.created[0]["operation"] == "CREATE"
    assert uow.created[0]["prompt"].find("Senior Advertising Copywriter") >= 0
    assert "Produce only the requested standalone copy" in uow.created[0]["prompt"]
    assert "Develop complementary copy and visual direction" not in uow.created[0]["prompt"]
    assert queue.generations == [job.id]


def test_image_transform_binds_exact_source_version_and_destination() -> None:
    source_image = ImageRecord(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        content_id=CONTENT_ID,
        generation_id=uuid4(),
        version_number=3,
        storage_path="users/principal-1/contents/source/versions/3/image.png",
        public_url="https://storage.invalid/image.png",
        mime_type="image/png",
        width=1080,
        height=1080,
        model="test-model",
        prompt="source",
        metadata={},
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )
    uow = FakeUnitOfWork(
        brand=brand(),
        source=replace(content_record(), content_type="IMAGE"),
        image=source_image,
    )
    payload = IndependentGenerationRequest(
        brand_id=BRAND_ID,
        artifact_type="IMAGE",
        operation="TRANSFORM",
        briefing="Adapt the campaign image",
        direction="Keep the same visual concept and subject scale",
        source_content_id=CONTENT_ID,
        source_image_id=source_image.id,
        destination_preset="1080x1350",
    )

    job = submit_independent_generation(
        unit_of_work=uow,
        queue=FakeQueue(),
        settings=Settings(_env_file=None),
        user=USER,
        payload=payload,
        idempotency_key="image-transform-exact-version",
        request_id=uuid4(),
    )

    params = uow.created[0]["parameters"]
    assert job.operation == "TRANSFORM"
    assert params["source_image"]["id"] == str(source_image.id)
    assert params["source_image"]["version_number"] == 3
    assert params["source_image"]["storage_path"] == source_image.storage_path
    assert params["destination_preset"] == "1080x1350"


def test_submit_rejects_brand_not_visible_to_user() -> None:
    uow = FakeUnitOfWork(brand=None)
    with pytest.raises(EntityNotFoundError):
        submit_independent_generation(
            unit_of_work=uow,
            queue=FakeQueue(),
            settings=Settings(_env_file=None),
            user=USER,
            payload=IndependentGenerationRequest(
                brand_id=BRAND_ID, artifact_type="CAPTION", briefing="Caption"
            ),
            idempotency_key="caption-1",
            request_id=uuid4(),
        )
    assert not uow.created


def test_reusing_idempotency_key_for_different_input_conflicts() -> None:
    uow = FakeUnitOfWork(brand=brand())
    queue = FakeQueue()
    first_payload = IndependentGenerationRequest(
        brand_id=BRAND_ID, artifact_type="CAPTION", briefing="Caption one"
    )
    first_job = submit_independent_generation(
        unit_of_work=uow,
        queue=queue,
        settings=Settings(_env_file=None),
        user=USER,
        payload=first_payload,
        idempotency_key="same-key",
        request_id=uuid4(),
    )
    uow.existing = first_job

    with pytest.raises(IdempotencyConflictError):
        submit_independent_generation(
            unit_of_work=uow,
            queue=queue,
            settings=Settings(_env_file=None),
            user=USER,
            payload=first_payload.model_copy(update={"briefing": "Caption two"}),
            idempotency_key="same-key",
            request_id=uuid4(),
        )


@pytest.mark.parametrize(
    ("artifact_type", "expected_contract", "source_text"),
    [
        ("COPY", "Produce only the requested standalone copy", "Earlier copy"),
        ("CAPTION", "Produce only the requested post caption", "Earlier caption"),
    ],
)
def test_transform_preserves_source_component_and_uses_its_writer_contract(
    artifact_type: str, expected_contract: str, source_text: str
) -> None:
    uow = FakeUnitOfWork(brand=brand())
    queue = FakeQueue()
    job = submit_independent_generation(
        unit_of_work=uow,
        queue=queue,
        settings=Settings(_env_file=None),
        user=USER,
        payload=IndependentGenerationRequest(
            brand_id=BRAND_ID,
            artifact_type=artifact_type,
            operation="TRANSFORM",
            briefing="Improve the current component while preserving its concept",
            source_content_id=CONTENT_ID,
        ),
        idempotency_key=f"{artifact_type.lower()}-transform",
        request_id=uuid4(),
    )

    prompt = str(uow.created[0]["prompt"])
    assert job.operation == "TRANSFORM"
    assert job.artifact_type == artifact_type
    assert expected_contract in prompt
    assert source_text in prompt
    assert "preserve_source_facts_and_concept" in prompt
    assert queue.generations == [job.id]


def test_source_content_from_another_brand_is_not_authorized() -> None:
    source = replace(content_record(), brand_id=uuid4())
    uow = FakeUnitOfWork(brand=brand(), source=source)

    with pytest.raises(EntityNotFoundError):
        submit_independent_generation(
            unit_of_work=uow,
            queue=FakeQueue(),
            settings=Settings(_env_file=None),
            user=USER,
            payload=IndependentGenerationRequest(
                brand_id=BRAND_ID,
                artifact_type="CAPTION",
                operation="REGENERATE",
                briefing="Keep the message and facts",
                source_content_id=CONTENT_ID,
            ),
            idempotency_key="wrong-brand-source",
            request_id=uuid4(),
        )

    assert not uow.created


def planning_record() -> PlanningRecord:
    return PlanningRecord(
        id=uuid4(),
        brand_id=BRAND_ID,
        campaign_id=uuid4(),
        persona_id=uuid4(),
        created_by=USER.id,
        info="Planning context",
        static_amount=None,
        carousel_amount=None,
        stories_amount=None,
        special_dates=None,
        start_period=None,
        end_period=None,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def post_structure_record(planning_id: UUID) -> PostStructureRecord:
    return PostStructureRecord(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        planning_id=planning_id,
        created_by=USER.id,
        title="Planning post",
        objective="Objetivo",
        big_idea="Ideia",
        main_message="Mensagem",
        headline="Headline",
        image_cta="CTA",
        art_guiding="Luz suave",
        status="APPROVED",
        format="feed",
        ratio="1:1",
        resolution="1024x1024",
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def image_record() -> ImageRecord:
    return ImageRecord(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        content_id=CONTENT_ID,
        generation_id=uuid4(),
        version_number=1,
        storage_path="users/principal/contents/content/versions/1/image.png",
        public_url="https://example.com/image.png",
        mime_type="image/png",
        width=1024,
        height=1024,
        model="gemini-image-original",
        prompt="Original prompt",
        metadata={"style": "photographic"},
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def test_planning_generation_persists_resolved_input_and_keeps_request_input() -> None:
    planning = planning_record()
    post_structure = post_structure_record(planning.id)
    uow = FakeUnitOfWork(
        brand=brand(),
        planning=planning,
        post_structure=post_structure,
    )
    queue = FakeQueue()
    payload = IndependentGenerationRequest(
        artifact_type="IMAGE",
        planning_id=planning.id,
        post_structure_id=post_structure.id,
    )

    job = submit_independent_generation(
        unit_of_work=uow,
        queue=queue,
        settings=Settings(_env_file=None),
        user=USER,
        payload=payload,
        idempotency_key="planning-image-1",
        request_id=uuid4(),
    )

    parameters = uow.created[0]["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["request_input"] == payload.model_dump(mode="json")
    assert "resolved_input" not in parameters["request_input"]
    assert parameters["resolved_input"] == {
        "briefing": (
            "Contexto do Planning: Planning context\n"
            "Objetivo: Objetivo\n"
            "Ideia central: Ideia\n"
            "Mensagem principal: Mensagem\n"
            "Headline: Headline\n"
            "Chamada para ação: CTA"
        ),
        "direction": "Luz suave\nFormato: feed\nProporção: 1:1\nResolução: 1024x1024",
    }
    assert queue.images == [job.id]


@pytest.mark.parametrize(
    ("requested_model", "expected_model"),
    [
        (None, DEFAULT_OPENAI_IMAGE_MODEL),
        ("", DEFAULT_OPENAI_IMAGE_MODEL),
        ("gemini-2.5-flash-image", DEFAULT_OPENAI_IMAGE_MODEL),
        ("imagen-3.0", DEFAULT_OPENAI_IMAGE_MODEL),
        ("gpt-image-2.6-flare", DEFAULT_OPENAI_IMAGE_MODEL),
        ("gpt-image-2.5-sunburst", "gpt-image-2.5-sunburst"),
        ("gpt-image-2.5-sunburst-2026-09-08", "gpt-image-2.5-sunburst-2026-09-08"),
        ("gpt-image-2", "gpt-image-2"),
        ("custom-image-model", "custom-image-model"),
        ("  custom-image-model  ", "custom-image-model"),
    ],
)
def test_normalize_image_model_canonicalizes_legacy_values(
    requested_model: str | None, expected_model: str
) -> None:
    assert (
        normalize_image_model(requested_model, default_model=DEFAULT_OPENAI_IMAGE_MODEL)
        == expected_model
    )


@pytest.mark.parametrize("original_model", ["gemini-image-original", "gpt-image-2.6-flare"])
def test_regeneration_normalizes_legacy_model_for_new_generation(original_model: str) -> None:
    image = replace(image_record(), model=original_model)
    uow = FakeUnitOfWork(brand=brand(), image=image)
    queue = FakeQueue()

    job = submit_image_regeneration(
        unit_of_work=uow,
        queue=queue,
        settings=Settings(_env_file=None),
        user=USER,
        image_id=image.id,
        style="illustration",
        idempotency_key="regenerate-1",
        request_id=uuid4(),
    )

    created = uow.created[0]
    assert created["model"] == DEFAULT_OPENAI_IMAGE_MODEL
    assert created["parameters"]["regenerated_from_model"] == original_model
    assert queue.images == [job.job.id]
