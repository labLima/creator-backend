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
    balance_after: int
    type: str
    order_id: UUID | None
    invoice_id: UUID | None
    generated_image_id: UUID | None
    image_resize_id: UUID | None
    created_by: UUID | None
    created_at: datetime


class WorkspaceCreditTransactionRepository(Protocol):
    def list_for_user(
        self, *, user_id: UUID, workspace_id: UUID | None = None
    ) -> list[WorkspaceCreditTransactionRecord]: ...
    def get_for_user(
        self, *, user_id: UUID, transaction_id: UUID
    ) -> WorkspaceCreditTransactionRecord | None: ...
