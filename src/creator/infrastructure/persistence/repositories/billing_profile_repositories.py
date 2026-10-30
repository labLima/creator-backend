from __future__ import annotations

# Repository methods are structurally typed by the Protocols; SQLAlchemy's
# inferred scalar result types are intentionally kept behind this adapter.
# mypy: disable-error-code=no-untyped-def
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.billing_account import models as billing_account_tables
from creator.payment_method import models as payment_method_tables
from creator.repositories.billing import (
    BillingAddressRecord,
    BillingAddressRepository,
    BillingPaymentMethodRecord,
    BillingPaymentMethodRepository,
)


class SqlAlchemyBillingAddressRepository(BillingAddressRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _record(self, x: billing_account_tables.BillingAddress) -> BillingAddressRecord:
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
            select(billing_account_tables.BillingAddress)
            .join(billing_account_tables.BillingAccount)
            .where(
                billing_account_tables.BillingAddress.id == aid,
                billing_account_tables.BillingAccount.user_id == uid,
                billing_account_tables.BillingAddress.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id: UUID, account_id: UUID | None = None):
        q = (
            select(billing_account_tables.BillingAddress)
            .join(billing_account_tables.BillingAccount)
            .where(
                billing_account_tables.BillingAccount.user_id == user_id,
                billing_account_tables.BillingAddress.deleted_at.is_(None),
            )
        )
        if account_id is not None:
            q = q.where(billing_account_tables.BillingAddress.billing_account_id == account_id)
        return [self._record(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id: UUID, address_id: UUID):
        x = self._owned(user_id, address_id)
        return self._record(x) if x else None

    def add(self, *, billing_account_id: UUID, fields: dict[str, object]):
        x = billing_account_tables.BillingAddress(billing_account_id=billing_account_id, **fields)
        self.s.add(x)
        self.s.flush()
        return self._record(x)

    def update(self, *, address_id: UUID, fields: dict[str, object]):
        x = self.s.get(billing_account_tables.BillingAddress, address_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Billing address not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._record(x)

    def soft_delete(self, *, address_id: UUID):
        x = self.s.get(billing_account_tables.BillingAddress, address_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Billing address not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyBillingPaymentMethodRepository(BillingPaymentMethodRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _record(self, x: payment_method_tables.BillingPaymentMethod) -> BillingPaymentMethodRecord:
        return BillingPaymentMethodRecord(
            x.id,
            x.billing_account_id,
            x.holder_name,
            x.holder_document,
            x.card_brand,
            x.card_last_four,
            x.exp_month,
            x.exp_year,
            x.card_type,
            x.card_status,
            x.is_default,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid: UUID, mid: UUID):
        return self.s.scalar(
            select(payment_method_tables.BillingPaymentMethod)
            .join(billing_account_tables.BillingAccount)
            .where(
                payment_method_tables.BillingPaymentMethod.id == mid,
                billing_account_tables.BillingAccount.user_id == uid,
                payment_method_tables.BillingPaymentMethod.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id: UUID, account_id: UUID | None = None):
        q = (
            select(payment_method_tables.BillingPaymentMethod)
            .join(billing_account_tables.BillingAccount)
            .where(
                billing_account_tables.BillingAccount.user_id == user_id,
                payment_method_tables.BillingPaymentMethod.deleted_at.is_(None),
            )
        )
        if account_id is not None:
            q = q.where(payment_method_tables.BillingPaymentMethod.billing_account_id == account_id)
        return [self._record(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id: UUID, method_id: UUID):
        x = self._owned(user_id, method_id)
        return self._record(x) if x else None

    def add(self, *, billing_account_id: UUID, fields: dict[str, object]):
        x = payment_method_tables.BillingPaymentMethod(
            billing_account_id=billing_account_id, **fields
        )
        self.s.add(x)
        self.s.flush()
        return self._record(x)

    def update(self, *, method_id: UUID, fields: dict[str, object]):
        x = self.s.get(payment_method_tables.BillingPaymentMethod, method_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Billing payment method not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._record(x)

    def soft_delete(self, *, method_id: UUID):
        x = self.s.get(payment_method_tables.BillingPaymentMethod, method_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Billing payment method not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
