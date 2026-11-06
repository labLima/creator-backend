from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.domain.generation import GenerationJobStatus
from creator.generation.ports import GenerationJobRecord, ImageGenerationWorkItem
from creator.services.agents.contracts import AgentExecutionResult, WriterCopyOutput
from creator.user.ports import UserRecord
from creator.workers import generation

NOW = datetime(2026, 11, 5, tzinfo=UTC)
USER = UserRecord(
    id=uuid4(),
    external_id="principal-copy",
    email=None,
    display_name="Writer",
    global_role="membro",
    created_at=NOW,
    updated_at=NOW,
    deleted_at=None,
)
WORKSPACE_ID = uuid4()
BRAND_ID = uuid4()
JOB_ID = uuid4()


class FakeWorkRepository:
    def __init__(self) -> None:
        self.claims: list[tuple[UUID, str]] = []
        self.completed: list[UUID] = []

    def claim_pending_by_id(
        self, job_id: UUID, *, artifact_type: str
    ) -> ImageGenerationWorkItem | None:
        self.claims.append((job_id, artifact_type))
        if artifact_type != "COPY":
            return None
        return ImageGenerationWorkItem(
            job=GenerationJobRecord(
                id=JOB_ID,
                workspace_id=WORKSPACE_ID,
                generation_id=uuid4(),
                content_id=uuid4(),
                status=GenerationJobStatus.PROCESSING,
                external_id=None,
                attempt_count=1,
                max_attempts=3,
                failure_code=None,
                failure_message=None,
                queued_at=NOW,
                started_at=NOW,
                completed_at=None,
                failed_at=None,
                created_at=NOW,
                updated_at=NOW,
                deleted_at=None,
                artifact_type="COPY",
                operation="CREATE",
            ),
            model="text-model",
            prompt="Writer prompt",
            parameters={
                "request_input": {
                    "brand_id": str(BRAND_ID),
                    "operation": "CREATE",
                    "briefing": "Launch copy",
                }
            },
            requested_by_user=USER,
        )

    def complete_text_job(self, job_id: UUID) -> None:
        self.completed.append(job_id)


class FakeUnitOfWork:
    def __init__(self, repository: FakeWorkRepository) -> None:
        self.generation = SimpleNamespace(image_jobs=repository)
        self.brand = SimpleNamespace(
            brands=SimpleNamespace(
                get_for_user=lambda **_: SimpleNamespace(
                    id=BRAND_ID,
                    workspace_id=WORKSPACE_ID,
                    name="Test Brand",
                    description="Brand context",
                    brand_voice="Clear",
                )
            )
        )
        self.contents = SimpleNamespace(append_text_version=self.append_text_version)
        self.appended: list[dict[str, object]] = []
        self.commits = 0

    def __enter__(self) -> FakeUnitOfWork:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def append_text_version(self, **kwargs: object) -> None:
        self.appended.append(kwargs)


class FakeOrchestrator:
    def execute(self, context) -> AgentExecutionResult:
        assert context.role == AgentWorkflowStepRole.WRITER
        assert context.output_contract == "COPY"
        assert context.inputs["brand_context"]["name"] == "Test Brand"
        output = WriterCopyOutput(copy_text="Clear launch copy")
        return AgentExecutionResult(
            output=output,
            prompt="Writer prompt",
            prompt_template_id="agent.writer.copy.v1",
            prompt_template_version="3.0",
            input_hash="a" * 64,
            output_hash="b" * 64,
            schema_name="WriterCopyOutput",
            schema_version="1.0",
            provider="fake",
            model="text-model",
        )


def test_copy_worker_persists_immutable_component_with_audit_metadata(monkeypatch) -> None:
    repository = FakeWorkRepository()
    uows: list[FakeUnitOfWork] = []

    def make_uow() -> FakeUnitOfWork:
        uow = FakeUnitOfWork(repository)
        uows.append(uow)
        return uow

    monkeypatch.setattr(generation, "SqlAlchemyUnitOfWork", make_uow)
    monkeypatch.setattr(generation, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(generation, "create_specialist_executor", lambda _: FakeOrchestrator())
    monkeypatch.setattr(generation, "correlation_context", lambda **_: nullcontext())

    generation.run_generation_job(str(JOB_ID), str(uuid4()))

    assert repository.claims == [(JOB_ID, "COPY")]
    assert repository.completed == [JOB_ID]
    assert uows[0].commits == 1
    assert uows[-1].appended[0]["text"] == "Clear launch copy"
    assert uows[-1].appended[0]["artifact_type"] == "COPY"
    assert uows[-1].appended[0]["metadata"]["provider"] == "fake"
    assert uows[-1].commits == 1
