"""SQLAlchemy implementation of the credit persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.credit.models as credit_models
import creator.workspace.models as workspace_models
from creator.credit.ports import (
    WorkspaceCreditTransactionRecord,
    WorkspaceCreditTransactionRepository,
)


class SqlAlchemyWorkspaceCreditTransactionRepository(WorkspaceCreditTransactionRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x: credit_models.WorkspaceCreditTransaction) -> WorkspaceCreditTransactionRecord:
        return WorkspaceCreditTransactionRecord(
            x.id,
            x.workspace_id,
            x.amount,
            x.transaction_type,
            x.reference_type,
            x.reference_id,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def list_for_user(
        self, *, user_id: UUID, workspace_id: UUID | None = None
    ) -> list[WorkspaceCreditTransactionRecord]:
        q = (
            select(credit_models.WorkspaceCreditTransaction)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == credit_models.WorkspaceCreditTransaction.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                credit_models.WorkspaceCreditTransaction.deleted_at.is_(None),
            )
        )
        if workspace_id is not None:
            q = q.where(credit_models.WorkspaceCreditTransaction.workspace_id == workspace_id)
        return [self._r(x) for x in self.s.scalars(q).all()]

    def get_for_user(
        self, *, user_id: UUID, transaction_id: UUID
    ) -> WorkspaceCreditTransactionRecord | None:
        x = self.s.scalar(
            select(credit_models.WorkspaceCreditTransaction)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == credit_models.WorkspaceCreditTransaction.workspace_id,
            )
            .where(
                credit_models.WorkspaceCreditTransaction.id == transaction_id,
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                credit_models.WorkspaceCreditTransaction.deleted_at.is_(None),
            )
        )
        return self._r(x) if x else None

    def add(self, *, fields: dict[str, object]) -> WorkspaceCreditTransactionRecord:
        x = credit_models.WorkspaceCreditTransaction(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, transaction_id: UUID) -> None:
        x = self.s.get(credit_models.WorkspaceCreditTransaction, transaction_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Workspace credit transaction not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
