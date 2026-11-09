"""Behaviour of the media expand slice (ADR-028, T11).

``generated_images`` only becomes current when the generation succeeded and the
row is not deleted; approval is only possible after a successful generation;
``image_resizes`` follow their source image.
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


def _slide(connection: sa.Connection) -> str:
    user, workspace, brand, campaign, persona, plan, post, design, slide = (
        uuid4() for _ in range(9)
    )
    connection.execute(
        sa.text("INSERT INTO users (id, external_id, global_role) VALUES (:id, :e, 'membro')"),
        {"id": user.hex, "e": f"ext-{user}"},
    )
    connection.execute(
        sa.text("INSERT INTO workspaces (id, name) VALUES (:id, 'ws')"), {"id": workspace.hex}
    )
    connection.execute(
        sa.text(
            "INSERT INTO brands (id, workspace_id, created_by_user_id, name, metadata) "
            "VALUES (:id, :w, :u, 'brand', '{}')"
        ),
        {"id": brand.hex, "w": workspace.hex, "u": user.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO campaigns (id, brand_id, workspace_id, created_by, name) "
            "VALUES (:id, :b, :w, :u, 'campaign')"
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
            "INSERT INTO content_plans (id, brand_id, campaign_id, persona_id, created_by) "
            "VALUES (:id, :b, :c, :p, :u)"
        ),
        {"id": plan.hex, "b": brand.hex, "c": campaign.hex, "p": persona.hex, "u": user.hex},
    )
    connection.execute(
        sa.text("INSERT INTO posts (id, content_plan_id) VALUES (:id, :plan)"),
        {"id": post.hex, "plan": plan.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO post_designs (id, post_id, format, ratio) "
            "VALUES (:id, :post, 'IMAGE', 'RATIO_1_1')"
        ),
        {"id": design.hex, "post": post.hex},
    )
    connection.execute(
        sa.text(
            "INSERT INTO design_slides (id, post_design_id, position, art_direction) "
            "VALUES (:id, :design, 0, 'direction')"
        ),
        {"id": slide.hex, "design": design.hex},
    )
    return slide.hex


def _image(connection: sa.Connection, slide: str, **overrides: object) -> str:
    image = uuid4().hex
    values: dict[str, object] = {
        "id": image,
        "slide": slide,
        "status": "GENERATING",
        "bucket": None,
        "key": None,
        "size": None,
        "width": None,
        "height": None,
        "is_current": False,
        "error": None,
    }
    values.update(overrides)
    connection.execute(
        sa.text(
            "INSERT INTO generated_images "
            "(id, design_slide_id, generation_status, storage_bucket, storage_key, "
            "size_bytes, width, height, is_current, error_message) "
            "VALUES (:id, :slide, :status, :bucket, :key, :size, :width, :height, "
            ":is_current, :error)"
        ),
        values,
    )
    return image


def _succeed(connection: sa.Connection, image: str) -> None:
    connection.execute(
        sa.text(
            "UPDATE generated_images SET generation_status = 'SUCCEEDED', "
            "storage_bucket = 'bucket', storage_key = :key, size_bytes = 100, "
            "width = 10, height = 10 WHERE id = :id"
        ),
        {"key": f"images/{image}.png", "id": image},
    )


def test_success_requires_complete_file_metadata(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        slide = _slide(connection)
        image = _image(connection, slide)
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text(
                    "UPDATE generated_images SET generation_status = 'SUCCEEDED' WHERE id = :id"
                ),
                {"id": image},
            )
        assert "chk_generated_images_file_by_status" in str(error.value)
        _succeed(connection, image)


def test_failure_requires_error_message(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        image = _image(connection, _slide(connection))
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text("UPDATE generated_images SET generation_status = 'FAILED' WHERE id = :id"),
                {"id": image},
            )
        assert "chk_generated_images_failed_message" in str(error.value)


def test_only_one_current_image_per_slide(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        slide = _slide(connection)
        first, second = _image(connection, slide), _image(connection, slide)
        _succeed(connection, first)
        _succeed(connection, second)
        connection.execute(
            sa.text("UPDATE generated_images SET is_current = true WHERE id = :id"),
            {"id": first},
        )
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text("UPDATE generated_images SET is_current = true WHERE id = :id"),
                {"id": second},
            )
        assert "uq_generated_images_current_per_slide" in str(error.value) or (
            "UNIQUE constraint failed: generated_images.design_slide_id" in str(error.value)
        )


def test_current_requires_a_successful_generation(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        image = _image(connection, _slide(connection))
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text("UPDATE generated_images SET is_current = true WHERE id = :id"),
                {"id": image},
            )
        assert "chk_generated_images_current_complete" in str(error.value)


def test_approval_requires_a_successful_generation(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        slide = _slide(connection)
        approver = uuid4()
        connection.execute(
            sa.text("INSERT INTO users (id, external_id, global_role) VALUES (:id, :e, 'membro')"),
            {"id": approver.hex, "e": f"ext-{approver}"},
        )
        image = _image(connection, slide)
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text(
                    "UPDATE generated_images SET approval_status = 'APPROVED', "
                    "approved_by = :user, approved_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                {"user": approver.hex, "id": image},
            )
        message = str(error.value)
        assert "chk_generated_images_approval_after_generation" in message or (
            "chk_generated_images_approved_metadata" in message
        )

        _succeed(connection, image)
        connection.execute(
            sa.text(
                "UPDATE generated_images SET approval_status = 'APPROVED', "
                "approved_by = :user, approved_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"user": approver.hex, "id": image},
        )


def test_resizes_follow_the_image_and_validate_their_state(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        slide = _slide(connection)
        image = _image(connection, slide)
        _succeed(connection, image)
        resize = uuid4().hex
        statement = sa.text(
            "INSERT INTO image_resizes "
            "(id, source_image_id, ratio, status, storage_bucket, storage_key, "
            "size_bytes, width, height, error_message) "
            "VALUES (:id, :source, 'RATIO_9_16', :status, :bucket, :key, :size, "
            ":width, :height, :error)"
        )
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                statement,
                {
                    "id": resize,
                    "source": image,
                    "status": "SUCCEEDED",
                    "bucket": None,
                    "key": None,
                    "size": None,
                    "width": None,
                    "height": None,
                    "error": None,
                },
            )
        assert "chk_image_resizes_file" in str(error.value)
        connection.execute(
            statement,
            {
                "id": resize,
                "source": image,
                "status": "SUCCEEDED",
                "bucket": "bucket",
                "key": "resizes/1.png",
                "size": 10,
                "width": 9,
                "height": 16,
                "error": None,
            },
        )
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                statement,
                {
                    "id": uuid4().hex,
                    "source": image,
                    "status": "FAILED",
                    "bucket": None,
                    "key": None,
                    "size": None,
                    "width": None,
                    "height": None,
                    "error": None,
                },
            )
        assert "chk_image_resizes_failed" in str(error.value)

        connection.execute(sa.text("DELETE FROM generated_images WHERE id = :id"), {"id": image})
        remaining = connection.execute(sa.text("SELECT COUNT(*) FROM image_resizes")).scalar_one()
    assert remaining == 0
