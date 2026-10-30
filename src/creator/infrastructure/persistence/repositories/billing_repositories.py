"""Repository ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.billing_account import models as billing_account_tables
from creator.billing_account.ports import BillingAccountRecord
from creator.plan.repository import SqlAlchemyPlanItemRepository, SqlAlchemyPlanRepository


def _billing_account(row: billing_account_tables.BillingAccount) -> BillingAccountRecord:
    return BillingAccountRecord(
        id=row.id,
        user_id=row.user_id,
        payer_type=row.payer_type,
        name=row.name,
        email=row.email,
        phone=row.phone,
        document=row.document,
        document_type=row.document_type,
        company_name=row.company_name,
        provider=row.provider,
        provider_customer_id=row.provider_customer_id,
        provider_customer_code=row.provider_customer_code,
        delinquent=row.delinquent,
        metadata=dict(row.metadata_json or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyBillingAccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, *, user_id: UUID) -> list[BillingAccountRecord]:
        rows = self._session.scalars(
            select(billing_account_tables.BillingAccount)
            .where(
                billing_account_tables.BillingAccount.user_id == user_id,
                billing_account_tables.BillingAccount.deleted_at.is_(None),
            )
            .order_by(billing_account_tables.BillingAccount.created_at.desc())
        ).all()
        return [_billing_account(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, account_id: UUID) -> BillingAccountRecord | None:
        row = self._session.scalars(
            select(billing_account_tables.BillingAccount).where(
                billing_account_tables.BillingAccount.id == account_id,
                billing_account_tables.BillingAccount.user_id == user_id,
                billing_account_tables.BillingAccount.deleted_at.is_(None),
            )
        ).one_or_none()
        return _billing_account(row) if row else None

    def add(
        self,
        *,
        user_id: UUID,
        payer_type: str,
        name: str,
        email: str,
        phone: str | None,
        document: str | None,
        document_type: str | None,
    ) -> BillingAccountRecord:
        row = billing_account_tables.BillingAccount(
            user_id=user_id,
            payer_type=payer_type,
            name=name,
            email=email,
            phone=phone,
            document=document,
            document_type=document_type,
        )
        self._session.add(row)
        self._session.flush()
        return _billing_account(row)

    def update(
        self, *, user_id: UUID, account_id: UUID, fields: dict[str, object]
    ) -> BillingAccountRecord:
        row = self._session.scalars(
            select(billing_account_tables.BillingAccount).where(
                billing_account_tables.BillingAccount.id == account_id,
                billing_account_tables.BillingAccount.user_id == user_id,
                billing_account_tables.BillingAccount.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise ValueError("Billing account not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _billing_account(row)

    def soft_delete(self, *, user_id: UUID, account_id: UUID) -> None:
        row = self._session.scalars(
            select(billing_account_tables.BillingAccount).where(
                billing_account_tables.BillingAccount.id == account_id,
                billing_account_tables.BillingAccount.user_id == user_id,
                billing_account_tables.BillingAccount.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise ValueError("Billing account not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()


__all__ = [
    "SqlAlchemyBillingAccountRepository",
    "SqlAlchemyPlanItemRepository",
    "SqlAlchemyPlanRepository",
]
