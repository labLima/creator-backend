"""Backfill of the four redesigned models (ADR-028, T12).

The script must copy the legacy rows with their identifiers preserved, satisfy
the final-modeling constraints, skip what cannot be mapped and be idempotent.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa

from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import backfill_redesigns  # noqa: E402


@pytest.fixture()
def database(tmp_path: Path) -> Iterator[tuple[str, sa.Engine]]:
    path = tmp_path / "backfill.db"
    url = f"sqlite+pysqlite:///{path}"
    engine = sa.create_engine(url)
    Base.metadata.create_all(engine)
    yield url, engine
    engine.dispose()


def _seed(engine: sa.Engine) -> dict[str, object]:
    ids = {name: uuid4() for name in ("user", "workspace", "brand", "campaign", "persona")}
    ids.update({name: uuid4() for name in ("planning", "post", "design", "image")})
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO users (id, auth_provider_id, display_name, global_role) "
                "VALUES (:id, :e, 'User', 'membro')"
            ),
            {"id": ids["user"].hex, "e": f"ext-{ids['user']}"},
        )
        connection.execute(
            sa.text("INSERT INTO workspaces (id, name) VALUES (:id, 'ws')"),
            {"id": ids["workspace"].hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO brands (id, workspace_id, created_by_user_id, name, metadata) "
                "VALUES (:id, :w, :u, 'brand', '{}')"
            ),
            {"id": ids["brand"].hex, "w": ids["workspace"].hex, "u": ids["user"].hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO campaigns (id, workspace_id, created_by, name) "
                "VALUES (:id, :w, :u, 'campaign')"
            ),
            {"id": ids["campaign"].hex, "w": ids["workspace"].hex, "u": ids["user"].hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO personas (id, brand_id, created_by, name) "
                "VALUES (:id, :b, :u, 'persona')"
            ),
            {"id": ids["persona"].hex, "b": ids["brand"].hex, "u": ids["user"].hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO planning "
                "(id, brand_id, campaign_id, persona_id, created_by, planning_info, "
                "planning_static_amount, planning_carousel_amount, "
                "planning_special_dates, planning_start_period, planning_end_period) "
                "VALUES (:id, :b, :c, :p, :u, 'briefing', 2, 1, '2026-05-10', "
                "'2026-01-01', '2026-02-01')"
            ),
            {
                "id": ids["planning"].hex,
                "b": ids["brand"].hex,
                "c": ids["campaign"].hex,
                "p": ids["persona"].hex,
                "u": ids["user"].hex,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO post_structure "
                "(id, workspace_id, planning_id, created_by, post_title, post_headline, "
                "image_cta, art_guiding, content_format, art_ratio) "
                "VALUES (:id, :w, :p, :u, 'title', 'headline', 'cta', 'guiding', "
                "'IMAGE', 'RATIO_1_1')"
            ),
            {
                "id": ids["post"].hex,
                "w": ids["workspace"].hex,
                "p": ids["planning"].hex,
                "u": ids["user"].hex,
            },
        )
        connection.execute(
            sa.text("INSERT INTO design_structure (id, post_structure_id) VALUES (:id, :post)"),
            {"id": ids["design"].hex, "post": ids["post"].hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO generated_image "
                "(id, workspace_id, design_structure_id, signed_url, size, resolution, "
                "image_status) "
                "VALUES (:id, :w, :d, 'https://storage/image.png', '12345', "
                "'1024x1024', 'SUCCESS')"
            ),
            {
                "id": ids["image"].hex,
                "w": ids["workspace"].hex,
                "d": ids["design"].hex,
            },
        )
    return ids


def test_backfill_preserves_ids_and_is_idempotent(database: tuple[str, sa.Engine]) -> None:
    url, engine = database
    ids = _seed(engine)

    first = backfill_redesigns.run(url)
    assert first["campaigns.brand_id"] == 1
    assert first["content_plans"] == 1
    assert first["content_plan_items"] == 2
    assert first["content_plan_special_dates"] == 1
    assert first["posts"] == 1
    assert first["post_designs_from_posts"] == 1
    assert first["post_designs_from_designs"] == 1
    assert first["design_slides"] == 1
    assert first["generated_images"] == 1

    with engine.begin() as connection:
        campaign = connection.execute(sa.text("SELECT brand_id FROM campaigns")).scalar_one()
        plan = connection.execute(
            sa.text("SELECT briefing, start_date, end_date FROM content_plans")
        ).one()
        post = connection.execute(sa.text("SELECT content_plan_id FROM posts")).scalar_one()
        slide = connection.execute(
            sa.text("SELECT headline, cta, art_direction FROM design_slides")
        ).one()
        image = connection.execute(
            sa.text(
                "SELECT generation_status, storage_bucket, storage_key, size_bytes, "
                "width, height, is_current FROM generated_images"
            )
        ).one()

    assert campaign == ids["brand"].hex.replace("-", "")
    assert tuple(plan) == ("briefing", "2026-01-01", "2026-02-01")
    assert post == ids["planning"].hex.replace("-", "")
    assert tuple(slide) == ("headline", "cta", "guiding")
    assert tuple(image) == (
        "SUCCEEDED",
        "legacy",
        "https://storage/image.png",
        12345,
        1024,
        1024,
        0,
    )

    second = backfill_redesigns.run(url)
    assert sum(second.values()) == 0, second


def test_backfill_skips_unmappable_rows_and_flags_broken_images(
    database: tuple[str, sa.Engine],
) -> None:
    url, engine = database
    ids = _seed(engine)
    other_brand = uuid4()
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO brands (id, workspace_id, created_by_user_id, name, metadata) "
                "VALUES (:id, :w, :u, 'other', '{}')"
            ),
            {"id": other_brand.hex, "w": ids["workspace"].hex, "u": ids["user"].hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO planning "
                "(id, brand_id, campaign_id, persona_id, created_by) "
                "VALUES (:id, :b, :c, :p, :u)"
            ),
            {
                "id": uuid4().hex,
                "b": other_brand.hex,
                "c": ids["campaign"].hex,
                "p": ids["persona"].hex,
                "u": ids["user"].hex,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO generated_image "
                "(id, workspace_id, design_structure_id, image_status) "
                "VALUES (:id, :w, :d, 'SUCCESS')"
            ),
            {"id": uuid4().hex, "w": ids["workspace"].hex, "d": ids["design"].hex},
        )

    report = backfill_redesigns.run(url)
    assert report["content_plans"] == 1
    # The legacy row without file metadata is kept but marked FAILED, so the
    # final-modeling constraint is satisfied instead of being violated.
    assert report["generated_images"] == 2

    with engine.begin() as connection:
        statuses = {
            row[0]
            for row in connection.execute(sa.text("SELECT generation_status FROM generated_images"))
        }
        broken = connection.execute(
            sa.text("SELECT error_message FROM generated_images WHERE generation_status = 'FAILED'")
        ).scalar_one()
    assert statuses == {"SUCCEEDED", "FAILED"}
    assert broken == "legacy image metadata incomplete"


def test_dry_run_writes_nothing(database: tuple[str, sa.Engine]) -> None:
    url, engine = database
    _seed(engine)
    backfill_redesigns.run(url, dry_run=True)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT COUNT(*) FROM content_plans")).scalar_one() == 0
