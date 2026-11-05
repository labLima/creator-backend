from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ActivityEventRecord:
    id: UUID
    workspace_id: UUID
    user_id: UUID | None
    brand_id: UUID | None
    entity_type: str
    entity_id: UUID | None
    event_type: str
    metadata: dict[str, object]
    created_at: datetime


class ActivityEventRepository(Protocol):
    def add_brand_event(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        brand_id: UUID,
        event_type: str,
        metadata: dict[str, object],
    ) -> None: ...

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
    ) -> list[ActivityEventRecord]: ...
