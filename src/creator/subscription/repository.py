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
import creator.plan.models as plan_models
import creator.subscription.models as subscription_models
from creator.subscription.ports import (
    SubscriptionHistoryRecord,
    SubscriptionHistoryRepository,
    SubscriptionRecord,
    SubscriptionRepository,
)


def _subscription(row: subscription_models.Subscription) -> SubscriptionRecord:
    return SubscriptionRecord(
        id=row.id,
        billing_account_id=row.billing_account_id,
        workspace_id=row.workspace_id,
        plan_id=row.plan_id,
        status=row.status,
        payment_method=row.payment_method,
        billing_day=None,
        start_at=row.current_period_start,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=None,
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
        plan = self._session.get(plan_models.Plan, plan_id)
        price_cents = plan.price_cents if plan is not None else 0
        currency = plan.currency if plan is not None else "BRL"
        row = subscription_models.Subscription(
            billing_account_id=billing_account_id,
            workspace_id=workspace_id,
            plan_id=plan_id,
            contracted_price_cents=price_cents,
            currency=currency,
            status="ACTIVE",
            payment_method=(payment_method or "").upper() or None,
            current_period_start=start_at,
        )
        self._session.add(row)
        self._session.flush()
        return _subscription(row)

    def update(self, *, subscription_id: UUID, fields: dict[str, object]) -> SubscriptionRecord:
        row = self._session.get(subscription_models.Subscription, subscription_id)
        if row is None:
            raise ValueError("Subscription not found")
        mapping = {"start_at": "current_period_start", "billing_day": None}
        for name, value in fields.items():
            target = mapping.get(name, name)
            if target is None:
                continue
            if target == "status" and value is not None:
                value = str(value).upper()
            if hasattr(row, target):
                setattr(row, target, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _subscription(row)

    def soft_delete(self, *, subscription_id: UUID) -> None:
        row = self._session.get(subscription_models.Subscription, subscription_id)
        if row is None:
            raise ValueError("Subscription not found")
        timestamp = datetime.now(UTC)
        row.status = "CANCELED"
        row.canceled_at = timestamp
        row.updated_at = timestamp
        self._session.flush()


class SqlAlchemySubscriptionHistoryRepository(SubscriptionHistoryRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return SubscriptionHistoryRecord(
            id=x.id,
            subscription_id=x.subscription_id,
            change_type=x.change_type,
            previous_plan_id=x.old_plan_id,
            plan_id=x.new_plan_id,
            previous_status=x.old_status,
            status=x.new_status,
            reason=x.reason_text or x.reason_code,
            created_at=x.created_at,
            updated_at=x.created_at,
            deleted_at=None,
        )

    def _owned(self, uid, hid):
        return self.s.scalar(
            select(subscription_models.SubscriptionHistory)
            .join(subscription_models.Subscription)
            .join(billing_account_models.BillingAccount)
            .where(
                subscription_models.SubscriptionHistory.id == hid,
                billing_account_models.BillingAccount.user_id == uid,
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
                )
            ).all()
        ]

    def get_for_user(self, *, user_id, history_id):
        x = self._owned(user_id, history_id)
        return self._r(x) if x else None

    def add(self, *, fields):
        mapping = {
            "previous_plan_id": "old_plan_id",
            "plan_id": "new_plan_id",
            "previous_status": "old_status",
            "status": "new_status",
            "reason": "reason_text",
        }
        values = {}
        for key, value in fields.items():
            target = mapping.get(key, key)
            if target in {"change_type", "old_status", "new_status"} and value is not None:
                value = str(value).upper()
            values[target] = value
        x = subscription_models.SubscriptionHistory(**values)
        self.s.add(x)
        self.s.flush()
        return self._r(x)
