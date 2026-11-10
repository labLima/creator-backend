"""SQLAlchemy implementation of the plan persistence ports.

The HTTP record keeps ``code``/``description``/``is_active``; the final tables
have no such columns, so the repository stores code/description in ``metadata``
and derives ``is_active`` from ``status``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.plan.models as plan_models
from creator.plan.ports import PlanItemRecord, PlanRecord

_INACTIVE = "INACTIVE"
_ACTIVE = "ACTIVE"


def _metadata_with(row: plan_models.Plan, **values: object) -> dict[str, object]:
    metadata = dict(row.metadata_json or {})
    metadata.update({key: value for key, value in values.items() if value is not None})
    return metadata


def _plan(row: plan_models.Plan) -> PlanRecord:
    metadata = dict(row.metadata_json or {})
    return PlanRecord(
        id=row.id,
        code=str(metadata.get("code", "")),
        type=row.type,
        name=row.name,
        description=(
            str(metadata["description"]) if metadata.get("description") is not None else None
        ),
        metadata=metadata,
        is_active=row.status == _ACTIVE,
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
        price_cents: int = 0,
        credits_per_month: int = 0,
        currency: str = "BRL",
        provider: str = "PAGARME",
        external_id: str | None = None,
    ) -> PlanRecord:
        values = dict(metadata)
        values["code"] = code
        if description is not None:
            values["description"] = description
        row = plan_models.Plan(
            name=name,
            type=type,
            provider=provider,
            external_id=external_id,
            price_cents=price_cents,
            credits_per_month=credits_per_month,
            currency=currency,
            status=_ACTIVE if is_active else _INACTIVE,
            metadata_json=values,
        )
        self._session.add(row)
        self._session.flush()
        return _plan(row)

    def update(self, *, plan_id: UUID, fields: dict[str, object]) -> PlanRecord:
        row = self._session.get(plan_models.Plan, plan_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Plan not found")
        metadata = dict(row.metadata_json or {})
        for name, value in fields.items():
            if name == "code":
                metadata["code"] = value
            elif name == "description":
                metadata["description"] = value
            elif name == "is_active":
                row.status = _ACTIVE if value else _INACTIVE
            elif name == "metadata":
                metadata.update(value if isinstance(value, dict) else {})
            elif hasattr(row, name):
                setattr(row, name, value)
        row.metadata_json = metadata
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
        deleted_at=None,
    )


class SqlAlchemyPlanItemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *, plan_id: UUID | None = None) -> list[PlanItemRecord]:
        statement = select(plan_models.PlanItem)
        if plan_id is not None:
            statement = statement.where(plan_models.PlanItem.plan_id == plan_id)
        rows = self._session.scalars(
            statement.order_by(plan_models.PlanItem.created_at.desc())
        ).all()
        return [_plan_item(row) for row in rows]

    def get(self, *, item_id: UUID) -> PlanItemRecord | None:
        row = self._session.scalars(
            select(plan_models.PlanItem).where(plan_models.PlanItem.id == item_id)
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
        provider: str = "PAGARME",
        external_id: str | None = None,
        currency: str = "BRL",
    ) -> PlanItemRecord:
        row = plan_models.PlanItem(
            plan_id=plan_id,
            provider=provider,
            external_id=external_id,
            name=name,
            description=description,
            quantity=quantity,
            cycles=cycles,
            pricing_scheme_type=pricing_scheme_type,
            price_cents=price_cents,
            currency=currency,
            price_brackets=price_brackets,
            status=(status or "ACTIVE").upper(),
        )
        self._session.add(row)
        self._session.flush()
        return _plan_item(row)

    def update(self, *, item_id: UUID, fields: dict[str, object]) -> PlanItemRecord:
        row = self._session.get(plan_models.PlanItem, item_id)
        if row is None:
            raise ValueError("Plan item not found")
        for name, value in fields.items():
            if name == "status" and value is not None:
                value = str(value).upper()
            if hasattr(row, name):
                setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _plan_item(row)

    def soft_delete(self, *, item_id: UUID) -> None:
        row = self._session.get(plan_models.PlanItem, item_id)
        if row is None:
            raise ValueError("Plan item not found")
        self._session.delete(row)
        self._session.flush()
