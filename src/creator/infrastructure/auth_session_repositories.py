from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.infrastructure import models
from creator.repositories.auth import AuthSessionRecord


def _record(row: models.AuthSession) -> AuthSessionRecord:
    return AuthSessionRecord(
        id=row.id,
        user_id=row.user_id,
        family_id=row.family_id,
        refresh_token_hash=row.refresh_token_hash,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by_id=row.replaced_by_id,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
    )


class SqlAlchemyAuthSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        user_id: UUID,
        family_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthSessionRecord:
        row = models.AuthSession(
            user_id=user_id,
            family_id=family_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self._session.add(row)
        self._session.flush()
        return _record(row)

    def get_by_id(self, session_id: UUID) -> AuthSessionRecord | None:
        row = self._session.get(models.AuthSession, session_id)
        return _record(row) if row else None

    def get_by_refresh_hash(self, refresh_token_hash: str) -> AuthSessionRecord | None:
        row = self._session.scalars(
            select(models.AuthSession).where(
                models.AuthSession.refresh_token_hash == refresh_token_hash
            )
        ).one_or_none()
        return _record(row) if row else None

    def revoke(self, session_id: UUID, *, replaced_by_id: UUID | None = None) -> None:
        row = self._session.get(models.AuthSession, session_id)
        if row is None or row.revoked_at is not None:
            return
        row.revoked_at = datetime.now(UTC)
        row.replaced_by_id = replaced_by_id
        self._session.flush()

    def revoke_family(self, family_id: UUID) -> None:
        rows = self._session.scalars(
            select(models.AuthSession).where(
                models.AuthSession.family_id == family_id,
                models.AuthSession.revoked_at.is_(None),
            )
        ).all()
        now = datetime.now(UTC)
        for row in rows:
            row.revoked_at = now
        self._session.flush()

    def touch(self, session_id: UUID, *, at: datetime) -> None:
        row = self._session.get(models.AuthSession, session_id)
        if row is not None:
            row.last_used_at = at
            self._session.flush()
