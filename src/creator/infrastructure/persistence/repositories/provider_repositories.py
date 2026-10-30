from __future__ import annotations

# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.billing_account import models as billing_account_tables
from creator.billing_provider import models as billing_provider_tables
from creator.billing_provider.ports import ProviderDisputeRecord, ProviderDisputeRepository
from creator.refund import models as refund_tables
from creator.refund.ports import RefundRecord, RefundRepository


class SqlAlchemyRefundRepository(RefundRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return RefundRecord(
            x.id,
            x.billing_account_id,
            x.invoice_id,
            x.amount_cents,
            x.currency,
            x.reason,
            x.status,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, rid):
        return self.s.scalar(
            select(refund_tables.Refund)
            .join(billing_account_tables.BillingAccount)
            .where(
                refund_tables.Refund.id == rid,
                billing_account_tables.BillingAccount.user_id == uid,
                refund_tables.Refund.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(refund_tables.Refund)
                .join(billing_account_tables.BillingAccount)
                .where(
                    billing_account_tables.BillingAccount.user_id == user_id,
                    refund_tables.Refund.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, refund_id):
        x = self._owned(user_id, refund_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = refund_tables.Refund(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, refund_id, fields):
        x = self.s.get(refund_tables.Refund, refund_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Refund not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, refund_id):
        x = self.s.get(refund_tables.Refund, refund_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Refund not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyProviderDisputeRepository(ProviderDisputeRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return ProviderDisputeRecord(
            x.id,
            x.billing_account_id,
            x.charge_id,
            x.code,
            x.reason,
            x.status,
            x.opened_at,
            x.deadline_at,
            x.payload,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, did):
        return self.s.scalar(
            select(billing_provider_tables.ProviderDispute)
            .join(billing_account_tables.BillingAccount)
            .where(
                billing_provider_tables.ProviderDispute.id == did,
                billing_account_tables.BillingAccount.user_id == uid,
                billing_provider_tables.ProviderDispute.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(billing_provider_tables.ProviderDispute)
                .join(billing_account_tables.BillingAccount)
                .where(
                    billing_account_tables.BillingAccount.user_id == user_id,
                    billing_provider_tables.ProviderDispute.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, dispute_id):
        x = self._owned(user_id, dispute_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = billing_provider_tables.ProviderDispute(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, dispute_id, fields):
        x = self.s.get(billing_provider_tables.ProviderDispute, dispute_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider dispute not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, dispute_id):
        x = self.s.get(billing_provider_tables.ProviderDispute, dispute_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider dispute not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
