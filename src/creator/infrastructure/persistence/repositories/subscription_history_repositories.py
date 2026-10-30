from __future__ import annotations

from datetime import UTC, datetime

# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False
from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.modules.billing_account.adapters import tables as billing_account_tables
from creator.modules.subscription.adapters import tables as subscription_tables
from creator.repositories.subscription_history import (
    SubscriptionHistoryRecord,
    SubscriptionHistoryRepository,
)


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
            select(subscription_tables.SubscriptionHistory)
            .join(subscription_tables.Subscription)
            .join(billing_account_tables.BillingAccount)
            .where(
                subscription_tables.SubscriptionHistory.id == hid,
                billing_account_tables.BillingAccount.user_id == uid,
                subscription_tables.SubscriptionHistory.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id):
        return [
            self._r(x)
            for x in self.s.scalars(
                select(subscription_tables.SubscriptionHistory)
                .join(subscription_tables.Subscription)
                .join(billing_account_tables.BillingAccount)
                .where(
                    billing_account_tables.BillingAccount.user_id == user_id,
                    subscription_tables.SubscriptionHistory.deleted_at.is_(None),
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, history_id):
        x = self._owned(user_id, history_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        x = subscription_tables.SubscriptionHistory(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, history_id, fields):
        x = self.s.get(subscription_tables.SubscriptionHistory, history_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Subscription history not found")
        for key, value in fields.items():
            setattr(x, key, value)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, history_id):
        x = self.s.get(subscription_tables.SubscriptionHistory, history_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Subscription history not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
