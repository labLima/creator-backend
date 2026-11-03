"""SQLAlchemy implementation of the billing_provider persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.billing_provider.models as billing_provider_models
import creator.subscription.models as subscription_models
from creator.billing_provider.ports import (
    ProviderCustomerRecord,
    ProviderCustomerRepository,
    ProviderDisputeRecord,
    ProviderDisputeRepository,
    ProviderIdempotencyKeyRecord,
    ProviderIdempotencyKeyRepository,
    ProviderSubscriptionRecord,
    ProviderSubscriptionRepository,
    ProviderWebhookEventRecord,
    ProviderWebhookEventRepository,
)


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
            select(billing_provider_models.ProviderCustomer)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_provider_models.ProviderCustomer.id == rid,
                billing_account_models.BillingAccount.user_id == uid,
                billing_provider_models.ProviderCustomer.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(billing_provider_models.ProviderCustomer)
                .join(billing_account_models.BillingAccount)
                .where(
                    billing_account_models.BillingAccount.user_id == user_id,
                    billing_provider_models.ProviderCustomer.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, record_id):
        x = self._owned(user_id, record_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = billing_provider_models.ProviderCustomer(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, record_id, fields):
        x = self.s.get(billing_provider_models.ProviderCustomer, record_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider customer not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, record_id):
        x = self.s.get(billing_provider_models.ProviderCustomer, record_id)
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
            select(billing_provider_models.ProviderSubscription)
            .join(subscription_models.Subscription)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_provider_models.ProviderSubscription.id == rid,
                billing_account_models.BillingAccount.user_id == uid,
                billing_provider_models.ProviderSubscription.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(billing_provider_models.ProviderSubscription)
                .join(subscription_models.Subscription)
                .join(billing_account_models.BillingAccount)
                .where(
                    billing_account_models.BillingAccount.user_id == user_id,
                    billing_provider_models.ProviderSubscription.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, record_id):
        x = self._owned(user_id, record_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = billing_provider_models.ProviderSubscription(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, record_id, fields):
        x = self.s.get(billing_provider_models.ProviderSubscription, record_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider subscription not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, record_id):
        x = self.s.get(billing_provider_models.ProviderSubscription, record_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider subscription not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()


class SqlAlchemyProviderWebhookEventRepository(ProviderWebhookEventRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return ProviderWebhookEventRecord(
            x.id,
            x.provider,
            x.provider_event_id,
            x.dedupe_key,
            x.event_type,
            x.account_id,
            x.resource_type,
            x.resource_id,
            x.payload,
            x.signature_verified,
            x.status,
            x.attempts,
            x.last_error,
            x.received_at,
            x.processed_at,
        )

    def list(self):
        return [
            self._r(x)
            for x in self.s.scalars(select(billing_provider_models.ProviderWebhookEvent)).all()
        ]

    def get(self, *, event_id):
        x = self.s.get(billing_provider_models.ProviderWebhookEvent, event_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = billing_provider_models.ProviderWebhookEvent(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, event_id, fields):
        x = self.s.get(billing_provider_models.ProviderWebhookEvent, event_id)
        if x is None:
            raise ValueError("Provider webhook event not found")
        for k, v in fields.items():
            setattr(x, k, v)
        self.s.flush()
        return self._r(x)


class SqlAlchemyProviderIdempotencyKeyRepository(ProviderIdempotencyKeyRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return ProviderIdempotencyKeyRecord(
            x.id,
            x.provider,
            x.idempotency_key,
            x.request_hash,
            x.resource_type,
            x.resource_id,
            x.status,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def list(self):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(billing_provider_models.ProviderIdempotencyKey).where(
                    billing_provider_models.ProviderIdempotencyKey.deleted_at.is_(None)
                )
            ).all()
        ]

    def get(self, *, key_id):
        x = self.s.get(billing_provider_models.ProviderIdempotencyKey, key_id)
        return self._r(x) if x and x.deleted_at is None else None

    def add(self, *, fields):
        x = billing_provider_models.ProviderIdempotencyKey(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, key_id, fields):
        x = self.s.get(billing_provider_models.ProviderIdempotencyKey, key_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider idempotency key not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)


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
            select(billing_provider_models.ProviderDispute)
            .join(billing_account_models.BillingAccount)
            .where(
                billing_provider_models.ProviderDispute.id == did,
                billing_account_models.BillingAccount.user_id == uid,
                billing_provider_models.ProviderDispute.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(billing_provider_models.ProviderDispute)
                .join(billing_account_models.BillingAccount)
                .where(
                    billing_account_models.BillingAccount.user_id == user_id,
                    billing_provider_models.ProviderDispute.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, dispute_id):
        x = self._owned(user_id, dispute_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = billing_provider_models.ProviderDispute(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, dispute_id, fields):
        x = self.s.get(billing_provider_models.ProviderDispute, dispute_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider dispute not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, dispute_id):
        x = self.s.get(billing_provider_models.ProviderDispute, dispute_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Provider dispute not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
