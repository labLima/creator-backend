"""Behaviour of the editorial expand slice (ADR-030, T10).

``posts`` owns publication/approval, ``captions`` are versioned per post,
``post_designs`` split the art format and ``design_slides`` order the copy.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base


@pytest.fixture()
def engine() -> Iterator[sa.Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def _foreign_keys(connection: object, _record: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _content_plan(connection: sa.Connection) -> str:
    user, workspace, brand, campaign, persona, plan = (uuid4() for _ in range(6))
    connection.execute(
        sa.text(
            "INSERT INTO users (id, auth_provider_id, display_name, global_role) "
            "VALUES (:id, :e, 'User', 'membro')"
        ),
        {"id": user.hex, "e": f"ext-{user}"},
    )
    connection.execute(
        sa.text("INSERT INTO workspaces (id, name) VALUES (:id, 'ws')"), {"id": workspace.hex}
    )
    connection.execute(
        sa.text(
            "INSERT INTO brands (id, workspace_id, created_by, name) VALUES (:id, :w, :u, 'brand')"
        ),
        {"id": brand.hex, "w": workspace.hex, "u": user.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO campaigns (id, brand_id, created_by, name) "
            "VALUES (:id, :b, :u, 'campaign')"
        ),
        {"id": campaign.hex, "b": brand.hex, "w": workspace.hex, "u": user.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO personas (id, brand_id, created_by, name) VALUES (:id, :b, :u, 'persona')"
        ),
        {"id": persona.hex, "b": brand.hex, "u": user.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO content_plans "
            "(id, brand_id, campaign_id, persona_id, created_by, briefing) "
            "VALUES (:id, :b, :c, :p, :u, 'briefing')"
        ),
        {
            "id": plan.hex,
            "b": brand.hex,
            "c": campaign.hex,
            "p": persona.hex,
            "u": user.hex,
        },
    )
    return plan.hex


def _post(connection: sa.Connection, plan: str, **overrides: object) -> str:
    post = uuid4().hex
    values: dict[str, object] = {"id": post, "plan": plan}
    values.update(overrides)
    connection.execute(
        sa.text(
            "INSERT INTO posts (id, content_plan_id, title, publication_status, approval_status) "
            "VALUES (:id, :plan, :title, :publication, :approval)"
        ),
        {
            "id": post,
            "plan": plan,
            "title": values.get("title", "post"),
            "publication": values.get("publication", "DRAFT"),
            "approval": values.get("approval", "PENDING"),
        },
    )
    return post


def test_posts_default_to_draft_and_pending(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        plan = _content_plan(connection)
        post = _post(connection, plan)
        row = connection.execute(
            sa.text("SELECT publication_status, approval_status FROM posts WHERE id = :id"),
            {"id": post},
        ).one()
    assert tuple(row) == ("DRAFT", "PENDING")


def test_posts_publish_requires_approval(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        plan = _content_plan(connection)
        with pytest.raises(IntegrityError) as error:
            _post(connection, plan, publication="SCHEDULED")
        assert "chk_posts" in str(error.value)


def test_posts_approval_metadata_is_consistent(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        plan = _content_plan(connection)
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text(
                    "INSERT INTO posts (id, content_plan_id, approval_status, approved_at) "
                    "VALUES (:id, :plan, 'APPROVED', CURRENT_TIMESTAMP)"
                ),
                {"id": uuid4().hex, "plan": plan},
            )
        message = str(error.value)
        assert "chk_posts_approval_pair" in message or "chk_posts_approved_metadata" in message

        approver = uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO users (id, auth_provider_id, display_name, global_role) "
                "VALUES (:id, :e, 'User', 'membro')"
            ),
            {"id": approver.hex, "e": f"ext-{approver}"},
        )
        approved = _post(connection, plan)
        connection.execute(
            sa.text(
                "UPDATE posts SET approval_status = 'APPROVED', approved_by = :user, "
                "approved_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"user": approver.hex, "id": approved},
        )
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text(
                    "UPDATE posts SET rejection_reason = NULL, "
                    "approval_status = 'REJECTED' WHERE id = :id"
                ),
                {"id": approved},
            )
        assert "chk_posts_rejected_reason" in str(error.value)


def test_captions_are_versioned_and_single_current(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        post = _post(connection, _content_plan(connection))
        statement = sa.text(
            "INSERT INTO captions (id, post_id, body, version) VALUES (:id, :post, :body, :version)"
        )
        connection.execute(statement, {"id": uuid4().hex, "post": post, "body": "v1", "version": 1})
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                statement, {"id": uuid4().hex, "post": post, "body": "v1-again", "version": 1}
            )
        assert "UNIQUE constraint failed" in str(error.value)
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                statement, {"id": uuid4().hex, "post": post, "body": "bad", "version": 0}
            )
        assert "ck_captions_version" in str(error.value)
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                statement, {"id": uuid4().hex, "post": post, "body": "v2", "version": 2}
            )
        assert "UNIQUE constraint failed: captions.post_id" in str(error.value)


def test_design_slides_are_ordered_and_tenant_scoped(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        post = _post(connection, _content_plan(connection))
        design = uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO post_designs (id, post_id, format, ratio) "
                "VALUES (:id, :post, 'STORIES', 'RATIO_9_16')"
            ),
            {"id": design, "post": post},
        )
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text(
                    "INSERT INTO post_designs (id, post_id, format, ratio) "
                    "VALUES (:id, :post, 'STORIES', 'RATIO_1_1')"
                ),
                {"id": uuid4().hex, "post": post},
            )
        assert "chk_post_designs_stories_ratio" in str(error.value)

        slide = sa.text(
            "INSERT INTO design_slides (id, post_design_id, position, art_direction) "
            "VALUES (:id, :design, :position, 'direction')"
        )
        connection.execute(slide, {"id": uuid4().hex, "design": design, "position": 0})
        with pytest.raises(IntegrityError):
            connection.execute(slide, {"id": uuid4().hex, "design": design, "position": 0})
        with pytest.raises(IntegrityError) as error:
            connection.execute(slide, {"id": uuid4().hex, "design": design, "position": -1})
        assert "ck_design_slides_position" in str(error.value)

        connection.execute(sa.text("DELETE FROM posts WHERE id = :id"), {"id": post})
        remaining = connection.execute(sa.text("SELECT COUNT(*) FROM post_designs")).scalar_one()
    assert remaining == 0
