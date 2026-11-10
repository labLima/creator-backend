"""Data-safety test for the T25 campaign/persona migration (0018).

The migration must backfill ``campaigns.brand_id``, move the free-form voice to
``campaign_voices``, map persona age/trigger and move ``interest`` to
``persona_interests`` before dropping the old columns.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREV_SCHEMA = PROJECT_ROOT / "tests" / "contracts" / "schema_prev_ddl.sql"


def _upgrade(path: Path, revision: str) -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    command.upgrade(config, revision)


def _prepare(path: Path) -> None:
    statements = [
        statement.strip()
        for statement in PREV_SCHEMA.read_text(encoding="utf-8").split("\n\n")
        if statement.strip()
    ]
    engine = sa.create_engine(f"sqlite+pysqlite:///{path}")
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
        connection.exec_driver_sql(
            "CREATE TABLE alembic_version ("
            "version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        connection.exec_driver_sql(
            "INSERT INTO alembic_version (version_num) VALUES (?)", ("0005_content_text_versions",)
        )
    engine.dispose()


def test_campaign_and_persona_data_is_migrated(tmp_path: Path) -> None:
    database = tmp_path / "campaigns.db"
    _prepare(database)
    _upgrade(database, "0017_brand_alignment")

    workspace, user, brand, campaign, persona = (uuid4() for _ in range(5))
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            sa.text("INSERT INTO workspaces (id, name) VALUES (:id, 'ws')"),
            {"id": workspace.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO users (id, auth_provider_id, display_name, global_role) "
                "VALUES (:id, 'provider', 'User', 'membro')"
            ),
            {"id": user.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO brands (id, workspace_id, created_by, name, segment) "
                "VALUES (:id, :workspace, :user, 'Brand', 'creator')"
            ),
            {"id": brand.hex, "workspace": workspace.hex, "user": user.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO campaigns "
                "(id, brand_id, workspace_id, created_by, name, voice) "
                "VALUES (:id, NULL, :workspace, :user, 'Campaign', 'inspirational')"
            ),
            {"id": campaign.hex, "workspace": workspace.hex, "user": user.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO personas "
                "(id, brand_id, created_by, name, age, gender, interest, trigger) "
                "VALUES (:id, :brand, :user, 'Persona', 30, 'female', 'Coffee', 'Commute')"
            ),
            {"id": persona.hex, "brand": brand.hex, "user": user.hex},
        )
    engine.dispose()

    _upgrade(database, "head")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        brand_id = connection.execute(
            sa.text("SELECT brand_id FROM campaigns WHERE id = :id"), {"id": campaign.hex}
        ).scalar_one()
        assert brand_id == brand.hex
        voices = (
            connection.execute(
                sa.text("SELECT voice FROM campaign_voices WHERE campaign_id = :id"),
                {"id": campaign.hex},
            )
            .scalars()
            .all()
        )
        assert voices == ["INSPIRATIONAL"]
        persona_row = connection.execute(
            sa.text("SELECT age_range, gender, trigger_event FROM personas WHERE id = :id"),
            {"id": persona.hex},
        ).one()
        assert tuple(persona_row) == ("FROM_25_TO_34", "FEMALE", "Commute")
        interests = (
            connection.execute(
                sa.text("SELECT interest FROM persona_interests WHERE persona_id = :id"),
                {"id": persona.hex},
            )
            .scalars()
            .all()
        )
        assert interests == ["Coffee"]
        campaign_columns = {
            row[1] for row in connection.execute(sa.text("PRAGMA table_info(campaigns)"))
        }
        assert "workspace_id" not in campaign_columns
        assert "voice" not in campaign_columns
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    engine.dispose()
