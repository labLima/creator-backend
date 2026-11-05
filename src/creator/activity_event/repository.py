from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from creator.activity_event.models import ActivityEvent
from creator.activity_event.ports import ActivityEventRecord
from creator.brand.models import Brand
from creator.domain.exceptions import EntityNotFoundError
from creator.infrastructure.persistence.sql import flush_or_raise, user_has_workspace_role


class SqlAlchemyActivityEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_brand_event(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        brand_id: UUID,
        event_type: str,
        metadata: dict[str, object],
    ) -> None:
        if event_type not in {"brand.created", "brand.updated", "brand.deleted"} or metadata:
            raise ValueError("Invalid Activity Event or metadata")
        if not user_has_workspace_role(
            self._session, user_id=user_id, workspace_id=workspace_id, minimum_role="editor"
        ):
            raise EntityNotFoundError("Workspace not found")
        brand = self._session.scalar(
            select(Brand).where(Brand.id == brand_id, Brand.workspace_id == workspace_id)
        )
        if brand is None:
            raise EntityNotFoundError("Brand not found")
        self._session.add(
            ActivityEvent(
                workspace_id=workspace_id,
                user_id=user_id,
                brand_id=brand_id,
                entity_type="brand",
                entity_id=brand_id,
                event_type=event_type,
                metadata_json={},
                created_at=datetime.now(UTC),
            )
        )
        flush_or_raise(self._session)

    def list_events(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID | None,
        brand_id: UUID | None,
        entity_type: str | None,
        entity_id: UUID | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[ActivityEventRecord]:
        q = select(ActivityEvent).where(ActivityEvent.workspace_id == workspace_id)
        for column, value in (
            (ActivityEvent.user_id, user_id),
            (ActivityEvent.brand_id, brand_id),
            (ActivityEvent.entity_type, entity_type),
            (ActivityEvent.entity_id, entity_id),
        ):
            if value is not None:
                q = q.where(column == value)
        if before is not None:
            timestamp, event_id = before
            q = q.where(
                or_(
                    ActivityEvent.created_at < timestamp,
                    and_(ActivityEvent.created_at == timestamp, ActivityEvent.id < event_id),
                )
            )
        rows = self._session.scalars(
            q.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc()).limit(limit)
        ).all()
        return [
            ActivityEventRecord(
                id=r.id,
                workspace_id=r.workspace_id,
                user_id=r.user_id,
                brand_id=r.brand_id,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                event_type=r.event_type,
                metadata=r.metadata_json,
                created_at=r.created_at,
            )
            for r in rows
        ]
