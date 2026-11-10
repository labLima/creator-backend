"""Consumers of design_structure/generated_image read the final tables.

T23 third slice: the design_structure and generated-images endpoints keep their
records while reading ``post_designs`` and ``generated_images``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Session

from creator.brand.models import Brand
from creator.campaign.models import Campaign
from creator.content_plan.models import ContentPlan
from creator.design_structure.repository import SqlAlchemyDesignStructureRepository
from creator.generation.repository import SqlAlchemyGeneratedImageRepository
from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.enums import WorkspaceRole
from creator.media.models import GeneratedImage
from creator.persona.models import Persona
from creator.post.models import DesignSlide, Post, PostDesign
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
    )
    session.add(plan)
    session.flush()
    post = Post(content_plan_id=plan.id, created_by=user_id)
    session.add(post)
    session.flush()
    design = PostDesign(post_id=post.id, format="IMAGE", ratio="RATIO_1_1")
    session.add(design)
    session.flush()
    slide = DesignSlide(post_design_id=design.id, position=0, art_direction="Warm")
    session.add(slide)
    session.flush()
    return {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "design_id": design.id,
        "slide_id": slide.id,
    }


def test_design_structure_reads_post_designs() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ids = _seed(session)
        repository = SqlAlchemyDesignStructureRepository(session)
        listed = repository.list_for_user(user_id=ids["user_id"])
        assert [row.id for row in listed] == [ids["design_id"]]
        found = repository.get_for_user(user_id=ids["user_id"], design_id=ids["design_id"])
        assert found is not None
        assert found.post_structure_id == session.get(PostDesign, ids["design_id"]).post_id
        created = repository.add(post_structure_id=found.post_structure_id)
        assert created.id == ids["design_id"]
    engine.dispose()


def test_generated_image_reads_final_media_table() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        ids = _seed(session)
        image = GeneratedImage(
            design_slide_id=ids["slide_id"],
            storage_bucket="assets",
            storage_key="renders/hero.png",
            size_bytes=1234,
            width=1080,
            height=1080,
            generation_status="SUCCEEDED",
            is_current=True,
        )
        session.add(image)
        session.flush()

        repository = SqlAlchemyGeneratedImageRepository(session)
        record = repository.get_for_user(user_id=ids["user_id"], image_id=image.id)
        assert record is not None
        assert record.workspace_id == ids["workspace_id"]
        assert record.design_structure_id == ids["design_id"]
        assert record.signed_url == "storage://assets/renders/hero.png"
        assert record.size == "1234"
        assert record.resolution == "1080x1080"
        assert record.image_ratio == "1:1"
        assert record.status == "SUCCEEDED"
    engine.dispose()
