#!/usr/bin/env python3
"""Backfill the four redesigned models from their legacy tables (ADR-028, T12).

The legacy rows are copied with their identifiers preserved, so the mapping is
direct (``planning.id`` becomes ``content_plans.id``, and so on) and reruns are
idempotent through ``INSERT OR IGNORE`` plus the natural keys.

Order matters:

1. ``campaigns.brand_id`` is filled from ``planning`` because the composite
   foreign keys of ``content_plans`` require the campaign to carry the brand;
2. ``content_plans`` and its items/dates from ``planning``;
3. ``posts`` from ``post_structure``;
4. ``post_designs`` from ``post_structure`` and ``design_structure``;
5. ``design_slides`` from ``design_structure`` (using the parent art fields);
6. ``generated_images`` from ``generated_image``.

Rows that cannot satisfy the final-modeling constraints are skipped and counted
in the report instead of aborting the whole migration.

Usage:
    python scripts/backfill_redesigns.py [--database-url URL] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import sqlalchemy as sa

ROOT = Path(__file__).resolve().parents[1]

CONTENT_FORMATS = ("IMAGE", "CAROUSEL", "STORIES")
ART_RATIOS = ("RATIO_4_5", "RATIO_1_1", "RATIO_9_16", "RATIO_16_9")
ART_RATIO_9_16 = "RATIO_9_16"

STEPS: tuple[tuple[str, str], ...] = (
    (
        "campaigns.brand_id",
        """
        UPDATE campaigns
        SET brand_id = (
            SELECT p.brand_id FROM planning p
            WHERE p.campaign_id = campaigns.id AND p.deleted_at IS NULL
            LIMIT 1
        )
        WHERE campaigns.brand_id IS NULL
          AND EXISTS (
            SELECT 1 FROM planning p
            WHERE p.campaign_id = campaigns.id AND p.deleted_at IS NULL
          )
        """,
    ),
    (
        "content_plans",
        """
        INSERT OR IGNORE INTO content_plans
            (id, brand_id, campaign_id, persona_id, created_by, briefing,
             start_date, end_date, created_at, updated_at, deleted_at)
        SELECT p.id, p.brand_id, p.campaign_id, p.persona_id, p.created_by,
               p.planning_info, date(p.planning_start_period),
               date(p.planning_end_period), p.created_at, p.updated_at, p.deleted_at
        FROM planning p
        WHERE p.deleted_at IS NULL
          AND EXISTS (
            SELECT 1 FROM campaigns c
            WHERE c.id = p.campaign_id AND c.brand_id = p.brand_id
          )
          AND EXISTS (
            SELECT 1 FROM personas pe
            WHERE pe.id = p.persona_id AND pe.brand_id = p.brand_id
          )
        """,
    ),
    (
        "content_plan_items",
        """
        INSERT OR IGNORE INTO content_plan_items
            (id, content_plan_id, format, quantity, created_at, updated_at)
        SELECT lower(hex(randomblob(16))), src.plan_id, src.format, src.quantity,
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM (
            SELECT p.id AS plan_id, 'IMAGE' AS format, p.planning_static_amount AS quantity
            FROM planning p WHERE p.planning_static_amount > 0
            UNION ALL
            SELECT p.id, 'CAROUSEL', p.planning_carousel_amount
            FROM planning p WHERE p.planning_carousel_amount > 0
            UNION ALL
            SELECT p.id, 'STORIES', p.planning_stories_amount
            FROM planning p WHERE p.planning_stories_amount > 0
        ) AS src
        WHERE EXISTS (SELECT 1 FROM content_plans cp WHERE cp.id = src.plan_id)
        """,
    ),
    (
        "content_plan_special_dates",
        """
        INSERT OR IGNORE INTO content_plan_special_dates
            (id, content_plan_id, special_date, label, created_at, updated_at)
        SELECT lower(hex(randomblob(16))), p.id, date(p.planning_special_dates),
               'legacy', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM planning p
        WHERE date(p.planning_special_dates) IS NOT NULL
          AND EXISTS (SELECT 1 FROM content_plans cp WHERE cp.id = p.id)
        """,
    ),
    (
        "posts",
        """
        INSERT OR IGNORE INTO posts
            (id, content_plan_id, created_by, title, objective, big_idea,
             main_message, publication_status, approval_status,
             created_at, updated_at, deleted_at)
        SELECT s.id, s.planning_id, s.created_by, s.post_title, s.post_objective,
               s.post_big_idea, s.post_main_message, 'DRAFT', 'PENDING',
               s.created_at, s.updated_at, s.deleted_at
        FROM post_structure s
        WHERE s.deleted_at IS NULL
          AND EXISTS (SELECT 1 FROM content_plans cp WHERE cp.id = s.planning_id)
        """,
    ),
    (
        "post_designs_from_posts",
        f"""
        INSERT OR IGNORE INTO post_designs
            (id, post_id, format, ratio, created_at, updated_at)
        SELECT s.id, s.id, s.content_format, s.art_ratio,
               s.created_at, s.updated_at
        FROM post_structure s
        WHERE s.content_format IN {CONTENT_FORMATS}
          AND s.art_ratio IN {ART_RATIOS}
          AND (s.content_format <> 'STORIES' OR s.art_ratio = '{ART_RATIO_9_16}')
          AND EXISTS (SELECT 1 FROM posts po WHERE po.id = s.id)
        """,
    ),
    (
        "post_designs_from_designs",
        f"""
        INSERT OR IGNORE INTO post_designs
            (id, post_id, format, ratio, created_at, updated_at)
        SELECT d.id, d.post_structure_id, s.content_format, s.art_ratio,
               d.created_at, d.updated_at
        FROM design_structure d
        JOIN post_structure s ON s.id = d.post_structure_id
        WHERE s.content_format IN {CONTENT_FORMATS}
          AND s.art_ratio IN {ART_RATIOS}
          AND (s.content_format <> 'STORIES' OR s.art_ratio = '{ART_RATIO_9_16}')
          AND EXISTS (SELECT 1 FROM posts po WHERE po.id = d.post_structure_id)
        """,
    ),
    (
        "design_slides",
        """
        INSERT OR IGNORE INTO design_slides
            (id, post_design_id, position, headline, subtitle, cta,
             art_direction, created_at, updated_at)
        SELECT d.id, d.id, 0, s.post_headline, NULL, s.image_cta,
               COALESCE(NULLIF(s.art_guiding, ''), 'legacy'),
               d.created_at, d.updated_at
        FROM design_structure d
        JOIN post_structure s ON s.id = d.post_structure_id
        WHERE EXISTS (SELECT 1 FROM post_designs pd WHERE pd.id = d.id)
        """,
    ),
    (
        "generated_images",
        """
        INSERT OR IGNORE INTO generated_images
            (id, design_slide_id, storage_bucket, storage_key, mime_type,
             size_bytes, width, height, error_message, generation_status,
             is_current, approval_status, created_at, updated_at, deleted_at)
        SELECT i.id, i.design_structure_id,
               CASE WHEN i.signed_url IS NOT NULL THEN 'legacy' END,
               i.signed_url,
               'image/png',
               CAST(NULLIF(i.size, '') AS INTEGER),
               CAST(substr(i.resolution, 1, instr(i.resolution, 'x') - 1) AS INTEGER),
               CAST(substr(i.resolution, instr(i.resolution, 'x') + 1) AS INTEGER),
               CASE
                 WHEN lower(COALESCE(i.image_status, '')) IN ('success', 'succeeded', 'completed')
                      AND i.signed_url IS NOT NULL
                      AND CAST(NULLIF(i.size, '') AS INTEGER) IS NOT NULL
                      AND instr(COALESCE(i.resolution, ''), 'x') > 1
                 THEN NULL
                 WHEN lower(COALESCE(i.image_status, '')) IN ('success', 'succeeded', 'completed')
                 THEN 'legacy image metadata incomplete'
               END,
               CASE
                 WHEN lower(COALESCE(i.image_status, '')) IN ('success', 'succeeded', 'completed')
                      AND i.signed_url IS NOT NULL
                      AND CAST(NULLIF(i.size, '') AS INTEGER) IS NOT NULL
                      AND instr(COALESCE(i.resolution, ''), 'x') > 1
                 THEN 'SUCCEEDED'
                 WHEN lower(COALESCE(i.image_status, '')) IN (
                      'failed', 'error', 'success', 'succeeded', 'completed'
                 ) THEN 'FAILED'
                 ELSE 'GENERATING'
               END,
               0,
               'PENDING',
               i.created_at, i.updated_at, i.deleted_at
        FROM generated_image i
        WHERE i.deleted_at IS NULL
          AND EXISTS (SELECT 1 FROM design_slides ds WHERE ds.id = i.design_structure_id)
        """,
    ),
)


def run(database_url: str, *, dry_run: bool = False) -> dict[str, int]:
    engine = sa.create_engine(database_url)
    report: dict[str, int] = {}
    try:
        with engine.begin() as connection:
            for name, statement in STEPS:
                result = connection.execute(sa.text(statement))
                report[name] = int(result.rowcount or 0)
            if dry_run:
                connection.rollback()
    finally:
        engine.dispose()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "sqlite+pysqlite:///./.local/db/creator.db"),
    )
    parser.add_argument("--dry-run", action="store_true", help="roll back at the end")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args()

    report = run(args.database_url, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for name, count in report.items():
            print(f"{name}: {count}")
        print(f"total rows written: {sum(report.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
