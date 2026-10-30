from __future__ import annotations

# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.billing_account import models as billing_account_tables
from creator.billing_provider import models as billing_provider_tables
from creator.repositories.provider_sync import (
    ProviderCustomerRecord,
    ProviderCustomerRepository,
    ProviderSubscriptionRecord,
    ProviderSubscriptionRepository,
)
from creator.subscription import models as subscription_tables


class SqlAlchemyProviderCustomerRepository(ProviderCustomerRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return ProviderCustomerRecord(
            x.id,
            x.billing_account_id,
            x.provider,
            x.provider_customer_id,
            x.provider_code,
            x.metadata_json,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, rid):
        return self.s.scalar(
            select(billing_provider_tables.ProviderCustomer)
            .join(billing_account_tables.BillingAccount)
            .where(
                billing_provider_tables.ProviderCustomer.id == rid,
                billing_account_tables.BillingAccount.user_id == uid,
                billing_provider_tables.ProviderCustomer.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(billing_provider_tables.ProviderCustomer)
                .join(billing_account_tables.BillingAccount)
                .where(
                    billing_account_tables.BillingAccount.user_id == user_id,
                    billing_provider_tables.ProviderCustomer.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, record_id):
        x = self._owned(user_id, record_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = billing_provider_tables.ProviderCustomer(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, record_id, fields):
        x = self.s.get(billing_provider_tables.ProviderCustomer, record_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider customer not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, record_id):
        x = self.s.get(billing_provider_tables.ProviderCustomer, record_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider customer not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyProviderSubscriptionRepository(ProviderSubscriptionRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return ProviderSubscriptionRecord(
            x.id,
            x.subscription_id,
            x.provider,
            x.provider_subscription_id,
            x.provider_status,
            x.payload,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, rid):
        return self.s.scalar(
            select(billing_provider_tables.ProviderSubscription)
            .join(subscription_tables.Subscription)
            .join(billing_account_tables.BillingAccount)
            .where(
                billing_provider_tables.ProviderSubscription.id == rid,
                billing_account_tables.BillingAccount.user_id == uid,
                billing_provider_tables.ProviderSubscription.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(billing_provider_tables.ProviderSubscription)
                .join(subscription_tables.Subscription)
                .join(billing_account_tables.BillingAccount)
                .where(
                    billing_account_tables.BillingAccount.user_id == user_id,
                    billing_provider_tables.ProviderSubscription.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, record_id):
        x = self._owned(user_id, record_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = billing_provider_tables.ProviderSubscription(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, record_id, fields):
        x = self.s.get(billing_provider_tables.ProviderSubscription, record_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider subscription not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, record_id):
        x = self.s.get(billing_provider_tables.ProviderSubscription, record_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider subscription not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
