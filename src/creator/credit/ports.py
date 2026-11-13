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

    def workspace_balance(self, workspace_id: UUID) -> int:
        """Available credit of a Workspace: ``SUM`` of the non-expired lots.

        This is the derived measure of ADR-019 (the dump's
        ``workspace_credit_balance``), not the ledger balance: an expired Credit
        Lot stops counting even though its grant stays in the ledger.
        """
        ...

    def lot_available(self, workspace_id: UUID, lot_id: UUID) -> int:
        """Availability of one Credit Lot; ``0`` when it is expired, unknown or foreign.

        The dump's ``workspace_credit_lot_available``. A Credit Lot is tenant scoped
        (ADR-019 decision 6), so the Workspace is part of the read: an identifier
        alone must never expose another Workspace's availability. Returning ``0``
        instead of raising keeps the caller from spending credit the lot no longer
        holds.
        """
        ...
