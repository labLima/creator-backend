from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthSessionRecord:
    id: UUID
    user_id: UUID
    family_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by_id: UUID | None
    created_at: datetime
    last_used_at: datetime | None


class AuthSessionRepository(Protocol):
    def add(
        self,
        *,
        user_id: UUID,
        family_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthSessionRecord: ...

    def get_by_id(self, session_id: UUID) -> AuthSessionRecord | None: ...

    def get_by_refresh_hash(self, refresh_token_hash: str) -> AuthSessionRecord | None: ...

    def revoke(self, session_id: UUID, *, replaced_by_id: UUID | None = None) -> None: ...

    def revoke_family(self, family_id: UUID) -> None: ...

    def touch(self, session_id: UUID, *, at: datetime) -> None: ...
