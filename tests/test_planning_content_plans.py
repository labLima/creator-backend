"""The planning API persists in ``content_plans``, not in the legacy table.

T23 first slice: the repository keeps the HTTP record stable while writing
``content_plans``, ``content_plan_items`` and ``content_plan_special_dates``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session

from creator.brand.models import Brand
from creator.campaign.models import Campaign
from creator.content_plan.models import ContentPlan, ContentPlanItem, ContentPlanSpecialDate
from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.enums import WorkspaceRole
from creator.persona.models import Persona
from creator.planning.repository import SqlAlchemyPlanningRepository
from creator.user.models import User
from creator.workspace.models import Workspace, WorkspaceMembership


def _seed(session: Session) -> dict[str, UUID]:
    workspace_id, user_id, brand_id, campaign_id, persona_id = (uuid4() for _ in range(5))
    session.add(Workspace(id=workspace_id, name="ws"))
    session.add(User(id=user_id, auth_provider_id=None, display_name="User", global_role="membro"))
    session.flush()
    session.add(
        WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=user_id,
            role=WorkspaceRole.OWNER,
            status="ACTIVE",
        )
    )
    session.add(Brand(id=brand_id, workspace_id=workspace_id, created_by=user_id, name="Brand"))
    session.flush()
    session.add(
        Campaign(
            id=campaign_id,
            brand_id=brand_id,
            created_by=user_id,
            name="Campaign",
        )
    )
    session.add(Persona(id=persona_id, brand_id=brand_id, created_by=user_id, name="Persona"))
    session.flush()
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "brand_id": brand_id,
        "campaign_id": campaign_id,
        "persona_id": persona_id,
    }


def test_planning_add_reads_and_writes_content_plans() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ids = _seed(session)
        repository = SqlAlchemyPlanningRepository(session)
        created = repository.add(
            created_by=ids["user_id"],
            brand_id=ids["brand_id"],
            campaign_id=ids["campaign_id"],
            persona_id=ids["persona_id"],
            info="Launch plan",
            static_amount=2,
            carousel_amount=1,
            stories_amount=None,
            special_dates="2026-12-25",
            start_period=datetime(2026, 12, 1, tzinfo=UTC),
            end_period=datetime(2027, 1, 1, tzinfo=UTC),
        )
        session.flush()

        assert "planning" not in Base.metadata.tables
        assert session.scalar(sa.select(sa.func.count()).select_from(ContentPlan)) == 1
        plan = session.scalars(sa.select(ContentPlan)).one()
        assert plan.id == created.id
        assert plan.briefing == "Launch plan"
        assert plan.start_date.isoformat() == "2026-12-01"
        items = {item.format: item.quantity for item in session.scalars(sa.select(ContentPlanItem))}
        assert items == {"IMAGE": 2, "CAROUSEL": 1}
        special = session.scalars(sa.select(ContentPlanSpecialDate)).one()
        assert special.special_date.isoformat() == "2026-12-25"

        fetched = repository.get_for_user(user_id=ids["user_id"], planning_id=created.id)
        assert fetched is not None
        assert fetched.info == "Launch plan"
        assert fetched.static_amount == 2
        assert fetched.carousel_amount == 1
        assert fetched.special_dates == "2026-12-25"

        updated = repository.update(
            planning_id=created.id,
            fields={
                "info": "Updated plan",
                "static_amount": 5,
                "stories_amount": 3,
                "special_dates": "Valentine",
            },
        )
        assert updated.info == "Updated plan"
        assert updated.static_amount == 5
        assert updated.stories_amount == 3
        assert updated.special_dates == "Valentine"
        quantities = {
            item.format: item.quantity for item in session.scalars(sa.select(ContentPlanItem))
        }
        assert quantities == {"IMAGE": 5, "CAROUSEL": 1, "STORIES": 3}

        page = repository.list_for_user(user_id=ids["user_id"])
        assert page.total == 1
        repository.soft_delete(planning_id=created.id)
        assert session.get(ContentPlan, created.id).deleted_at is not None
    engine.dispose()
