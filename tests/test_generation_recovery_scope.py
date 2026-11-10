from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import creator.brand.models  # noqa: F401
import creator.project.models  # noqa: F401
from creator.domain.generation import GenerationJobStatus
from creator.generation.models import Generation, GenerationJob, GenerationJobStatusEvent
from creator.generation.repository import SqlAlchemyImageGenerationRepository
from creator.infrastructure.database.enums import GenerationType
from creator.user.models import User


def test_image_recovery_leaves_text_jobs_untouched() -> None:
    engine = create_engine("sqlite:///:memory:")
    GenerationJob.__table__.create(engine)
    GenerationJobStatusEvent.__table__.create(engine)
    now = datetime.now(UTC)
    with Session(engine) as session:
        jobs = [
            GenerationJob(
                id=uuid4(),
                workspace_id=uuid4(),
                generation_id=uuid4(),
                artifact_type=artifact_type,
                status=GenerationJobStatus.PROCESSING,
                started_at=now - timedelta(hours=2),
            )
            for artifact_type in (GenerationType.IMAGE, GenerationType.COPY, GenerationType.CAPTION)
        ]
        session.add_all(jobs)
        session.flush()
        count = SqlAlchemyImageGenerationRepository(session).fail_stale_processing(
            older_than=now - timedelta(hours=1),
            failure_code="STALE",
            failure_message="Expired",
        )
        assert count == 1
        assert [job.status for job in jobs] == [
            GenerationJobStatus.FAILED,
            GenerationJobStatus.PROCESSING,
            GenerationJobStatus.PROCESSING,
        ]
        assert len(session.scalars(select(GenerationJobStatusEvent)).all()) == 1
    engine.dispose()


def test_image_claim_does_not_claim_copy_or_caption_jobs() -> None:
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    Generation.__table__.create(engine)
    GenerationJob.__table__.create(engine)
    GenerationJobStatusEvent.__table__.create(engine)
    now = datetime.now(UTC)
    workspace_id = uuid4()
    user_id = uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, auth_provider_id="test-user", display_name="Test"))
        jobs = []
        for index, artifact_type in enumerate(
            (GenerationType.COPY, GenerationType.CAPTION, GenerationType.IMAGE)
        ):
            generation_id = uuid4()
            session.add(
                Generation(
                    id=generation_id,
                    workspace_id=workspace_id,
                    content_id=uuid4(),
                    requested_by_user_id=user_id,
                    generation_type=artifact_type,
                    model="test",
                    prompt="briefing",
                )
            )
            job = GenerationJob(
                id=uuid4(),
                workspace_id=workspace_id,
                generation_id=generation_id,
                artifact_type=artifact_type,
                status=GenerationJobStatus.PENDING,
                created_at=now + timedelta(seconds=index),
            )
            jobs.append(job)
            session.add(job)
        session.flush()
        repository = SqlAlchemyImageGenerationRepository(session)
        assert repository.claim_pending_by_id(jobs[0].id) is None
        claimed = repository.claim_next_pending()
        assert claimed is not None and claimed.id == jobs[2].id
        assert jobs[0].status == GenerationJobStatus.PENDING
        assert jobs[1].status == GenerationJobStatus.PENDING
    engine.dispose()
