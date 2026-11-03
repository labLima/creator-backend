"""SQLAlchemy implementation of the subscription persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.billing_account.models as billing_account_models
import creator.subscription.models as subscription_models
from creator.subscription.ports import (
    SubscriptionHistoryRecord,
    SubscriptionHistoryRepository,
    SubscriptionRecord,
    SubscriptionRepository,
)


def _subscription(row: subscription_models.Subscription) -> SubscriptionRecord:
    return SubscriptionRecord(
        row.id,
        row.billing_account_id,
        row.workspace_id,
        row.plan_id,
        row.status,
        row.payment_method,
        row.billing_day,
        row.start_at,
        row.created_at,
        row.updated_at,
        row.deleted_at,
    )


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _owned(
        self, user_id: UUID, subscription_id: UUID
    ) -> subscription_models.Subscription | None:
        return self._session.scalar(
            select(subscription_models.Subscription)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id
                == subscription_models.Subscription.billing_account_id,
            )
            .where(
                subscription_models.Subscription.id == subscription_id,
                billing_account_models.BillingAccount.user_id == user_id,
                subscription_models.Subscription.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id: UUID) -> list[SubscriptionRecord]:
        rows = self._session.scalars(
            select(subscription_models.Subscription)
            .join(
                billing_account_models.BillingAccount,
                billing_account_models.BillingAccount.id
                == subscription_models.Subscription.billing_account_id,
            )
            .where(
                billing_account_models.BillingAccount.user_id == user_id,
                subscription_models.Subscription.deleted_at.is_(None),
            )
        ).all()
        return [_subscription(row) for row in rows]

    def get_for_user(self, *, user_id: UUID, subscription_id: UUID) -> SubscriptionRecord | None:
        row = self._owned(user_id, subscription_id)
        return _subscription(row) if row else None

    def add(
        self,
        *,
        billing_account_id: UUID,
        workspace_id: UUID,
        plan_id: UUID,
        payment_method: str | None,
        billing_day: int | None,
        start_at: datetime | None,
    ) -> SubscriptionRecord:
        row = subscription_models.Subscription(
            billing_account_id=billing_account_id,
            workspace_id=workspace_id,
            plan_id=plan_id,
            status="pending",
            payment_method=payment_method,
            billing_day=billing_day,
            start_at=start_at,
        )
        self._session.add(row)
        self._session.flush()
        return _subscription(row)

    def update(self, *, subscription_id: UUID, fields: dict[str, object]) -> SubscriptionRecord:
        row = self._session.get(subscription_models.Subscription, subscription_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Subscription not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _subscription(row)

    def soft_delete(self, *, subscription_id: UUID) -> None:
        row = self._session.get(subscription_models.Subscription, subscription_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Subscription not found")
        row.deleted_at = datetime.now(UTC)
        row.updated_at = row.deleted_at
        self._session.flush()


class SqlAlchemySubscriptionHistoryRepository(SubscriptionHistoryRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return SubscriptionHistoryRecord(
            x.id,
            x.subscription_id,
            x.change_type,
            x.previous_plan_id,
            x.plan_id,
            x.previous_status,
            x.status,
            x.reason,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _owned(self, uid, hid):
        return self.s.scalar(
            select(subscription_models.SubscriptionHistory)
            .join(subscription_models.Subscription)
            .join(billing_account_models.BillingAccount)
            .where(
                subscription_models.SubscriptionHistory.id == hid,
                billing_account_models.BillingAccount.user_id == uid,
                subscription_models.SubscriptionHistory.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(subscription_models.SubscriptionHistory)
                .join(subscription_models.Subscription)
                .join(billing_account_models.BillingAccount)
                .where(
                    billing_account_models.BillingAccount.user_id == user_id,
                    subscription_models.SubscriptionHistory.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, history_id):
        x = self._owned(user_id, history_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = subscription_models.SubscriptionHistory(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, history_id, fields):
        x = self.s.get(subscription_models.SubscriptionHistory, history_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Subscription history not found")
        for key, value in fields.items():
            setattr(x, key, value)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, history_id):
        x = self.s.get(subscription_models.SubscriptionHistory, history_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Subscription history not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
