"""The post_structure API persists in posts/post_designs/design_slides.

T23 second slice: the legacy flat table is no longer written while the HTTP
record keeps its former fields.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session

from creator.brand.models import Brand
from creator.campaign.models import Campaign
from creator.content_plan.models import ContentPlan
from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.enums import WorkspaceRole
from creator.persona.models import Persona
from creator.post.models import DesignSlide, Post, PostDesign
from creator.post_structure.models import PostStructure
from creator.post_structure.repository import SqlAlchemyPostStructureRepository
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
    session.add(Campaign(id=campaign_id, brand_id=brand_id, created_by=user_id, name="Campaign"))
    session.add(Persona(id=persona_id, brand_id=brand_id, created_by=user_id, name="Persona"))
    session.flush()
    plan = ContentPlan(
        brand_id=brand_id,
        campaign_id=campaign_id,
        persona_id=persona_id,
        created_by=user_id,
        briefing="Plan",
    )
    session.add(plan)
    session.flush()
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "plan_id": plan.id,
    }


def test_post_structure_add_reads_and_writes_editorial_tables() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ids = _seed(session)
        repository = SqlAlchemyPostStructureRepository(session)
        created = repository.add(
            workspace_id=ids["workspace_id"],
            planning_id=ids["plan_id"],
            created_by=ids["user_id"],
            title="Hero post",
            objective="Awareness",
            big_idea="A brighter morning",
            main_message="Fresh start",
            headline="Good morning",
            image_cta="Discover",
            art_guiding="Warm sunrise",
            format="STATIC",
            ratio="1:1",
            resolution="1080x1080",
        )
        session.flush()

        assert session.scalar(sa.select(sa.func.count()).select_from(PostStructure)) == 0
        assert session.scalar(sa.select(sa.func.count()).select_from(Post)) == 1
        assert session.scalar(sa.select(sa.func.count()).select_from(PostDesign)) == 1
        slide = session.scalars(sa.select(DesignSlide)).one()
        assert slide.headline == "Good morning"
        assert slide.cta == "Discover"
        assert slide.art_direction == "Warm sunrise"

        assert created.planning_id == ids["plan_id"]
        assert created.workspace_id == ids["workspace_id"]
        assert created.format == "IMAGE"
        assert created.ratio == "RATIO_1_1"
        assert created.resolution == "1080x1080"
        assert created.status == "DRAFT"

        updated = repository.update(
            post_structure_id=created.id,
            fields={"title": "Updated", "status": "PUBLISHED", "headline": "New headline"},
        )
        assert updated is not None
        assert updated.title == "Updated"
        assert updated.status == "PUBLISHED"
        assert updated.headline == "New headline"
        post = session.get(Post, created.id)
        assert post.published_at is not None

        fetched = repository.get_for_user(user_id=ids["user_id"], post_structure_id=created.id)
        assert fetched is not None and fetched.title == "Updated"
        page = repository.list_for_user(user_id=ids["user_id"], workspace_id=ids["workspace_id"])
        assert page.total == 1
        assert repository.soft_delete(post_structure_id=created.id) is True
        assert session.get(Post, created.id).deleted_at is not None
    engine.dispose()
