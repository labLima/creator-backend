from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from creator.config import Settings
from creator.content.ports import ContentRecord
from creator.domain.exceptions import EntityNotFoundError
from creator.domain.generation import GenerationJobStatus
from creator.generation.ports import GenerationJobRecord
from creator.generation.schemas import IndependentGenerationRequest
from creator.generation.service import (
    IdempotencyConflictError,
    submit_independent_generation,
)
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
    def __init__(self, *, brand: object | None = None, existing=None, source=None) -> None:
        self.brand_record = brand
        self.existing = existing
        self.source = source if source is not None else content_record()
        self.created: list[dict[str, object]] = []
        self.commits = 0
        self.rollbacks = 0
        self.brand = SimpleNamespace(brands=SimpleNamespace(get_for_user=self.get_brand))
        self.contents = SimpleNamespace(
            user_has_workspace_access=lambda **_: True,
            get_by_id_for_user=lambda **_: self.source,
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
            create_image_generation=self.create_job,
        )
        self.generation = SimpleNamespace(image_jobs=image_jobs)
        self.fingerprint: str | None = None

    def get_brand(self, **_: object) -> object | None:
        return self.brand_record

    def create_job(self, **kwargs: object) -> GenerationJobRecord:
        self.created.append(kwargs)
        self.fingerprint = kwargs["parameters"]["idempotency_fingerprint"]
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
            artifact_type=kwargs["artifact_type"],
            operation=kwargs["operation"],
            idempotency_key=kwargs["idempotency_key"],
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
    assert queue.images == []
    assert uow.commits == 1


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
