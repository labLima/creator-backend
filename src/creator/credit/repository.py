"""SQLAlchemy implementation of the credit persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.credit.models as credit_models
import creator.workspace.models as workspace_models
from creator.credit.ports import (
    WorkspaceCreditTransactionRecord,
    WorkspaceCreditTransactionRepository,
)
from creator.infrastructure.database.enums import MemberStatus


class SqlAlchemyWorkspaceCreditTransactionRepository(WorkspaceCreditTransactionRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x: credit_models.WorkspaceCreditTransaction) -> WorkspaceCreditTransactionRecord:
        return WorkspaceCreditTransactionRecord(
            id=x.id,
            workspace_id=x.workspace_id,
            amount=x.amount,
            balance_after=x.balance_after,
            type=x.type,
            order_id=x.order_id,
            invoice_id=x.invoice_id,
            generated_image_id=x.generated_image_id,
            image_resize_id=x.image_resize_id,
            created_by=x.created_by,
            created_at=x.created_at,
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
            .join(
                workspace_models.Workspace,
                workspace_models.Workspace.id
                == credit_models.WorkspaceCreditTransaction.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.status == MemberStatus.ACTIVE,
                workspace_models.Workspace.deleted_at.is_(None),
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
            .join(
                workspace_models.Workspace,
                workspace_models.Workspace.id
                == credit_models.WorkspaceCreditTransaction.workspace_id,
            )
            .where(
                credit_models.WorkspaceCreditTransaction.id == transaction_id,
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.status == MemberStatus.ACTIVE,
                workspace_models.Workspace.deleted_at.is_(None),
            )
        )
        return self._r(x) if x else None
