"""SQLAlchemy implementation of the planning persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.campaign.models as campaign_models
import creator.persona.models as persona_models
import creator.planning.models as planning_models
import creator.workspace.models as workspace_models
from creator.core.pagination import Page, PageRequest
from creator.planning.ports import PlanningRecord


def _planning_record(row: planning_models.Planning) -> PlanningRecord:
    return PlanningRecord(
        id=row.id,
        brand_id=row.brand_id,
        campaign_id=row.campaign_id,
        persona_id=row.persona_id,
        created_by=row.created_by,
        info=row.planning_info,
        static_amount=row.planning_static_amount,
        carousel_amount=row.planning_carousel_amount,
        stories_amount=row.planning_stories_amount,
        special_dates=row.planning_special_dates,
        start_period=row.planning_start_period,
        end_period=row.planning_end_period,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyPlanningRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, created_by: UUID, **fields: object) -> PlanningRecord:
        persona = self._session.get(persona_models.Persona, fields["persona_id"])
        if persona is None or persona.deleted_at is not None:
            raise ValueError("Persona does not exist")
        campaign = self._session.get(campaign_models.Campaign, fields["campaign_id"])
        if campaign is None or campaign.deleted_at is not None:
            raise ValueError("Campaign does not exist")
        if persona.brand_id != fields["brand_id"]:
            raise ValueError("Persona and planning brand do not match")
        brand = self._session.get(brand_models.Brand, fields["brand_id"])
        if (
            brand is None
            or brand.deleted_at is not None
            or brand.workspace_id != campaign.workspace_id
        ):
            raise ValueError("Brand and campaign workspace do not match")
        fields = {"planning_info" if key == "info" else key: value for key, value in fields.items()}
        fields = {
            {
                "static_amount": "planning_static_amount",
                "carousel_amount": "planning_carousel_amount",
                "stories_amount": "planning_stories_amount",
                "special_dates": "planning_special_dates",
                "start_period": "planning_start_period",
                "end_period": "planning_end_period",
            }.get(key, key): value
            for key, value in fields.items()
        }
        fields.update(
            {
                "persona_name": persona.name,
                "persona_age": persona.age,
                "persona_gender": persona.gender,
                "persona_main_goal": persona.main_goal,
                "persona_challenge": persona.challenge,
                "persona_interest": persona.interest,
                "persona_routine": persona.routine,
                "persona_journey": persona.journey,
                "persona_trigger": persona.trigger,
            }
        )
        row = planning_models.Planning(created_by=created_by, **fields)
        self._session.add(row)
        self._session.flush()
        return _planning_record(row)

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
            .select_from(planning_models.Planning)
            .join(
                campaign_models.Campaign,
                campaign_models.Campaign.id == planning_models.Planning.campaign_id,
            )
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == campaign_models.Campaign.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                planning_models.Planning.deleted_at.is_(None),
                campaign_models.Campaign.deleted_at.is_(None),
            )
        )
        if campaign_id is not None:
            statement = statement.where(planning_models.Planning.campaign_id == campaign_id)
            count = count.where(planning_models.Planning.campaign_id == campaign_id)
        order = (
            asc(planning_models.Planning.created_at)
            if page.sort == "asc"
            else desc(planning_models.Planning.created_at)
        )
        rows = self._session.scalars(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        return Page(
            items=[_planning_record(row) for row in rows],
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def get_for_user(self, *, user_id: UUID, planning_id: UUID) -> PlanningRecord | None:
        row = self._session.scalars(
            self._select(user_id).where(planning_models.Planning.id == planning_id)
        ).one_or_none()
        return _planning_record(row) if row else None

    def update(self, *, planning_id: UUID, fields: dict[str, object]) -> PlanningRecord:
        row = self._session.get(planning_models.Planning, planning_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Planning not found")
        mapping = {
            "info": "planning_info",
            "static_amount": "planning_static_amount",
            "carousel_amount": "planning_carousel_amount",
            "stories_amount": "planning_stories_amount",
            "special_dates": "planning_special_dates",
            "start_period": "planning_start_period",
            "end_period": "planning_end_period",
        }
        for name, value in fields.items():
            setattr(row, mapping.get(name, name), value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _planning_record(row)

    def soft_delete(self, *, planning_id: UUID) -> None:
        row = self._session.get(planning_models.Planning, planning_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Planning not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()

    def _select(self, user_id: UUID) -> Select[planning_models.Planning]:
        return (
            select(planning_models.Planning)
            .join(
                campaign_models.Campaign,
                campaign_models.Campaign.id == planning_models.Planning.campaign_id,
            )
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == campaign_models.Campaign.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                planning_models.Planning.deleted_at.is_(None),
                campaign_models.Campaign.deleted_at.is_(None),
            )
        )
