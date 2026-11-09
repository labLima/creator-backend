"""Data-safety test for the ``campaigns`` rebuild in migration 0011 (T22).

SQLite cannot alter a foreign key in place, so the migration rebuilds the table.
With foreign keys enforced, ``DROP TABLE`` would cascade into ``campaign_hashtags``
and ``campaign_voices``; the migration disables enforcement on its own connection.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
PREV_SCHEMA = CONTRACTS / "schema_prev_ddl.sql"
PREV_REVISION = "0005_content_text_versions"


def _config(path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    return config


def test_campaign_rebuild_preserves_children(tmp_path: Path) -> None:
    database = tmp_path / "campaigns.db"
    statements = [
        statement.strip()
        for statement in PREV_SCHEMA.read_text(encoding="utf-8").split("\n\n")
        if statement.strip()
    ]
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
        connection.exec_driver_sql(
            "CREATE TABLE alembic_version ("
            "version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        connection.exec_driver_sql(
            "INSERT INTO alembic_version (version_num) VALUES (?)", (PREV_REVISION,)
        )
    engine.dispose()

    config = _config(database)
    command.upgrade(config, "0010_workspace_role_vocabulary")

    workspace, user, campaign = uuid4(), uuid4(), uuid4()
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            sa.text("INSERT INTO workspaces (id, name) VALUES (:id, 'ws')"),
            {"id": workspace.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO users (id, external_id, global_role) VALUES (:id, :external, 'membro')"
            ),
            {"id": user.hex, "external": f"ext-{user}"},
        )
        connection.execute(
            sa.text(
                "INSERT INTO campaigns "
                "(id, workspace_id, created_by, name, created_at, updated_at) "
                "VALUES (:id, :workspace, :user, 'campaign', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": campaign.hex, "workspace": workspace.hex, "user": user.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO campaign_hashtags "
                "(id, campaign_id, hashtag, created_at, updated_at) "
                "VALUES (:id, :campaign, 'verao', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "campaign": campaign.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO campaign_voices "
                "(id, campaign_id, voice, created_at, updated_at) "
                "VALUES (:id, :campaign, 'INSPIRATIONAL', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "campaign": campaign.hex},
        )
    engine.dispose()

    command.upgrade(config, "head")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.connect() as connection:
        hashtags = connection.execute(
            sa.text("SELECT COUNT(*) FROM campaign_hashtags")
        ).scalar_one()
        voices = connection.execute(sa.text("SELECT COUNT(*) FROM campaign_voices")).scalar_one()
        campaigns = connection.execute(sa.text("SELECT COUNT(*) FROM campaigns")).scalar_one()
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    engine.dispose()

    assert (campaigns, hashtags, voices) == (1, 1, 1)
    assert violations == []
