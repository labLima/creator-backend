"""SQLAlchemy implementation of the plan persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.plan.models as plan_models
from creator.plan.ports import PlanItemRecord, PlanRecord


def _plan(row: plan_models.Plan) -> PlanRecord:
    return PlanRecord(
        id=row.id,
        code=row.code,
        type=row.type,
        name=row.name,
        description=row.description,
        metadata=dict(row.metadata_json or {}),
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyPlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[PlanRecord]:
        rows = self._session.scalars(
            select(plan_models.Plan)
            .where(plan_models.Plan.deleted_at.is_(None))
            .order_by(plan_models.Plan.created_at.desc())
        ).all()
        return [_plan(row) for row in rows]

    def get(self, *, plan_id: UUID) -> PlanRecord | None:
        row = self._session.scalars(
            select(plan_models.Plan).where(
                plan_models.Plan.id == plan_id,
                plan_models.Plan.deleted_at.is_(None),
            )
        ).one_or_none()
        return _plan(row) if row else None

    def add(
        self,
        *,
        code: str,
        type: str,
        name: str,
        description: str | None,
        metadata: dict[str, object],
        is_active: bool,
    ) -> PlanRecord:
        row = plan_models.Plan(
            code=code,
            type=type,
            name=name,
            description=description,
            metadata_json=metadata,
            is_active=is_active,
        )
        self._session.add(row)
        self._session.flush()
        return _plan(row)

    def update(self, *, plan_id: UUID, fields: dict[str, object]) -> PlanRecord:
        row = self._session.get(plan_models.Plan, plan_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Plan not found")
        mapping = {"metadata": "metadata_json"}
        for name, value in fields.items():
            setattr(row, mapping.get(name, name), value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _plan(row)

    def soft_delete(self, *, plan_id: UUID) -> None:
        row = self._session.get(plan_models.Plan, plan_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Plan not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()


def _plan_item(row: plan_models.PlanItem) -> PlanItemRecord:
    return PlanItemRecord(
        id=row.id,
        plan_id=row.plan_id,
        name=row.name,
        description=row.description,
        quantity=row.quantity,
        cycles=row.cycles,
        pricing_scheme_type=row.pricing_scheme_type,
        price_cents=row.price_cents,
        price_brackets=dict(row.price_brackets) if row.price_brackets else None,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyPlanItemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *, plan_id: UUID | None = None) -> list[PlanItemRecord]:
        statement = select(plan_models.PlanItem).where(plan_models.PlanItem.deleted_at.is_(None))
        if plan_id is not None:
            statement = statement.where(plan_models.PlanItem.plan_id == plan_id)
        rows = self._session.scalars(
            statement.order_by(plan_models.PlanItem.created_at.desc())
        ).all()
        return [_plan_item(row) for row in rows]

    def get(self, *, item_id: UUID) -> PlanItemRecord | None:
        row = self._session.scalars(
            select(plan_models.PlanItem).where(
                plan_models.PlanItem.id == item_id, plan_models.PlanItem.deleted_at.is_(None)
            )
        ).one_or_none()
        return _plan_item(row) if row else None

    def add(
        self,
        *,
        plan_id: UUID,
        name: str,
        description: str | None,
        quantity: int,
        cycles: int | None,
        pricing_scheme_type: str | None,
        price_cents: int,
        price_brackets: dict[str, object] | None,
        status: str | None,
    ) -> PlanItemRecord:
        row = plan_models.PlanItem(
            plan_id=plan_id,
            name=name,
            description=description,
            quantity=quantity,
            cycles=cycles,
            pricing_scheme_type=pricing_scheme_type,
            price_cents=price_cents,
            price_brackets=price_brackets,
            status=status,
        )
        self._session.add(row)
        self._session.flush()
        return _plan_item(row)

    def update(self, *, item_id: UUID, fields: dict[str, object]) -> PlanItemRecord:
        row = self._session.get(plan_models.PlanItem, item_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Plan item not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _plan_item(row)

    def soft_delete(self, *, item_id: UUID) -> None:
        row = self._session.get(plan_models.PlanItem, item_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Plan item not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()
