"""SQLAlchemy implementation of the invoice persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.invoice.models as invoice_models
from creator.invoice.ports import InvoiceRecord, InvoiceRepository


def _invoice(row: invoice_models.Invoice) -> InvoiceRecord:
    return InvoiceRecord(
        row.id,
        row.billing_account_id,
        row.subscription_id,
        row.amount_cents,
        row.currency,
        row.status,
        row.billing_at,
        row.due_at,
        row.created_at,
        row.updated_at,
        row.deleted_at,
    )


class SqlAlchemyInvoiceRepository(InvoiceRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _owned(self, user_id: UUID, invoice_id: UUID) -> invoice_models.Invoice | None:
        return self._session.scalar(
            select(invoice_models.Invoice)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id
                == invoice_models.Invoice.billing_account_id,
            )
            .where(
                invoice_models.Invoice.id == invoice_id,
                billing_account_models.BillingAccount.user_id == user_id,
                invoice_models.Invoice.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id: UUID) -> list[InvoiceRecord]:
        rows = self._session.scalars(
            select(invoice_models.Invoice)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id
                == invoice_models.Invoice.billing_account_id,
            )
            .where(
                billing_account_models.BillingAccount.user_id == user_id,
                invoice_models.Invoice.deleted_at.is_(None),
            )
        ).all()
        return [_invoice(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, invoice_id: UUID) -> InvoiceRecord | None:
        row = self._owned(user_id, invoice_id)
        return _invoice(row) if row else None

    def add(
        self,
        *,
        billing_account_id: UUID,
        subscription_id: UUID | None,
        amount_cents: int,
        currency: str,
        billing_at: datetime | None,
        due_at: datetime | None,
    ) -> InvoiceRecord:
        row = invoice_models.Invoice(
            billing_account_id=billing_account_id,
            subscription_id=subscription_id,
            amount_cents=amount_cents,
            currency=currency,
            status="pending",
            billing_at=billing_at,
            due_at=due_at,
        )
        self._session.add(row)
        self._session.flush()
        return _invoice(row)

    def update(self, *, invoice_id: UUID, fields: dict[str, object]) -> InvoiceRecord:
        row = self._session.get(invoice_models.Invoice, invoice_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Invoice not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _invoice(row)

    def soft_delete(self, *, invoice_id: UUID) -> None:
        row = self._session.get(invoice_models.Invoice, invoice_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Invoice not found")
        row.deleted_at = datetime.now(UTC)
        row.updated_at = row.deleted_at
        self._session.flush()
