"""SQLAlchemy implementation of the generation persistence ports."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.generation.models as generation_models
import creator.workspace.models as workspace_models
from creator.generation.ports import GeneratedImageRecord


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
