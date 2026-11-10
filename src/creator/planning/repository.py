"""SQLAlchemy implementation of the planning persistence ports.

The legacy ``planning`` table is still present until the contract step (T13),
but this repository already reads and writes the final modeling:
``content_plans`` plus ``content_plan_items`` and ``content_plan_special_dates``.
The HTTP record is kept stable by mapping the quantities and the free-form
special-date text back and forth.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.campaign.models as campaign_models
import creator.content_plan.models as content_plan_models
import creator.persona.models as persona_models
import creator.workspace.models as workspace_models
from creator.core.pagination import Page, PageRequest
from creator.planning.ports import PlanningRecord

_FORMAT_BY_FIELD = {
    "static_amount": "IMAGE",
    "carousel_amount": "CAROUSEL",
    "stories_amount": "STORIES",
}
_FIELD_BY_FORMAT = {value: key for key, value in _FORMAT_BY_FIELD.items()}


def _period_date(value: datetime | None) -> date | None:
    return value.date() if value is not None else None


def _parse_special_date(value: str, fallback: date | None) -> date:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return fallback or date.today()


def _special_text(values: list[str]) -> str | None:
    return ", ".join(values) if values else None


class SqlAlchemyPlanningRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, created_by: UUID | None, **fields: object) -> PlanningRecord:
        persona = self._session.get(persona_models.Persona, fields["persona_id"])
        if persona is None or persona.deleted_at is not None:
            raise ValueError("Persona does not exist")
        campaign = self._session.get(campaign_models.Campaign, fields["campaign_id"])
        if campaign is None or campaign.deleted_at is not None:
            raise ValueError("Campaign does not exist")
        if persona.brand_id != fields["brand_id"]:
            raise ValueError("Persona and planning brand do not match")
        brand = self._session.get(brand_models.Brand, fields["brand_id"])
        if brand is None or brand.deleted_at is not None or campaign.brand_id != brand.id:
            raise ValueError("Brand and campaign workspace do not match")

        start_period = fields.pop("start_period", None)
        end_period = fields.pop("end_period", None)
        start_date = _period_date(start_period if isinstance(start_period, datetime) else None)
        end_date = _period_date(end_period if isinstance(end_period, datetime) else None)
        special_text = fields.pop("special_dates", None)
        amounts = {key: fields.pop(key, None) for key in _FORMAT_BY_FIELD}
        row = content_plan_models.ContentPlan(
            brand_id=fields["brand_id"],
            campaign_id=fields["campaign_id"],
            persona_id=fields["persona_id"],
            created_by=created_by,
            briefing=fields.get("info"),
            start_date=start_date,
            end_date=end_date,
        )
        self._session.add(row)
        self._session.flush()

        for field_name, format_name in _FORMAT_BY_FIELD.items():
            amount = amounts[field_name]
            if amount is not None:
                self._session.add(
                    content_plan_models.ContentPlanItem(
                        content_plan_id=row.id,
                        format=format_name,
                        quantity=int(str(amount)),
                    )
                )
        if special_text:
            self._session.add(
                content_plan_models.ContentPlanSpecialDate(
                    content_plan_id=row.id,
                    special_date=_parse_special_date(str(special_text), start_date),
                    label=str(special_text)[:50],
                )
            )
        self._session.flush()
        return self._record(row)

    def list_for_user(
        self,
        *,
        user_id: UUID,
        campaign_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[PlanningRecord]:
        page = page or PageRequest()
        statement = self._select(user_id)
        count = (
            select(func.count())
            .select_from(content_plan_models.ContentPlan)
            .join(
                campaign_models.Campaign,
                campaign_models.Campaign.id == content_plan_models.ContentPlan.campaign_id,
            )
            .join(
                brand_models.Brand,
                brand_models.Brand.id == content_plan_models.ContentPlan.brand_id,
            )
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.Brand.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                content_plan_models.ContentPlan.deleted_at.is_(None),
                campaign_models.Campaign.deleted_at.is_(None),
            )
        )
        if campaign_id is not None:
            statement = statement.where(content_plan_models.ContentPlan.campaign_id == campaign_id)
            count = count.where(content_plan_models.ContentPlan.campaign_id == campaign_id)
        order = (
            asc(content_plan_models.ContentPlan.created_at)
            if page.sort == "asc"
            else desc(content_plan_models.ContentPlan.created_at)
        )
        rows = self._session.scalars(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        records = self._records(list(rows))
        return Page(
            items=records,
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def get_for_user(self, *, user_id: UUID, planning_id: UUID) -> PlanningRecord | None:
        row = self._session.scalars(
            self._select(user_id).where(content_plan_models.ContentPlan.id == planning_id)
        ).one_or_none()
        return self._record(row) if row else None

    def update(self, *, planning_id: UUID, fields: dict[str, object]) -> PlanningRecord:
        row = self._session.get(content_plan_models.ContentPlan, planning_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Planning not found")

        if "info" in fields:
            row.briefing = str(fields["info"]) if fields["info"] is not None else None
        if "start_period" in fields:
            value = fields["start_period"]
            row.start_date = _period_date(value if isinstance(value, datetime) else None)
        if "end_period" in fields:
            value = fields["end_period"]
            row.end_date = _period_date(value if isinstance(value, datetime) else None)
        if "special_dates" in fields:
            self._session.query(content_plan_models.ContentPlanSpecialDate).filter(
                content_plan_models.ContentPlanSpecialDate.content_plan_id == row.id
            ).delete(synchronize_session=False)
            special_text = fields["special_dates"]
            if special_text:
                self._session.add(
                    content_plan_models.ContentPlanSpecialDate(
                        content_plan_id=row.id,
                        special_date=_parse_special_date(str(special_text), row.start_date),
                        label=str(special_text)[:50],
                    )
                )
        for field_name, format_name in _FORMAT_BY_FIELD.items():
            if field_name not in fields:
                continue
            amount = fields[field_name]
            item = self._session.scalar(
                select(content_plan_models.ContentPlanItem).where(
                    content_plan_models.ContentPlanItem.content_plan_id == row.id,
                    content_plan_models.ContentPlanItem.format == format_name,
                )
            )
            if amount is None:
                if item is not None:
                    self._session.delete(item)
            elif item is None:
                self._session.add(
                    content_plan_models.ContentPlanItem(
                        content_plan_id=row.id,
                        format=format_name,
                        quantity=int(str(amount)),
                    )
                )
            else:
                item.quantity = int(str(amount))
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return self._record(row)

    def soft_delete(self, *, planning_id: UUID) -> None:
        row = self._session.get(content_plan_models.ContentPlan, planning_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Planning not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()

    def _select(self, user_id: UUID) -> Select[content_plan_models.ContentPlan]:
        return (
            select(content_plan_models.ContentPlan)
            .join(
                campaign_models.Campaign,
                campaign_models.Campaign.id == content_plan_models.ContentPlan.campaign_id,
            )
            .join(
                brand_models.Brand,
                brand_models.Brand.id == content_plan_models.ContentPlan.brand_id,
            )
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.Brand.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                content_plan_models.ContentPlan.deleted_at.is_(None),
                campaign_models.Campaign.deleted_at.is_(None),
            )
        )

    def _record(self, row: content_plan_models.ContentPlan) -> PlanningRecord:
        return self._records([row])[0]

    def _records(self, rows: list[content_plan_models.ContentPlan]) -> list[PlanningRecord]:
        if not rows:
            return []
        ids = [row.id for row in rows]
        amounts: dict[UUID, dict[str, int]] = defaultdict(dict)
        for item in self._session.scalars(
            select(content_plan_models.ContentPlanItem).where(
                content_plan_models.ContentPlanItem.content_plan_id.in_(ids)
            )
        ):
            field_name = _FIELD_BY_FORMAT.get(item.format)
            if field_name is not None:
                amounts[item.content_plan_id][field_name] = item.quantity
        specials: dict[UUID, list[str]] = defaultdict(list)
        for special in self._session.scalars(
            select(content_plan_models.ContentPlanSpecialDate)
            .where(content_plan_models.ContentPlanSpecialDate.content_plan_id.in_(ids))
            .order_by(content_plan_models.ContentPlanSpecialDate.special_date)
        ):
            if special.label:
                specials[special.content_plan_id].append(special.label)
        return [
            PlanningRecord(
                id=row.id,
                brand_id=row.brand_id,
                campaign_id=row.campaign_id,
                persona_id=row.persona_id,
                created_by=row.created_by,
                info=row.briefing,
                static_amount=amounts[row.id].get("static_amount"),
                carousel_amount=amounts[row.id].get("carousel_amount"),
                stories_amount=amounts[row.id].get("stories_amount"),
                special_dates=_special_text(specials[row.id]),
                start_period=(
                    datetime.combine(row.start_date, datetime.min.time(), tzinfo=UTC)
                    if row.start_date
                    else None
                ),
                end_period=(
                    datetime.combine(row.end_date, datetime.min.time(), tzinfo=UTC)
                    if row.end_date
                    else None
                ),
                created_at=row.created_at,
                updated_at=row.updated_at,
                deleted_at=row.deleted_at,
            )
            for row in rows
        ]
