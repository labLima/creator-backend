"""Data-safety test for the ``workspace_members`` migration (ADR-028, T8).

The upgrade must keep active memberships, drop the soft-deleted ones and leave
the child foreign keys pointing at the renamed table.
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


def _upgrade(path: Path) -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{path}")
    command.upgrade(config, "head")


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


def test_upgrade_keeps_active_members_and_drops_soft_deleted(tmp_path: Path) -> None:
    database = tmp_path / "members.db"
    _prepare(database)
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    workspace, user, active, removed = uuid4(), uuid4(), uuid4(), uuid4()
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
        invite, usage_active, usage_removed, recipient = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        connection.execute(
            sa.text(
                "INSERT INTO workspace_invites "
                "(id, workspace_id, type, role, token, created_by, status) "
                "VALUES (:id, :workspace, 'LINK', 'owner', :token, :user, 'PENDING')"
            ),
            {
                "id": invite.hex,
                "workspace": workspace.hex,
                "token": f"token-{invite}",
                "user": user.hex,
            },
        )
        for member, deleted in ((active, None), (removed, "CURRENT_TIMESTAMP")):
            connection.execute(
                sa.text(
                    "INSERT INTO workspace_memberships "
                    "(id, workspace_id, user_id, role, deleted_at) "
                    f"VALUES (:id, :workspace, :user, 'owner', {deleted or 'NULL'})"
                ),
                {"id": member.hex, "workspace": workspace.hex, "user": user.hex},
            )
        for usage, member in ((usage_active, active), (usage_removed, removed)):
            connection.execute(
                sa.text(
                    "INSERT INTO workspace_invite_usages "
                    "(id, invite_id, user_id, workspace_id, member_id) "
                    "VALUES (:id, :invite, :user, :workspace, :member)"
                ),
                {
                    "id": usage.hex,
                    "invite": invite.hex,
                    "user": user.hex,
                    "workspace": workspace.hex,
                    "member": member.hex,
                },
            )
        notification = uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO notifications "
                "(id, workspace_id, type, title, body, created_by) "
                "VALUES (:id, :workspace, 'SYSTEM', 'title', 'body', :user)"
            ),
            {"id": notification.hex, "workspace": workspace.hex, "user": user.hex},
        )
        connection.execute(
            sa.text(
                "INSERT INTO notification_recipients "
                "(id, notification_id, user_id, channel, status, workspace_member_id) "
                "VALUES (:id, :notification, :user, 'EMAIL', 'PENDING', :member)"
            ),
            {
                "id": recipient.hex,
                "notification": notification.hex,
                "user": user.hex,
                "member": removed.hex,
            },
        )
    engine.dispose()

    _upgrade(database)

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        rows = connection.execute(
            sa.text("SELECT id, role, status, invited_by FROM workspace_members")
        ).all()
        assert len(rows) == 1, rows
        kept = rows[0]
        assert kept[0] == active.hex
        assert kept[1] in {"owner", "OWNER"}
        assert kept[2] == "ACTIVE"
        assert kept[3] is None
        # the removed member's usage is gone; the active member's usage stays
        usages = connection.execute(
            sa.text("SELECT id, member_id FROM workspace_invite_usages")
        ).all()
        assert [row[0] for row in usages] == [usage_active.hex]
        recipient_member = connection.execute(
            sa.text("SELECT workspace_member_id FROM notification_recipients")
        ).scalar_one()
        assert recipient_member is None
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    engine.dispose()


def test_upgrade_maps_the_role_vocabulary(tmp_path: Path) -> None:
    database = tmp_path / "roles.db"
    _prepare(database)
    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    workspace = uuid4()
    roles = {
        "owner": uuid4(),
        "admin": uuid4(),
        "editor": uuid4(),
        "viewer": uuid4(),
    }
    with engine.begin() as connection:
        connection.execute(
            sa.text("INSERT INTO workspaces (id, name) VALUES (:id, 'ws')"),
            {"id": workspace.hex},
        )
        for role, user in roles.items():
            connection.execute(
                sa.text(
                    "INSERT INTO users (id, external_id, global_role) "
                    "VALUES (:id, :external, 'membro')"
                ),
                {"id": user.hex, "external": f"ext-{user}"},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO workspace_memberships (id, workspace_id, user_id, role) "
                    "VALUES (:id, :workspace, :user, :role)"
                ),
                {
                    "id": uuid4().hex,
                    "workspace": workspace.hex,
                    "user": user.hex,
                    "role": role,
                },
            )
            connection.execute(
                sa.text(
                    "INSERT INTO workspace_invites "
                    "(id, workspace_id, type, role, token, created_by, status) "
                    "VALUES (:id, :workspace, 'LINK', :role, :token, :user, 'PENDING')"
                ),
                {
                    "id": uuid4().hex,
                    "workspace": workspace.hex,
                    "role": role,
                    "token": f"token-{user}",
                    "user": user.hex,
                },
            )
    engine.dispose()

    _upgrade(database)

    engine = sa.create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        member_roles = {
            row[0] for row in connection.execute(sa.text("SELECT role FROM workspace_members"))
        }
        invite_roles = {
            row[0] for row in connection.execute(sa.text("SELECT role FROM workspace_invites"))
        }
    engine.dispose()
    assert member_roles == {"OWNER", "MANAGER", "EDITOR", "VIEWER"}
    assert invite_roles == {"OWNER", "MANAGER", "EDITOR", "VIEWER"}
