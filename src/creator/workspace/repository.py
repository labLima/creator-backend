"""SQLAlchemy implementation of the workspace persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, select, update
from sqlalchemy.orm import Session

import creator.workspace.models as workspace_models
from creator.core.pagination import Page, PageRequest
from creator.domain.exceptions import EntityNotFoundError
from creator.infrastructure.database.enums import WorkspaceRole
from creator.infrastructure.persistence.sql import (
    as_datetime,
    as_optional_datetime,
    enum_value,
    flush_or_raise,
    now,
    paginate,
    user_has_workspace_role,
)
from creator.workspace.ports import (
    CreatedWorkspaceRecord,
    WorkspaceInviteRecord,
    WorkspaceInviteRepository,
    WorkspaceInviteUsageRecord,
    WorkspaceInviteUsageRepository,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
)


def _workspace_membership_record(
    row: workspace_models.WorkspaceMembership,
) -> WorkspaceMembershipRecord:
    return WorkspaceMembershipRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        user_id=row.user_id,
        role=enum_value(row.role),
        created_at=as_datetime(row.created_at),
        updated_at=as_datetime(row.updated_at),
        deleted_at=as_optional_datetime(row.deleted_at),
    )


def _workspace_record(row: workspace_models.Workspace) -> WorkspaceRecord:
    return WorkspaceRecord(
        id=row.id,
        name=row.name,
        created_at=as_datetime(row.created_at),
        updated_at=as_datetime(row.updated_at),
        deleted_at=as_optional_datetime(row.deleted_at),
    )


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, name: str, owner_user_id: UUID) -> WorkspaceRecord:
        created = self.create_for_user(user_id=owner_user_id, name=name)
        return created.workspace

    def create_for_user(
        self,
        *,
        user_id: UUID,
        name: str,
        role: str = "owner",
    ) -> CreatedWorkspaceRecord:
        workspace = workspace_models.Workspace(name=name)
        self._session.add(workspace)
        flush_or_raise(self._session)

        membership = workspace_models.WorkspaceMembership(
            workspace_id=workspace.id,
            user_id=user_id,
            role=role,
        )
        self._session.add(membership)
        flush_or_raise(self._session)

        return CreatedWorkspaceRecord(
            workspace=_workspace_record(workspace),
            membership=_workspace_membership_record(membership),
        )

    def get_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        include_deleted: bool = False,
    ) -> WorkspaceRecord | None:
        statement = self._scoped_select(user_id).where(
            workspace_models.Workspace.id == workspace_id
        )
        if not include_deleted:
            statement = statement.where(workspace_models.Workspace.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _workspace_record(row) if row else None

    def list_for_user(
        self,
        *,
        user_id: UUID,
        page: PageRequest | None = None,
    ) -> Page[WorkspaceRecord]:
        page = page or PageRequest()
        statement = self._scoped_select(user_id).where(
            workspace_models.Workspace.deleted_at.is_(None)
        )
        count_statement = (
            select(func.count())
            .select_from(workspace_models.Workspace)
            .join(
                workspace_models.WorkspaceMembership,
                and_(
                    workspace_models.WorkspaceMembership.workspace_id
                    == workspace_models.Workspace.id,
                    workspace_models.WorkspaceMembership.user_id == user_id,
                    workspace_models.WorkspaceMembership.deleted_at.is_(None),
                ),
            )
            .where(workspace_models.Workspace.deleted_at.is_(None))
        )
        rows, total = paginate(
            self._session,
            statement,
            count_statement,
            workspace_models.Workspace.created_at,
            page,
        )
        return Page(
            items=[_workspace_record(row) for row in rows],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def update(self, *, user_id: UUID, workspace_id: UUID, name: str) -> WorkspaceRecord:
        row = self._writable_workspace(user_id=user_id, workspace_id=workspace_id)
        row.name = name
        row.updated_at = now()
        flush_or_raise(self._session)
        return _workspace_record(row)

    def soft_delete(self, *, user_id: UUID, workspace_id: UUID) -> None:
        self.soft_delete_for_user(user_id=user_id, workspace_id=workspace_id)

    def soft_delete_for_user(self, *, user_id: UUID, workspace_id: UUID) -> WorkspaceRecord:
        row = self._session.scalars(
            select(workspace_models.Workspace)
            .join(
                workspace_models.WorkspaceMembership,
                and_(
                    workspace_models.WorkspaceMembership.workspace_id
                    == workspace_models.Workspace.id,
                    workspace_models.WorkspaceMembership.user_id == user_id,
                    workspace_models.WorkspaceMembership.role == WorkspaceRole.OWNER,
                    workspace_models.WorkspaceMembership.deleted_at.is_(None),
                ),
            )
            .where(
                workspace_models.Workspace.id == workspace_id,
                workspace_models.Workspace.deleted_at.is_(None),
            )
            .with_for_update()
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Workspace not found")

        timestamp = now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.execute(
            update(workspace_models.WorkspaceMembership)
            .where(
                workspace_models.WorkspaceMembership.workspace_id == workspace_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
            )
            .values(deleted_at=timestamp, updated_at=timestamp)
        )
        flush_or_raise(self._session)
        return _workspace_record(row)

    def user_has_workspace_role(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        minimum_role: str = "viewer",
    ) -> bool:
        return user_has_workspace_role(
            self._session,
            user_id=user_id,
            workspace_id=workspace_id,
            minimum_role=minimum_role,
        )

    def _writable_workspace(
        self, *, user_id: UUID, workspace_id: UUID
    ) -> workspace_models.Workspace:
        if not self.user_has_workspace_role(
            user_id=user_id,
            workspace_id=workspace_id,
            minimum_role="admin",
        ):
            raise EntityNotFoundError("Workspace not found")
        row = self._session.get(workspace_models.Workspace, workspace_id)
        if row is None or row.deleted_at is not None:
            raise EntityNotFoundError("Workspace not found")
        return row

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return (
            select(workspace_models.Workspace)
            .join(
                workspace_models.WorkspaceMembership,
                and_(
                    workspace_models.WorkspaceMembership.workspace_id
                    == workspace_models.Workspace.id,
                    workspace_models.WorkspaceMembership.user_id == user_id,
                    workspace_models.WorkspaceMembership.deleted_at.is_(None),
                ),
            )
            .where(workspace_models.WorkspaceMembership.deleted_at.is_(None))
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
