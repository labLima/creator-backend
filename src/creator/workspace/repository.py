"""SQLAlchemy implementation of the workspace persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.workspace.models as workspace_models
from creator.workspace.ports import (
    WorkspaceInviteRecord,
    WorkspaceInviteRepository,
    WorkspaceInviteUsageRecord,
    WorkspaceInviteUsageRepository,
)


def _record(row: workspace_models.WorkspaceInvite) -> WorkspaceInviteRecord:
    return WorkspaceInviteRecord(
        row.id,
        row.workspace_id,
        row.type,
        row.role,
        row.email,
        row.max_uses,
        row.uses_count,
        row.status,
        row.is_active,
        row.created_by,
        row.expires_at,
        row.last_used_at,
        row.revoked_at,
        row.created_at,
        row.updated_at,
        row.deleted_at,
    )


class SqlAlchemyWorkspaceInviteRepository(WorkspaceInviteRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _owned(self, user_id: UUID, invite_id: UUID) -> workspace_models.WorkspaceInvite | None:
        return self._session.scalar(
            select(workspace_models.WorkspaceInvite)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == workspace_models.WorkspaceInvite.workspace_id,
            )
            .where(
                workspace_models.WorkspaceInvite.id == invite_id,
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceInvite.deleted_at.is_(None),
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
            )
        )

    def list_for_user(
        self, *, user_id: UUID, workspace_id: UUID | None = None
    ) -> list[WorkspaceInviteRecord]:
        query = (
            select(workspace_models.WorkspaceInvite)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == workspace_models.WorkspaceInvite.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                workspace_models.WorkspaceInvite.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            query = query.where(workspace_models.WorkspaceInvite.workspace_id == workspace_id)
        return [_record(x) for x in self._session.scalars(query).all()]

    def get_for_user(self, *, user_id: UUID, invite_id: UUID) -> WorkspaceInviteRecord | None:
        row = self._owned(user_id, invite_id)
        return _record(row) if row else None

    def add(
        self,
        *,
        workspace_id: UUID,
        created_by: UUID,
        type: str,
        role: str,
        email: str | None,
        max_uses: int | None,
        expires_at: datetime | None,
        token: str,
    ) -> WorkspaceInviteRecord:
        row = workspace_models.WorkspaceInvite(
            workspace_id=workspace_id,
            created_by=created_by,
            type=type,
            role=role,
            email=email,
            max_uses=max_uses,
            expires_at=expires_at,
            token=token,
            status="pending",
        )
        self._session.add(row)
        self._session.flush()
        return _record(row)

    def update(self, *, invite_id: UUID, fields: dict[str, object]) -> WorkspaceInviteRecord:
        row = self._session.get(workspace_models.WorkspaceInvite, invite_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Workspace invite not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _record(row)

    def soft_delete(self, *, invite_id: UUID) -> None:
        row = self._session.get(workspace_models.WorkspaceInvite, invite_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Workspace invite not found")
        row.deleted_at = datetime.now(UTC)
        row.updated_at = row.deleted_at
        self._session.flush()


class SqlAlchemyWorkspaceInviteUsageRepository(WorkspaceInviteUsageRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return WorkspaceInviteUsageRecord(
            x.id,
            x.invite_id,
            x.user_id,
            x.workspace_id,
            x.member_id,
            x.used_at,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, usage_id):
        return self.s.scalar(
            select(workspace_models.WorkspaceInviteUsage)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == workspace_models.WorkspaceInviteUsage.workspace_id,
            )
            .where(
                workspace_models.WorkspaceInviteUsage.id == usage_id,
                workspace_models.WorkspaceMembership.user_id == uid,
                workspace_models.WorkspaceInviteUsage.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id, workspace_id=None):
        q = (
            select(workspace_models.WorkspaceInviteUsage)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == workspace_models.WorkspaceInviteUsage.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceInviteUsage.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            q = q.where(workspace_models.WorkspaceInviteUsage.workspace_id == workspace_id)
        return [self._r(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id, usage_id):
        x = self._owned(user_id, usage_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = workspace_models.WorkspaceInviteUsage(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, usage_id, fields):
        x = self.s.get(workspace_models.WorkspaceInviteUsage, usage_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Workspace invite usage not found")
        for key, value in fields.items():
            setattr(x, key, value)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, usage_id):
        x = self.s.get(workspace_models.WorkspaceInviteUsage, usage_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Workspace invite usage not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
