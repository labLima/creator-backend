"""SQLAlchemy implementation of the generation persistence ports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Integer, Select, and_, asc, desc, func, select, update
from sqlalchemy import cast as sql_cast
from sqlalchemy.orm import Session

import creator.generation.models as generation_models
import creator.workspace.models as workspace_models
from creator.content import models as content_tables
from creator.content.ports import ImageMetadata, ImageRecord
from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.domain.exceptions import EntityNotFoundError, InvalidStateTransitionError
from creator.domain.generation import GenerationJobStatus, can_transition
from creator.generation import models as generation_tables
from creator.generation.ports import (
    GeneratedImageRecord,
    GenerationHistoryFilters,
    GenerationJobRecord,
    GenerationRecord,
    ImageGenerationStatusRecord,
    ImageGenerationWorkItem,
)
from creator.infrastructure.persistence.sql import as_datetime as _datetime
from creator.infrastructure.persistence.sql import as_optional_datetime as _optional_datetime
from creator.infrastructure.persistence.sql import enum_value as _enum_value
from creator.infrastructure.persistence.sql import flush_or_raise
from creator.infrastructure.persistence.sql import json_object as _json
from creator.infrastructure.persistence.sql import now as _now
from creator.infrastructure.persistence.sql import paginate as _page
from creator.infrastructure.persistence.sql import scoped_resource_count as _scoped_resource_count
from creator.infrastructure.persistence.sql import scoped_resource_select as _scoped_resource_select
from creator.infrastructure.persistence.sql import (
    user_has_workspace_role as _user_has_workspace_role,
)
from creator.user import models as user_tables
from creator.user.ports import UserRecord
from creator.workspace import models as workspace_tables


def _generated_image_record(row: generation_models.GeneratedImage) -> GeneratedImageRecord:
    return GeneratedImageRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        design_structure_id=row.design_structure_id,
        signed_url=row.signed_url,
        size=row.size,
        resolution=row.resolution,
        image_ratio=row.image_ratio,
        status=row.image_status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def _image_record(row: content_tables.Image) -> ImageRecord:
    return ImageRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        content_id=row.content_id,
        generation_id=row.generation_id,
        version_number=row.version_number,
        storage_path=row.storage_path,
        public_url=row.public_url,
        mime_type=row.mime_type,
        width=row.width,
        height=row.height,
        model=row.model,
        prompt=row.prompt,
        metadata=_json(row.metadata_json),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


class SqlAlchemyGeneratedImageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_user(self, *, user_id: UUID, image_id: UUID) -> GeneratedImageRecord | None:
        row = self._session.scalars(
            select(generation_models.GeneratedImage)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == generation_models.GeneratedImage.workspace_id,
            )
            .where(
                generation_models.GeneratedImage.id == image_id,
                generation_models.GeneratedImage.deleted_at.is_(None),
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
            )
        ).one_or_none()
        return _generated_image_record(row) if row else None


def _generation_record(row: generation_tables.Generation) -> GenerationRecord:
    return GenerationRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        content_id=row.content_id,
        brand_id=row.brand_id,
        project_id=row.project_id,
        requested_by_user_id=row.requested_by_user_id,
        generation_type=_enum_value(row.generation_type),
        model=row.model,
        prompt=row.prompt,
        parameters=_json(row.parameters),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


class SqlAlchemyGenerationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        workspace_id: UUID,
        content_id: UUID,
        requested_by_user_id: UUID | None,
        model: str,
        prompt: str,
        generation_type: str = "TEXT",
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        parameters: JsonObject | None = None,
    ) -> GenerationRecord:
        if requested_by_user_id is not None and not _user_has_workspace_role(
            self._session,
            user_id=requested_by_user_id,
            workspace_id=workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Workspace not found")
        content = self._session.scalars(
            select(content_tables.Content).where(
                content_tables.Content.id == content_id,
                content_tables.Content.workspace_id == workspace_id,
                content_tables.Content.deleted_at.is_(None),
            )
        ).one_or_none()
        if content is None:
            raise EntityNotFoundError("Content not found")
        row = generation_tables.Generation(
            workspace_id=workspace_id,
            content_id=content_id,
            requested_by_user_id=requested_by_user_id,
            generation_type=generation_type,
            brand_id=brand_id,
            project_id=project_id,
            model=model,
            prompt=prompt,
            parameters=_json(parameters),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _generation_record(row)

    def get_for_user(
        self,
        *,
        user_id: UUID,
        generation_id: UUID,
        include_deleted: bool = False,
    ) -> GenerationRecord | None:
        statement = self._scoped_select(user_id).where(
            generation_tables.Generation.id == generation_id
        )
        if not include_deleted:
            statement = statement.where(generation_tables.Generation.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _generation_record(row) if row else None

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        content_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[GenerationRecord]:
        page = page or PageRequest()
        statement = self._scoped_select(user_id).where(
            generation_tables.Generation.deleted_at.is_(None)
        )
        count_statement = self._scoped_count(user_id).where(
            generation_tables.Generation.deleted_at.is_(None)
        )
        if workspace_id is not None:
            statement = statement.where(generation_tables.Generation.workspace_id == workspace_id)
            count_statement = count_statement.where(
                generation_tables.Generation.workspace_id == workspace_id
            )
        if content_id is not None:
            statement = statement.where(generation_tables.Generation.content_id == content_id)
            count_statement = count_statement.where(
                generation_tables.Generation.content_id == content_id
            )
        rows, total = _page(
            self._session, statement, count_statement, generation_tables.Generation.created_at, page
        )
        return Page(
            items=[_generation_record(row) for row in rows],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def update(
        self,
        *,
        user_id: UUID,
        generation_id: UUID,
        model: str | None = None,
        prompt: str | None = None,
        parameters: JsonObject | None = None,
    ) -> GenerationRecord:
        row = self._writable_generation(user_id=user_id, generation_id=generation_id)
        if model is not None:
            row.model = model
        if prompt is not None:
            row.prompt = prompt
        if parameters is not None:
            row.parameters = _json(parameters)
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _generation_record(row)

    def soft_delete(self, *, user_id: UUID, generation_id: UUID) -> None:
        row = self._writable_generation(user_id=user_id, generation_id=generation_id)
        timestamp = _now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        flush_or_raise(self._session)

    def _writable_generation(
        self, *, user_id: UUID, generation_id: UUID
    ) -> generation_tables.Generation:
        row = self._session.scalars(
            self._scoped_select(user_id).where(
                generation_tables.Generation.id == generation_id,
                generation_tables.Generation.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None or not _user_has_workspace_role(
            self._session,
            user_id=user_id,
            workspace_id=row.workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Generation not found")
        return cast(generation_tables.Generation, row)

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_select(user_id, generation_tables.Generation).join(
            content_tables.Content,
            and_(
                content_tables.Content.id == generation_tables.Generation.content_id,
                content_tables.Content.workspace_id == generation_tables.Generation.workspace_id,
                content_tables.Content.deleted_at.is_(None),
            ),
        )

    def _scoped_count(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_count(user_id, generation_tables.Generation).join(
            content_tables.Content,
            and_(
                content_tables.Content.id == generation_tables.Generation.content_id,
                content_tables.Content.workspace_id == generation_tables.Generation.workspace_id,
                content_tables.Content.deleted_at.is_(None),
            ),
        )


def _image_generation_status_record(
    job: generation_tables.GenerationJob,
    content_id: UUID,
    parameters: dict[str, object] | None,
    image: content_tables.Image | None,
) -> ImageGenerationStatusRecord:
    return ImageGenerationStatusRecord(
        job=_job_record(job, content_id),
        parameters=_json(parameters),
        image=_image_record(image) if image else None,
    )


def _job_record(row: generation_tables.GenerationJob, content_id: UUID) -> GenerationJobRecord:
    return GenerationJobRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        generation_id=row.generation_id,
        content_id=content_id,
        status=row.status,
        external_id=row.external_id,
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        failure_code=row.failure_code,
        failure_message=row.failure_message,
        queued_at=_datetime(row.queued_at),
        started_at=_optional_datetime(row.started_at),
        completed_at=_optional_datetime(row.completed_at),
        failed_at=_optional_datetime(row.failed_at),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
        request_id=row.request_id,
    )


def _user_record(row: user_tables.User) -> UserRecord:
    return UserRecord(
        id=row.id,
        external_id=row.external_id,
        email=row.email,
        display_name=row.display_name,
        global_role=_enum_value(row.global_role),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
        password_hash=row.password_hash,
    )


class SqlAlchemyImageGenerationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_image_generation(
        self,
        *,
        workspace_id: UUID,
        content_id: UUID,
        requested_by_user_id: UUID | None,
        model: str,
        prompt: str,
        parameters: JsonObject | None = None,
        external_id: str | None = None,
        max_attempts: int = 1,
        request_id: UUID | None = None,
    ) -> GenerationJobRecord:
        if requested_by_user_id is None or not _user_has_workspace_role(
            self._session,
            user_id=requested_by_user_id,
            workspace_id=workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Content not found")
        content = self._session.scalars(
            select(content_tables.Content).where(
                content_tables.Content.id == content_id,
                content_tables.Content.workspace_id == workspace_id,
                content_tables.Content.deleted_at.is_(None),
            )
        ).one_or_none()
        if content is None:
            raise EntityNotFoundError("Content not found")

        generation = generation_tables.Generation(
            workspace_id=workspace_id,
            content_id=content_id,
            requested_by_user_id=requested_by_user_id,
            model=model,
            prompt=prompt,
            parameters=_json(parameters),
        )
        self._session.add(generation)
        flush_or_raise(self._session)

        job = generation_tables.GenerationJob(
            workspace_id=workspace_id,
            generation_id=generation.id,
            external_id=external_id,
            max_attempts=max_attempts,
            request_id=request_id,
        )
        self._session.add(job)
        flush_or_raise(self._session)
        self._add_status_event(job.id, None, GenerationJobStatus.PENDING, request_id=request_id)
        flush_or_raise(self._session)
        return _job_record(job, content_id)

    def get_job_for_user(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        include_deleted: bool = False,
    ) -> GenerationJobRecord | None:
        statement = self._scoped_job_select(user_id).where(
            generation_tables.GenerationJob.id == job_id
        )
        if not include_deleted:
            statement = statement.where(generation_tables.GenerationJob.deleted_at.is_(None))
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        job, content_id = cast(tuple[generation_tables.GenerationJob, UUID], row)
        return _job_record(job, content_id)

    def list_history_for_user(
        self,
        *,
        user_id: UUID,
        filters: GenerationHistoryFilters | None = None,
        page: PageRequest | None = None,
    ) -> Page[GenerationJobRecord]:
        filters = filters or GenerationHistoryFilters()
        page = page or PageRequest()
        statement = self._apply_history_filters(self._scoped_job_select(user_id), filters)
        count_statement = self._apply_history_filters(self._scoped_job_count(user_id), filters)
        order_column = (
            asc(generation_tables.GenerationJob.created_at)
            if page.sort == "asc"
            else desc(generation_tables.GenerationJob.created_at)
        )
        rows = self._session.execute(
            statement.order_by(order_column).offset(page.offset).limit(page.limit)
        ).all()
        total: int = self._session.execute(count_statement).scalar_one()
        return Page(
            items=[
                _job_record(*cast(tuple[generation_tables.GenerationJob, UUID], row))
                for row in rows
            ],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def claim_next_pending(
        self,
        *,
        workspace_id: UUID | None = None,
    ) -> GenerationJobRecord | None:
        candidate_statement = (
            select(generation_tables.GenerationJob)
            .where(
                generation_tables.GenerationJob.status == GenerationJobStatus.PENDING,
                generation_tables.GenerationJob.deleted_at.is_(None),
            )
            .order_by(generation_tables.GenerationJob.created_at.asc())
            .limit(1)
        )
        if workspace_id is not None:
            candidate_statement = candidate_statement.where(
                generation_tables.GenerationJob.workspace_id == workspace_id
            )

        candidate = self._session.scalars(candidate_statement).first()
        if candidate is None:
            return None
        candidate_id = candidate.id

        timestamp = _now()
        # SQLite ignores FOR UPDATE/SKIP LOCKED. A conditional UPDATE gives both
        # SQLite and PostgreSQL a single-winner claim.
        result = self._session.execute(
            update(generation_tables.GenerationJob)
            .where(
                generation_tables.GenerationJob.id == candidate_id,
                generation_tables.GenerationJob.status == GenerationJobStatus.PENDING,
                generation_tables.GenerationJob.deleted_at.is_(None),
            )
            .values(
                status=GenerationJobStatus.PROCESSING,
                started_at=timestamp,
                attempt_count=generation_tables.GenerationJob.attempt_count + 1,
                updated_at=timestamp,
            )
            .execution_options(synchronize_session=False)
        )
        if getattr(result, "rowcount", 1) == 0:
            return None

        candidate.status = GenerationJobStatus.PROCESSING
        candidate.started_at = timestamp
        candidate.attempt_count = (candidate.attempt_count or 0) + 1
        candidate.updated_at = timestamp
        self._add_status_event(
            candidate.id,
            GenerationJobStatus.PENDING,
            GenerationJobStatus.PROCESSING,
        )
        flush_or_raise(self._session)
        content_id = self._content_id_for_generation(candidate.generation_id)
        return _job_record(candidate, content_id)

    def next_image_version(self, content_id: UUID) -> int:
        return self._next_image_version(content_id)

    def reserve_image_version(self, job_id: UUID) -> int:
        job = self._locked_job(job_id)
        generation = self._generation_for_job(job)
        parameters = _json(generation.parameters)
        reserved = parameters.get("image_version_number")
        if isinstance(reserved, int) and reserved > 0:
            return reserved
        self._lock_content(generation.content_id)
        version_number = self._next_image_version(generation.content_id)
        parameters["image_version_number"] = version_number
        generation.parameters = parameters
        generation.updated_at = _now()
        flush_or_raise(self._session)
        return version_number

    def get_status_for_user(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        include_deleted: bool = False,
    ) -> ImageGenerationStatusRecord | None:
        statement = self._scoped_status_select(user_id).where(
            generation_tables.GenerationJob.id == job_id
        )
        if not include_deleted:
            statement = statement.where(generation_tables.GenerationJob.deleted_at.is_(None))
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        job, content_id, parameters, image = cast(
            tuple[
                generation_tables.GenerationJob,
                UUID,
                dict[str, object] | None,
                content_tables.Image | None,
            ],
            row,
        )
        return _image_generation_status_record(job, content_id, parameters, image)

    def get_status_by_external_id_for_user(
        self,
        *,
        user_id: UUID,
        external_id: str,
        include_deleted: bool = False,
    ) -> ImageGenerationStatusRecord | None:
        statement = self._scoped_status_select(user_id).where(
            generation_tables.GenerationJob.external_id == external_id
        )
        if not include_deleted:
            statement = statement.where(generation_tables.GenerationJob.deleted_at.is_(None))
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        job, content_id, parameters, image = cast(
            tuple[
                generation_tables.GenerationJob,
                UUID,
                dict[str, object] | None,
                content_tables.Image | None,
            ],
            row,
        )
        return _image_generation_status_record(job, content_id, parameters, image)

    def claim_pending_by_id(self, job_id: UUID) -> ImageGenerationWorkItem | None:
        statement = (
            select(generation_tables.GenerationJob, generation_tables.Generation, user_tables.User)
            .join(
                generation_tables.Generation,
                and_(
                    generation_tables.Generation.id
                    == generation_tables.GenerationJob.generation_id,
                    generation_tables.Generation.workspace_id
                    == generation_tables.GenerationJob.workspace_id,
                    generation_tables.Generation.deleted_at.is_(None),
                ),
            )
            .join(
                user_tables.User,
                and_(
                    user_tables.User.id == generation_tables.Generation.requested_by_user_id,
                    user_tables.User.deleted_at.is_(None),
                ),
            )
            .where(
                generation_tables.GenerationJob.id == job_id,
                generation_tables.GenerationJob.status.in_(
                    [GenerationJobStatus.PENDING, GenerationJobStatus.PROCESSING]
                ),
                generation_tables.GenerationJob.deleted_at.is_(None),
            )
            .with_for_update(of=generation_tables.GenerationJob)
        )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        job, generation, user = row
        if job.status == GenerationJobStatus.PENDING:
            self._transition_job(job, GenerationJobStatus.PROCESSING)
        timestamp = _now()
        job.started_at = timestamp
        job.attempt_count += 1
        job.updated_at = timestamp
        flush_or_raise(self._session)
        return ImageGenerationWorkItem(
            job=_job_record(job, generation.content_id),
            model=generation.model,
            prompt=generation.prompt,
            parameters=_json(generation.parameters),
            requested_by_user=_user_record(user),
        )

    def get_image_by_generation_id(self, generation_id: UUID) -> ImageRecord | None:
        image = self._session.scalars(
            select(content_tables.Image).where(
                content_tables.Image.generation_id == generation_id,
                content_tables.Image.deleted_at.is_(None),
            )
        ).one_or_none()
        return _image_record(image) if image else None

    def fail_stale_processing(
        self,
        *,
        older_than: datetime,
        failure_code: str,
        failure_message: str,
    ) -> int:
        jobs = self._session.scalars(
            select(generation_tables.GenerationJob)
            .where(
                generation_tables.GenerationJob.status == GenerationJobStatus.PROCESSING,
                generation_tables.GenerationJob.started_at < older_than,
                generation_tables.GenerationJob.deleted_at.is_(None),
            )
            .with_for_update(skip_locked=True)
        ).all()
        timestamp = _now()
        for job in jobs:
            self._transition_job(job, GenerationJobStatus.FAILED)
            job.failure_code = failure_code
            job.failure_message = failure_message
            job.failed_at = timestamp
            job.updated_at = timestamp
        flush_or_raise(self._session)
        return len(jobs)

    def get_image_for_user(
        self,
        *,
        user_id: UUID,
        image_id: UUID,
        include_deleted: bool = False,
    ) -> ImageRecord | None:
        statement = (
            select(content_tables.Image)
            .join(
                content_tables.Content,
                and_(
                    content_tables.Content.id == content_tables.Image.content_id,
                    content_tables.Content.workspace_id == content_tables.Image.workspace_id,
                    content_tables.Content.deleted_at.is_(None),
                ),
            )
            .join(
                workspace_tables.WorkspaceMembership,
                and_(
                    workspace_tables.WorkspaceMembership.workspace_id
                    == content_tables.Image.workspace_id,
                    workspace_tables.WorkspaceMembership.user_id == user_id,
                    workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                ),
            )
            .where(content_tables.Image.id == image_id)
        )
        if not include_deleted:
            statement = statement.where(content_tables.Image.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _image_record(row) if row else None

    def complete_job(self, job_id: UUID, image: ImageMetadata) -> ImageRecord:
        job = self._locked_job(job_id)
        generation = self._generation_for_job(job)
        self._lock_content(generation.content_id)
        self._transition_job(job, GenerationJobStatus.COMPLETED)
        version_number = (
            image.version_number
            if image.version_number is not None
            else self._next_image_version(generation.content_id)
        )
        timestamp = _now()
        job.completed_at = timestamp
        job.updated_at = timestamp
        image_row = content_tables.Image(
            workspace_id=job.workspace_id,
            content_id=generation.content_id,
            generation_id=job.generation_id,
            version_number=version_number,
            storage_path=image.storage_path,
            public_url=image.public_url,
            mime_type=image.mime_type,
            width=image.width,
            height=image.height,
            model=image.model,
            prompt=image.prompt,
            metadata_json=_json(image.metadata),
        )
        self._session.add(image_row)
        flush_or_raise(self._session)
        return _image_record(image_row)

    def fail_job(
        self,
        job_id: UUID,
        *,
        failure_code: str,
        failure_message: str,
    ) -> GenerationJobRecord:
        job = self._locked_job(job_id)
        self._transition_job(job, GenerationJobStatus.FAILED)
        timestamp = _now()
        job.failure_code = failure_code
        job.failure_message = failure_message
        job.failed_at = timestamp
        job.updated_at = timestamp
        flush_or_raise(self._session)
        content_id = self._content_id_for_generation(job.generation_id)
        return _job_record(job, content_id)

    def _scoped_job_select(self, user_id: UUID) -> Select[Any]:
        return cast(
            Select[Any],
            (
                select(generation_tables.GenerationJob, generation_tables.Generation.content_id)
                .join(
                    generation_tables.Generation,
                    and_(
                        generation_tables.Generation.id
                        == generation_tables.GenerationJob.generation_id,
                        generation_tables.Generation.workspace_id
                        == generation_tables.GenerationJob.workspace_id,
                        generation_tables.Generation.deleted_at.is_(None),
                    ),
                )
                .join(
                    content_tables.Content,
                    and_(
                        content_tables.Content.id == generation_tables.Generation.content_id,
                        content_tables.Content.workspace_id
                        == generation_tables.Generation.workspace_id,
                        content_tables.Content.deleted_at.is_(None),
                    ),
                )
                .join(
                    workspace_tables.WorkspaceMembership,
                    and_(
                        workspace_tables.WorkspaceMembership.workspace_id
                        == generation_tables.GenerationJob.workspace_id,
                        workspace_tables.WorkspaceMembership.user_id == user_id,
                        workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                    ),
                )
            ),
        )

    def _scoped_job_count(self, user_id: UUID) -> Select[Any]:
        return (
            select(func.count())
            .select_from(generation_tables.GenerationJob)
            .join(
                generation_tables.Generation,
                and_(
                    generation_tables.Generation.id
                    == generation_tables.GenerationJob.generation_id,
                    generation_tables.Generation.workspace_id
                    == generation_tables.GenerationJob.workspace_id,
                    generation_tables.Generation.deleted_at.is_(None),
                ),
            )
            .join(
                content_tables.Content,
                and_(
                    content_tables.Content.id == generation_tables.Generation.content_id,
                    content_tables.Content.workspace_id
                    == generation_tables.Generation.workspace_id,
                    content_tables.Content.deleted_at.is_(None),
                ),
            )
            .join(
                workspace_tables.WorkspaceMembership,
                and_(
                    workspace_tables.WorkspaceMembership.workspace_id
                    == generation_tables.GenerationJob.workspace_id,
                    workspace_tables.WorkspaceMembership.user_id == user_id,
                    workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                ),
            )
        )

    def _scoped_status_select(self, user_id: UUID) -> Select[Any]:
        return cast(
            Select[Any],
            (
                select(
                    generation_tables.GenerationJob,
                    generation_tables.Generation.content_id,
                    generation_tables.Generation.parameters,
                    content_tables.Image,
                )
                .join(
                    generation_tables.Generation,
                    and_(
                        generation_tables.Generation.id
                        == generation_tables.GenerationJob.generation_id,
                        generation_tables.Generation.workspace_id
                        == generation_tables.GenerationJob.workspace_id,
                        generation_tables.Generation.deleted_at.is_(None),
                    ),
                )
                .join(
                    content_tables.Content,
                    and_(
                        content_tables.Content.id == generation_tables.Generation.content_id,
                        content_tables.Content.workspace_id
                        == generation_tables.Generation.workspace_id,
                        content_tables.Content.deleted_at.is_(None),
                    ),
                )
                .join(
                    workspace_tables.WorkspaceMembership,
                    and_(
                        workspace_tables.WorkspaceMembership.workspace_id
                        == generation_tables.GenerationJob.workspace_id,
                        workspace_tables.WorkspaceMembership.user_id == user_id,
                        workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                    ),
                )
                .outerjoin(
                    content_tables.Image,
                    and_(
                        content_tables.Image.generation_id
                        == generation_tables.GenerationJob.generation_id,
                        content_tables.Image.workspace_id
                        == generation_tables.GenerationJob.workspace_id,
                        content_tables.Image.content_id == generation_tables.Generation.content_id,
                        content_tables.Image.deleted_at.is_(None),
                    ),
                )
            ),
        )

    def _apply_history_filters(
        self,
        statement: Select[Any],
        filters: GenerationHistoryFilters,
    ) -> Select[Any]:
        if not filters.include_deleted:
            statement = statement.where(generation_tables.GenerationJob.deleted_at.is_(None))
        if filters.workspace_id is not None:
            statement = statement.where(
                generation_tables.GenerationJob.workspace_id == filters.workspace_id
            )
        if filters.content_id is not None:
            statement = statement.where(
                generation_tables.Generation.content_id == filters.content_id
            )
        if filters.status is not None:
            statement = statement.where(generation_tables.GenerationJob.status == filters.status)
        if filters.created_from is not None:
            statement = statement.where(
                generation_tables.GenerationJob.created_at >= filters.created_from
            )
        if filters.created_to is not None:
            statement = statement.where(
                generation_tables.GenerationJob.created_at <= filters.created_to
            )
        return statement

    def _locked_job(self, job_id: UUID) -> generation_tables.GenerationJob:
        job = self._session.scalars(
            select(generation_tables.GenerationJob)
            .where(
                generation_tables.GenerationJob.id == job_id,
                generation_tables.GenerationJob.deleted_at.is_(None),
            )
            .with_for_update()
        ).one_or_none()
        if job is None:
            raise EntityNotFoundError("Generation Job not found")
        return job

    def _generation_for_job(
        self, job: generation_tables.GenerationJob
    ) -> generation_tables.Generation:
        generation = self._session.scalars(
            select(generation_tables.Generation).where(
                generation_tables.Generation.id == job.generation_id,
                generation_tables.Generation.workspace_id == job.workspace_id,
                generation_tables.Generation.deleted_at.is_(None),
            )
        ).one_or_none()
        if generation is None:
            raise EntityNotFoundError("Generation not found")
        return generation

    def _lock_content(self, content_id: UUID) -> None:
        content = self._session.scalars(
            select(content_tables.Content)
            .where(
                content_tables.Content.id == content_id, content_tables.Content.deleted_at.is_(None)
            )
            .with_for_update()
        ).one_or_none()
        if content is None:
            raise EntityNotFoundError("Content not found")

    def _transition_job(
        self, job: generation_tables.GenerationJob, target: GenerationJobStatus
    ) -> None:
        current = job.status
        if not can_transition(current, target):
            raise InvalidStateTransitionError(f"Cannot transition {current} to {target}")
        job.status = target
        self._add_status_event(job.id, current, target, request_id=job.request_id)

    def _add_status_event(
        self,
        job_id: UUID,
        previous_status: GenerationJobStatus | None,
        status: GenerationJobStatus,
        *,
        request_id: UUID | None = None,
    ) -> None:
        self._session.add(
            generation_tables.GenerationJobStatusEvent(
                generation_job_id=job_id,
                previous_status=previous_status,
                status=status,
                request_id=request_id,
            )
        )

    def _content_id_for_generation(self, generation_id: UUID) -> UUID:
        content_id = self._session.execute(
            select(generation_tables.Generation.content_id).where(
                generation_tables.Generation.id == generation_id
            )
        ).scalar_one_or_none()
        if content_id is None:
            raise EntityNotFoundError("Generation not found")
        return content_id

    def _next_image_version(self, content_id: UUID) -> int:
        completed_version = self._session.execute(
            select(func.coalesce(func.max(content_tables.Image.version_number), 0) + 1).where(
                content_tables.Image.content_id == content_id
            )
        ).scalar_one()
        reserved_version = self._session.execute(
            select(
                func.coalesce(
                    func.max(
                        sql_cast(
                            generation_tables.Generation.parameters[
                                "image_version_number"
                            ].as_integer(),
                            Integer,
                        )
                    ),
                    0,
                )
                + 1
            ).where(
                generation_tables.Generation.content_id == content_id,
                generation_tables.Generation.deleted_at.is_(None),
                func.json_type(generation_tables.Generation.parameters["image_version_number"])
                == "number",
            )
        ).scalar_one()
        return max(int(completed_version), int(reserved_version))
