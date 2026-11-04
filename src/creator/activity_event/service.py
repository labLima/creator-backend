import base64
import binascii
import json
from datetime import UTC, datetime
from uuid import UUID

from creator.application.errors import ApplicationError
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        data = json.loads(
            base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        )
        timestamp = datetime.fromisoformat(data[0])
        if len(data) != 2 or timestamp.tzinfo is None:
            raise ValueError
        return timestamp.astimezone(UTC), UUID(data[1])
    except (
        ValueError,
        TypeError,
        IndexError,
        KeyError,
        binascii.Error,
        UnicodeDecodeError,
    ) as error:
        raise ApplicationError(
            422, {"code": "INVALID_CURSOR", "message": "Invalid activity cursor"}
        ) from error


def list_events(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    workspace_id: UUID,
    limit: int,
    cursor: str | None,
    user_id: UUID | None,
    brand_id: UUID | None,
    entity_type: str | None,
    entity_id: UUID | None,
) -> dict[str, object]:
    if not uow.workspace.workspaces.user_has_workspace_role(
        user_id=actor.id, workspace_id=workspace_id, minimum_role="admin"
    ):
        raise ApplicationError(
            403,
            {
                "code": "WORKSPACE_ACCESS_DENIED",
                "message": "Workspace administrator access required",
            },
        )
    if (entity_type is None) != (entity_id is None):
        raise ApplicationError(
            422,
            {
                "code": "INVALID_ENTITY_FILTER",
                "message": "entity_type and entity_id must be supplied together",
            },
        )
    before = _decode_cursor(cursor) if cursor is not None else None
    rows = uow.activity_events.list_events(
        workspace_id=workspace_id,
        user_id=user_id,
        brand_id=brand_id,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        limit=limit + 1,
    )
    more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = None
    if more:
        last = rows[-1]
        next_cursor = (
            base64.urlsafe_b64encode(
                json.dumps(
                    [last.created_at.isoformat(), str(last.id)], separators=(",", ":")
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
    return {
        "items": [
            {
                "id": str(r.id),
                "workspace_id": str(r.workspace_id),
                "user_id": str(r.user_id) if r.user_id else None,
                "brand_id": str(r.brand_id) if r.brand_id else None,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "event_type": r.event_type,
                "metadata": r.metadata,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "next_cursor": next_cursor,
    }
