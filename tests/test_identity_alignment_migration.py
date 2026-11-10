"""Data-safety test for the T24 identity/invite migration (0016).

The migration must absorb ``external_id`` into ``auth_provider_id``, hash the
plaintext invite tokens, map inactive/soft-deleted invites to ``REVOKED`` and
derive ``member_id`` for usages before dropping the denormalized columns.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT_ROOT / "tests" / "contracts"
PREV_SCHEMA = CONTRACTS / "schema_prev_ddl.sql"
PREV_REVISION = "0005_content_text_versions"


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
            "INSERT INTO alembic_version (version_num) VALUES (?)", (PREV_REVISION,)
        )
    engine.dispose()


def test_identity_and_invites_are_migrated_without_data_loss(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _prepare(database)
    _upgrade(database, "0014_generated_images")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    workspace, local_user, provider_user = uuid4(), uuid4(), uuid4()
    local_token, link_token, revoked_token = (
        "local-token",
        "link-token",
        "revoked-token",
    )
    email_invite, link_invite, revoked_invite = uuid4(), uuid4(), uuid4()
    active_member = uuid4()
    with engine.begin() as connection:
        connection.execute(
            sa.text("INSERT INTO workspaces (id, name) VALUES (:id, 'ws')"),
            {"id": workspace.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO users (id, external_id, email, display_name, global_role) "
                "VALUES (:id, :external, :email, NULL, 'membro')"
            ),
            {"id": local_user.hex, "external": f"local:{local_user}", "email": "local@example.com"},
        )
        connection.execute(
            sa.text(
                "INSERT INTO users (id, external_id, email, global_role) "
                "VALUES (:id, :external, 'provider@example.com', 'membro')"
            ),
            {"id": provider_user.hex, "external": "google:123"},
        )
        connection.execute(
            sa.text(
                "INSERT INTO workspace_members "
                "(id, workspace_id, user_id, role, status) "
                "VALUES (:id, :workspace, :user, 'OWNER', 'ACTIVE')"
            ),
            {"id": active_member.hex, "workspace": workspace.hex, "user": local_user.hex},
        )
        invites = [
            (email_invite, "EMAIL", "OWNER", "invite@example.com", local_token, None, "PENDING", 1),
            (link_invite, "link", "manager", None, link_token, 5, "pending", 1),
            (revoked_invite, "LINK", "EDITOR", None, revoked_token, 2, "PENDING", 0),
        ]
        for invite_id, kind, role, email, token, max_uses, status, is_active in invites:
            connection.execute(
                sa.text(
                    "INSERT INTO workspace_invites "
                    "(id, workspace_id, type, role, email, token, max_uses, status, "
                    "created_by, is_active) "
                    "VALUES (:id, :workspace, :type, :role, :email, :token, :max_uses, "
                    ":status, :created_by, :is_active)"
                ),
                {
                    "id": invite_id.hex,
                    "workspace": workspace.hex,
                    "type": kind,
                    "role": role,
                    "email": email,
                    "token": token,
                    "max_uses": max_uses,
                    "status": status,
                    "created_by": local_user.hex,
                    "is_active": is_active,
                },
            )
        connection.execute(
            sa.text(
                "INSERT INTO workspace_invite_usages "
                "(id, invite_id, user_id, workspace_id, member_id) "
                "VALUES (:id, :invite, :user, :workspace, :member)"
            ),
            {
                "id": uuid4().hex,
                "invite": email_invite.hex,
                "user": local_user.hex,
                "workspace": workspace.hex,
                "member": active_member.hex,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO workspace_invite_usages "
                "(id, invite_id, user_id, workspace_id, member_id) "
                "VALUES (:id, :invite, :user, :workspace, NULL)"
            ),
            {
                "id": uuid4().hex,
                "invite": link_invite.hex,
                "user": local_user.hex,
                "workspace": workspace.hex,
            },
        )
    engine.dispose()

    _upgrade(database, "head")

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        users = {
            row[0]: row
            for row in connection.execute(
                sa.text("SELECT id, auth_provider_id, display_name, email FROM users")
            ).all()
        }
        assert users[local_user.hex][1] is None
        assert users[provider_user.hex][1] == "google:123"
        assert all(row[2] for row in users.values()), users
        assert users[local_user.hex][3] == "local@example.com"

        invites = {
            row[0]: row
            for row in connection.execute(
                sa.text("SELECT id, type, role, status, token_hash FROM workspace_invites")
            ).all()
        }
        assert invites[email_invite.hex][1:4] == ("EMAIL", "OWNER", "PENDING")
        assert invites[email_invite.hex][4] == hashlib.sha256(local_token.encode()).hexdigest()
        assert invites[link_invite.hex][1:4] == ("LINK", "MANAGER", "PENDING")
        assert invites[revoked_invite.hex][3] == "REVOKED"
        assert invites[revoked_invite.hex][4] == hashlib.sha256(revoked_token.encode()).hexdigest()

        usages = connection.execute(
            sa.text("SELECT invite_id, member_id FROM workspace_invite_usages")
        ).all()
        assert len(usages) == 2
        assert {row[1] for row in usages} == {active_member.hex}

        columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(users)")).all()}
        assert "external_id" not in columns
        assert "cpf" not in columns
        assert "cnpj" not in columns
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    engine.dispose()
