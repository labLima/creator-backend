"""Persistence ports owned by the credit capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkspaceCreditTransactionRecord:
    id: UUID
    workspace_id: UUID
    amount: int
    transaction_type: str
    reference_type: str | None
    reference_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class WorkspaceCreditTransactionRepository(Protocol):
    def list_for_user(
        self, *, user_id: UUID, workspace_id: UUID | None = None
    ) -> list[WorkspaceCreditTransactionRecord]: ...
    def get_for_user(
        self, *, user_id: UUID, transaction_id: UUID
    ) -> WorkspaceCreditTransactionRecord | None: ...
    def add(self, *, fields: dict[str, object]) -> WorkspaceCreditTransactionRecord: ...
    def soft_delete(self, *, transaction_id: UUID) -> None: ...
