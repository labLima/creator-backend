from __future__ import annotations

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
    submit_image_regeneration,
    submit_independent_generation,
)
from creator.planning.ports import PlanningRecord
from creator.post_structure.ports import PostStructureRecord
from creator.user.ports import UserRecord

NOW = datetime(2026, 11, 5, tzinfo=UTC)
USER_ID = UUID("10000000-0000-0000-0000-000000000001")
BRAND_ID = UUID("20000000-0000-0000-0000-000000000001")
WORKSPACE_ID = UUID("30000000-0000-0000-0000-000000000001")
OTHER_WORKSPACE_ID = UUID("30000000-0000-0000-0000-000000000002")
PLANNING_ID = UUID("40000000-0000-0000-0000-000000000001")
POST_STRUCTURE_ID = UUID("50000000-0000-0000-0000-000000000001")
CONTENT_ID = UUID("60000000-0000-0000-0000-000000000001")
IMAGE_ID = UUID("70000000-0000-0000-0000-000000000001")
JOB_ID = UUID("80000000-0000-0000-0000-000000000001")

USER = UserRecord(
    id=USER_ID,
    external_id="principal-1",
    email=None,
    display_name="Test",
    global_role="membro",
    created_at=NOW,
    updated_at=NOW,
    deleted_at=None,
)


def brand_record(*, workspace_id: UUID = WORKSPACE_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=BRAND_ID,
        workspace_id=workspace_id,
        created_by_user_id=USER_ID,
        name="Example Brand",
        description="Brand description",
        brand_voice="Direct",
        metadata={},
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def planning_record() -> PlanningRecord:
    return PlanningRecord(
        id=PLANNING_ID,
        brand_id=BRAND_ID,
        campaign_id=uuid4(),
        persona_id=uuid4(),
        created_by=USER_ID,
        info="Campanha de verão",
        static_amount=1,
        carousel_amount=0,
        stories_amount=0,
        special_dates=None,
        start_period=None,
        end_period=None,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def post_structure_record(
    *, planning_id: UUID = PLANNING_ID, workspace_id: UUID = WORKSPACE_ID
) -> PostStructureRecord:
    return PostStructureRecord(
        id=POST_STRUCTURE_ID,
        workspace_id=workspace_id,
        planning_id=planning_id,
        created_by=USER_ID,
        title="Post de lançamento",
        objective="Lançar a nova linha",
        big_idea="Verão sem esforço",
        main_message="Leveza para o dia a dia",
        headline="Vista o verão",
        image_cta="Compre agora",
        art_guiding="Luz natural e fundo minimalista",
        status="APPROVED",
        format="STATIC",
        ratio="4:5",
        resolution="1080x1350",
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def content_record() -> ContentRecord:
    return ContentRecord(
        id=CONTENT_ID,
        workspace_id=WORKSPACE_ID,
        created_by_user_id=USER_ID,
        content_type="IMAGE",
        title="Post de lançamento",
        payload={},
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
        brand_id=BRAND_ID,
    )


def image_record(model: str = "gemini-2.5-flash-image") -> ImageRecord:
    return ImageRecord(
        id=IMAGE_ID,
        workspace_id=WORKSPACE_ID,
        content_id=CONTENT_ID,
        generation_id=uuid4(),
        version_number=1,
        storage_path="images/original.png",
        public_url="https://example.test/images/original.png",
        mime_type="image/png",
        width=1024,
        height=1024,
        model=model,
        prompt="Original prompt",
        metadata={"style": "photographic"},
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
    )


def generation_job_record(**kwargs: object) -> GenerationJobRecord:
    return GenerationJobRecord(
        id=JOB_ID,
        workspace_id=kwargs["workspace_id"],  # type: ignore[arg-type]
        generation_id=uuid4(),
        content_id=kwargs["content_id"],  # type: ignore[arg-type]
        status=GenerationJobStatus.PENDING,
        external_id=kwargs.get("external_id"),  # type: ignore[arg-type]
        attempt_count=0,
        max_attempts=kwargs.get("max_attempts", 1),  # type: ignore[arg-type]
        failure_code=None,
        failure_message=None,
        queued_at=NOW,
        started_at=None,
        completed_at=None,
        failed_at=None,
        created_at=NOW,
        updated_at=NOW,
        deleted_at=None,
        artifact_type=str(kwargs.get("artifact_type", "IMAGE")),
        operation=str(kwargs.get("operation", "CREATE")),
        idempotency_key=kwargs.get("idempotency_key"),  # type: ignore[arg-type]
    )


class FakeBrandRepository:
    def __init__(self, brand: SimpleNamespace | None) -> None:
        self.brand = brand
        self.calls: list[dict[str, object]] = []

    def get_for_user(
        self, *, user_id: UUID, brand_id: UUID, include_deleted: bool = False
    ) -> SimpleNamespace | None:
        self.calls.append({"user_id": user_id, "brand_id": brand_id})
        if self.brand is None or self.brand.id != brand_id:
            return None
        return self.brand


class FakeContents:
    def __init__(self) -> None:
        self.added: list[dict[str, object]] = []

    def user_has_workspace_access(self, **_: object) -> bool:
        return True

    def add(self, **kwargs: object) -> ContentRecord:
        self.added.append(kwargs)
        record = content_record()
        return ContentRecord(
            id=record.id,
            workspace_id=kwargs["workspace_id"],  # type: ignore[arg-type]
            created_by_user_id=kwargs["created_by_user_id"],  # type: ignore[arg-type]
            content_type=str(kwargs["content_type"]),
            title=kwargs["title"],  # type: ignore[arg-type]
            payload={},
            created_at=NOW,
            updated_at=NOW,
            deleted_at=None,
            brand_id=kwargs["brand_id"],  # type: ignore[arg-type]
        )

    def get_by_id_for_user(self, **_: object) -> ContentRecord | None:
        return None

    def list_text_versions(self, **_: object) -> list[object]:
        return []


class FakeImageJobs:
    def __init__(self, original_image: ImageRecord | None = None) -> None:
        self.original_image = original_image
        self.created: list[dict[str, object]] = []

    def get_job_by_external_id_for_user(self, **_: object) -> GenerationJobRecord | None:
        return None

    def get_status_by_external_id_for_user(self, **_: object) -> object | None:
        return None

    def get_image_for_user(self, **_: object) -> ImageRecord | None:
        return self.original_image

    def create_image_generation(self, **kwargs: object) -> GenerationJobRecord:
        self.created.append(kwargs)
        return generation_job_record(**kwargs)


class FakeUnitOfWork:
    def __init__(
        self,
        *,
        planning: PlanningRecord | None = None,
        post_structure: PostStructureRecord | None = None,
        brand: SimpleNamespace | None = None,
        original_image: ImageRecord | None = None,
    ) -> None:
        self._planning = planning
        self._post_structure = post_structure
        self.brand_repository = FakeBrandRepository(brand)
        self.planning = SimpleNamespace(get_for_user=self._get_planning)
        self.post_structures = SimpleNamespace(get_for_user=self._get_post_structure)
        self.brand = SimpleNamespace(brands=self.brand_repository)
        self.contents = FakeContents()
        self.user = SimpleNamespace(
            settings=SimpleNamespace(get_by_user_id=lambda *args, **kwargs: None)
        )
        self.image_jobs = FakeImageJobs(original_image)
        self.generation = SimpleNamespace(image_jobs=self.image_jobs)
        self.commits = 0
        self.rollbacks = 0

    def _get_planning(self, *, user_id: UUID, planning_id: UUID) -> PlanningRecord | None:
        if self._planning is None or self._planning.id != planning_id:
            return None
        return self._planning

    def _get_post_structure(
        self, *, user_id: UUID, post_structure_id: UUID
    ) -> PostStructureRecord | None:
        if self._post_structure is None or self._post_structure.id != post_structure_id:
            return None
        return self._post_structure

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


def planning_payload() -> IndependentGenerationRequest:
    return IndependentGenerationRequest(
        planning_id=PLANNING_ID,
        post_structure_id=POST_STRUCTURE_ID,
        artifact_type="IMAGE",
    )


def test_independent_generation_resolves_brand_and_persists_resolved_input() -> None:
    unit_of_work = FakeUnitOfWork(
        planning=planning_record(),
        post_structure=post_structure_record(),
        brand=brand_record(),
    )
    queue = FakeQueue()

    job = submit_independent_generation(
        unit_of_work=unit_of_work,
        queue=queue,
        settings=Settings(_env_file=None, openai_image_model="gpt-image-2"),
        user=USER,
        payload=planning_payload(),
        idempotency_key="planning-image-1",
        request_id=uuid4(),
    )

    assert unit_of_work.brand_repository.calls == [{"user_id": USER_ID, "brand_id": BRAND_ID}]
    assert unit_of_work.contents.added[0]["brand_id"] == BRAND_ID
    assert unit_of_work.image_jobs.created, "Generation Job was not created"
    created = unit_of_work.image_jobs.created[0]
    assert created["brand_id"] == BRAND_ID
    assert created["model"] == "gpt-image-2"
    assert created["workspace_id"] == WORKSPACE_ID
    parameters = created["parameters"]
    assert isinstance(parameters, dict)
    assert "resolved_input" in parameters, (
        "generation.parameters must persist resolved prompt inputs from the Planning"
    )
    resolved = parameters["resolved_input"]
    assert isinstance(resolved, dict)
    briefing = resolved["briefing"]
    direction = resolved["direction"]
    assert isinstance(briefing, str)
    assert isinstance(direction, str) and direction.strip()
    for expected in (
        "Campanha de verão",
        "Lançar a nova linha",
        "Verão sem esforço",
        "Leveza para o dia a dia",
        "Vista o verão",
        "Compre agora",
    ):
        assert expected in briefing
    assert "Luz natural e fundo minimalista" in direction
    assert job.workspace_id == WORKSPACE_ID
    assert queue.images == [JOB_ID]
    assert queue.generations == []
    assert unit_of_work.commits == 1


def test_independent_generation_rejects_cross_workspace_post_structure() -> None:
    unit_of_work = FakeUnitOfWork(
        planning=planning_record(),
        post_structure=post_structure_record(workspace_id=OTHER_WORKSPACE_ID),
        brand=brand_record(workspace_id=WORKSPACE_ID),
    )
    queue = FakeQueue()

    with pytest.raises(EntityNotFoundError):
        submit_independent_generation(
            unit_of_work=unit_of_work,
            queue=queue,
            settings=Settings(_env_file=None),
            user=USER,
            payload=planning_payload(),
            idempotency_key="planning-image-2",
            request_id=uuid4(),
        )

    assert unit_of_work.image_jobs.created == []
    assert queue.images == []
    assert unit_of_work.commits == 0


def test_independent_generation_rejects_post_structure_from_another_planning() -> None:
    unit_of_work = FakeUnitOfWork(
        planning=planning_record(),
        post_structure=post_structure_record(planning_id=uuid4()),
        brand=brand_record(),
    )
    queue = FakeQueue()

    with pytest.raises(EntityNotFoundError):
        submit_independent_generation(
            unit_of_work=unit_of_work,
            queue=queue,
            settings=Settings(_env_file=None),
            user=USER,
            payload=planning_payload(),
            idempotency_key="planning-image-3",
            request_id=uuid4(),
        )

    assert unit_of_work.image_jobs.created == []
    assert queue.images == []
    assert unit_of_work.commits == 0


def test_image_regeneration_normalizes_legacy_gemini_model_to_openai() -> None:
    original = image_record(model="gemini-2.5-flash-image")
    unit_of_work = FakeUnitOfWork(original_image=original)
    queue = FakeQueue()

    submit_image_regeneration(
        unit_of_work=unit_of_work,
        queue=queue,
        settings=Settings(_env_file=None, openai_image_model="gpt-image-2"),
        user=USER,
        image_id=original.id,
        style="photographic",
        idempotency_key="regeneration-1",
        request_id=uuid4(),
    )

    created = unit_of_work.image_jobs.created[0]
    assert created["model"] == "gpt-image-2"
    parameters = created["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["regenerated_from_model"] == "gemini-2.5-flash-image"
    assert queue.images == [JOB_ID]
    assert unit_of_work.commits == 1


def test_image_regeneration_preserves_non_legacy_model() -> None:
    original = image_record(model="dall-e-3")
    unit_of_work = FakeUnitOfWork(original_image=original)

    submit_image_regeneration(
        unit_of_work=unit_of_work,
        queue=FakeQueue(),
        settings=Settings(_env_file=None, openai_image_model="gpt-image-2"),
        user=USER,
        image_id=original.id,
        style="photographic",
        idempotency_key="regeneration-2",
        request_id=uuid4(),
    )

    assert unit_of_work.image_jobs.created[0]["model"] == "dall-e-3"
