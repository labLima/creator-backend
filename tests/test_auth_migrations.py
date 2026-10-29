from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from creator.infrastructure.database.db import create_database_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_auth_session_rotation_migration_backfills_and_downgrades(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'legacy-auth.db'}"
    engine = create_database_engine(database_url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    user_id = uuid4()
    session_id = uuid4()
    family_id = uuid4()
    expires_at = datetime(2026, 11, 1, tzinfo=UTC)

    try:
        with engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
            )
            connection.execute(
                text(
                    """
                    INSERT INTO alembic_version (version_num)
                    VALUES ('0003_pipeline_delivery_state')
                    """
                )
            )
            connection.execute(text("CREATE TABLE users (id CHAR(32) PRIMARY KEY)"))
            connection.execute(
                text(
                    """
                    CREATE TABLE auth_sessions (
                        id CHAR(32) PRIMARY KEY,
                        user_id CHAR(32) NOT NULL REFERENCES users(id),
                        family_id CHAR(32) NOT NULL,
                        refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
                        expires_at DATETIME NOT NULL,
                        revoked_at DATETIME,
                        replaced_by_id CHAR(32),
                        user_agent VARCHAR(500),
                        ip_address VARCHAR(45),
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_used_at DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text("CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id)")
            )
            connection.execute(
                text("CREATE INDEX ix_auth_sessions_family_id ON auth_sessions (family_id)")
            )
            connection.execute(
                text("CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at)")
            )
            connection.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id.hex})
            connection.execute(
                text(
                    """
                        INSERT INTO auth_sessions
                            (id, user_id, family_id, refresh_token_hash, expires_at)
                    VALUES (:id, :user_id, :family_id, :hash, :expires_at)
                    """
                ),
                {
                    "id": session_id.hex,
                    "user_id": user_id.hex,
                    "family_id": family_id.hex,
                    "hash": "a" * 64,
                    "expires_at": expires_at,
                },
            )

        command.upgrade(config, "0003_auth_session_rotation")
        columns = {column["name"] for column in inspect(engine).get_columns("auth_sessions")}
        assert {
            "previous_refresh_token_hash",
            "rotated_at",
            "absolute_expires_at",
        } <= columns
        with engine.connect() as connection:
            absolute_expires_at = connection.execute(
                text("SELECT absolute_expires_at FROM auth_sessions WHERE id = :id"),
                {"id": session_id.hex},
            ).scalar_one()
        assert datetime.fromisoformat(absolute_expires_at) == expires_at

        command.downgrade(config, "0003_pipeline_delivery_state")
        downgraded_columns = {
            column["name"] for column in inspect(engine).get_columns("auth_sessions")
        }
        assert (
            not {
                "previous_refresh_token_hash",
                "rotated_at",
                "absolute_expires_at",
            }
            & downgraded_columns
        )
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT refresh_token_hash FROM auth_sessions WHERE id = :id"),
                    {"id": session_id.hex},
                ).scalar_one()
                == "a" * 64
            )
    finally:
        engine.dispose()
