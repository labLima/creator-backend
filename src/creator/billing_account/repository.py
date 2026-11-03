"""SQLAlchemy implementation of the billing_account persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
from creator.billing_account.ports import (
    BillingAccountRecord,
    BillingAddressRecord,
    BillingAddressRepository,
)


def _billing_account(row: billing_account_models.BillingAccount) -> BillingAccountRecord:
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
            select(billing_account_models.BillingAccount)
            .where(
                billing_account_models.BillingAccount.user_id == user_id,
                billing_account_models.BillingAccount.deleted_at.is_(None),
            )
            .order_by(billing_account_models.BillingAccount.created_at.desc())
        ).all()
        return [_billing_account(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, account_id: UUID) -> BillingAccountRecord | None:
        row = self._session.scalars(
            select(billing_account_models.BillingAccount).where(
                billing_account_models.BillingAccount.id == account_id,
                billing_account_models.BillingAccount.user_id == user_id,
                billing_account_models.BillingAccount.deleted_at.is_(None),
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
        row = billing_account_models.BillingAccount(
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
            select(billing_account_models.BillingAccount).where(
                billing_account_models.BillingAccount.id == account_id,
                billing_account_models.BillingAccount.user_id == user_id,
                billing_account_models.BillingAccount.deleted_at.is_(None),
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
            select(billing_account_models.BillingAccount).where(
                billing_account_models.BillingAccount.id == account_id,
                billing_account_models.BillingAccount.user_id == user_id,
                billing_account_models.BillingAccount.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None:
            raise ValueError("Billing account not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()


class SqlAlchemyBillingAddressRepository(BillingAddressRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _record(self, x: billing_account_models.BillingAddress) -> BillingAddressRecord:
        return BillingAddressRecord(
            x.id,
            x.billing_account_id,
            x.street,
            x.number,
            x.complement,
            x.neighborhood,
            x.zip_code,
            x.city,
            x.state,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid: UUID, aid: UUID):
        return self.s.scalar(
            select(billing_account_models.BillingAddress)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_account_models.BillingAddress.id == aid,
                billing_account_models.BillingAccount.user_id == uid,
                billing_account_models.BillingAddress.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id: UUID, account_id: UUID | None = None):
        q = (
            select(billing_account_models.BillingAddress)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_account_models.BillingAccount.user_id == user_id,
                billing_account_models.BillingAddress.deleted_at.is_(None),
            )
        )
        if account_id is not None:
            q = q.where(billing_account_models.BillingAddress.billing_account_id == account_id)
        return [self._record(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id: UUID, address_id: UUID):
        x = self._owned(user_id, address_id)
        return self._record(x) if x else None

    def add(self, *, billing_account_id: UUID, fields: dict[str, object]):
        x = billing_account_models.BillingAddress(billing_account_id=billing_account_id, **fields)
        self.s.add(x)
        self.s.flush()
        return self._record(x)

    def update(self, *, address_id: UUID, fields: dict[str, object]):
        x = self.s.get(billing_account_models.BillingAddress, address_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Billing address not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._record(x)

    def soft_delete(self, *, address_id: UUID):
        x = self.s.get(billing_account_models.BillingAddress, address_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Billing address not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
