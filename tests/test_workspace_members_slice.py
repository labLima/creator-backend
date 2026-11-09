"""Behaviour of ``workspace_members`` after the rename (ADR-028, slice T8).

Membership removal is physical: the final modeling has no ``deleted_at`` and the
unique key is ``(workspace_id, user_id)``. The ``status`` column carries the
membership lifecycle instead.
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
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _member(connection: sa.Connection, *, workspace_id: str, user_id: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO workspace_members (id, workspace_id, user_id, role) "
            "VALUES (:id, :workspace, :user, 'owner')"
        ),
        {"id": uuid4().hex, "workspace": workspace_id, "user": user_id},
    )


def test_membership_defaults_to_active(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        workspace_id, user_id = uuid4().hex, uuid4().hex
        _member(connection, workspace_id=workspace_id, user_id=user_id)
        status = connection.execute(sa.text("SELECT status FROM workspace_members")).scalar_one()
    assert status == "ACTIVE"


def test_membership_is_unique_per_workspace_and_user(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        workspace_id, user_id = uuid4().hex, uuid4().hex
        _member(connection, workspace_id=workspace_id, user_id=user_id)
        with pytest.raises(IntegrityError) as error:
            _member(connection, workspace_id=workspace_id, user_id=user_id)
    assert "UNIQUE constraint failed: workspace_members" in str(error.value)


def test_removed_membership_can_be_created_again(engine: sa.Engine) -> None:
    """Physical removal keeps the pair reusable, unlike a soft-deleted row."""
    with engine.begin() as connection:
        workspace_id, user_id = uuid4().hex, uuid4().hex
        _member(connection, workspace_id=workspace_id, user_id=user_id)
        connection.execute(sa.text("DELETE FROM workspace_members"))
        _member(connection, workspace_id=workspace_id, user_id=user_id)
        total = connection.execute(sa.text("SELECT COUNT(*) FROM workspace_members")).scalar_one()
    assert total == 1


def test_membership_status_vocabulary_is_closed(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        with pytest.raises(IntegrityError) as error:
            connection.execute(
                sa.text(
                    "INSERT INTO workspace_members "
                    "(id, workspace_id, user_id, role, status) "
                    "VALUES (:id, :workspace, :user, 'owner', 'NOT_A_STATUS')"
                ),
                {
                    "id": uuid4().hex,
                    "workspace": uuid4().hex,
                    "user": uuid4().hex,
                },
            )
    assert "member_status" in str(error.value)


def test_invited_by_is_nulled_when_the_inviter_is_deleted(engine: sa.Engine) -> None:
    engine.dispose()
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def _foreign_keys(connection: object, _record: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        with engine.begin() as connection:
            inviter, member, workspace = uuid4(), uuid4(), uuid4()
            users = sa.text(
                "INSERT INTO users (id, external_id, global_role, created_at, updated_at) "
                "VALUES (:id, :external, 'membro', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
            for user in (inviter, member):
                connection.execute(users, {"id": user.hex, "external": f"ext-{user}"})
            connection.execute(
                sa.text(
                    "INSERT INTO workspaces (id, name, created_at, updated_at) "
                    "VALUES (:id, 'ws', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": workspace.hex},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO workspace_members (id, workspace_id, user_id, role, invited_by) "
                    "VALUES (:id, :workspace, :user, 'editor', :inviter)"
                ),
                {
                    "id": uuid4().hex,
                    "workspace": workspace.hex,
                    "user": member.hex,
                    "inviter": inviter.hex,
                },
            )
            connection.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": inviter.hex})
            invited_by = connection.execute(
                sa.text("SELECT invited_by FROM workspace_members")
            ).scalar_one()
        assert invited_by is None
    finally:
        engine.dispose()
