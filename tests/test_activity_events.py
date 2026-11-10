from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from creator.activity_event.models import ActivityEvent
from creator.activity_event.repository import SqlAlchemyActivityEventRepository
from creator.activity_event.service import list_events
from creator.application.errors import ApplicationError
from creator.brand import service as brand_service
from creator.brand.models import Brand
from creator.domain.exceptions import EntityNotFoundError
from creator.infrastructure.database import metadata as _metadata  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.enums import WorkspaceRole
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.user.models import User
from creator.user.ports import UserRecord
from creator.workspace.models import Workspace, WorkspaceMembership


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def seed(session: Session) -> tuple[User, Workspace, Brand]:
    user = User(id=uuid4(), auth_provider_id=str(uuid4()), display_name="User")
    workspace = Workspace(id=uuid4(), name="Workspace")
    brand = Brand(id=uuid4(), workspace_id=workspace.id, name="Brand")
    session.add_all([user, workspace])
    session.flush()
    session.add_all(
        [
            brand,
            WorkspaceMembership(
                user_id=user.id, workspace_id=workspace.id, role=WorkspaceRole.OWNER
            ),
        ]
    )
    session.commit()
    return user, workspace, brand


def read(
    uow: SqlAlchemyUnitOfWork, user: User, workspace: Workspace, **kwargs: object
) -> dict[str, object]:
    params = dict(
        limit=20, cursor=None, user_id=None, brand_id=None, entity_type=None, entity_id=None
    )
    params.update(kwargs)
    return list_events(
        uow=uow,
        actor=cast(UserRecord, SimpleNamespace(id=user.id)),
        workspace_id=workspace.id,
        **params,
    )  # type: ignore[arg-type]


def test_brand_events_filters_and_keyset_pagination(db: Session) -> None:
    user, workspace, brand = seed(db)
    other_user, other_workspace, other_brand = seed(db)
    repo = SqlAlchemyActivityEventRepository(db)
    for event_type in ("brand.created", "brand.updated", "brand.deleted"):
        repo.add_brand_event(
            workspace_id=workspace.id,
            user_id=user.id,
            brand_id=brand.id,
            event_type=event_type,
            metadata={},
        )
    repo.add_brand_event(
        workspace_id=other_workspace.id,
        user_id=other_user.id,
        brand_id=other_brand.id,
        event_type="brand.created",
        metadata={},
    )
    db.flush()
    for row in db.scalars(select(ActivityEvent)).all():
        row.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    db.commit()
    uow = SqlAlchemyUnitOfWork(lambda: db)
    with uow:
        first = read(
            uow,
            user,
            workspace,
            limit=1,
            user_id=user.id,
            brand_id=brand.id,
            entity_type="brand",
            entity_id=brand.id,
        )
        second = read(uow, user, workspace, limit=1, cursor=first["next_cursor"])
        third = read(uow, user, workspace, limit=1, cursor=second["next_cursor"])
        ids = [page["items"][0]["id"] for page in (first, second, third)]  # type: ignore[index]
        assert len(set(ids)) == 3
        assert third["next_cursor"] is None
        assert read(uow, user, workspace, brand_id=other_brand.id)["items"] == []
        with pytest.raises(ApplicationError):
            read(uow, user, other_workspace)
        with pytest.raises(ApplicationError):
            read(uow, user, workspace, cursor="broken")
        with pytest.raises(ApplicationError):
            read(uow, user, workspace, entity_type="brand")


def test_event_rejects_cross_workspace_and_metadata(db: Session) -> None:
    user, workspace, brand = seed(db)
    _, _, other_brand = seed(db)
    repo = SqlAlchemyActivityEventRepository(db)
    with pytest.raises(EntityNotFoundError):
        repo.add_brand_event(
            workspace_id=workspace.id,
            user_id=user.id,
            brand_id=other_brand.id,
            event_type="brand.created",
            metadata={},
        )
    with pytest.raises(ValueError):
        repo.add_brand_event(
            workspace_id=workspace.id,
            user_id=user.id,
            brand_id=brand.id,
            event_type="brand.created",
            metadata={"token": "secret"},
        )
    with pytest.raises(ValueError):
        repo.add_brand_event(
            workspace_id=workspace.id,
            user_id=user.id,
            brand_id=brand.id,
            event_type="invalid",
            metadata={},
        )


def test_activity_migration_upgrade_downgrade(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    url = f"sqlite+pysqlite:///{tmp_path / 'activity.db'}"
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    assert "activity_events" in inspect(engine).get_table_names()
    command.downgrade(config, "0004_drop_dead_tables")
    assert "activity_events" not in inspect(engine).get_table_names()
    command.upgrade(config, "head")
    assert "activity_events" in inspect(engine).get_table_names()
    engine.dispose()


def test_brand_lifecycle_and_failed_audit_roll_back(db: Session) -> None:
    user, workspace, _ = seed(db)
    actor = cast(UserRecord, SimpleNamespace(id=user.id))
    payload = SimpleNamespace(
        workspace_id=workspace.id,
        name="New",
        segment=None,
        promise=None,
        goals=None,
        indicators=None,
        inspirations=None,
        restrictions=None,
    )
    uow = SqlAlchemyUnitOfWork(lambda: db)
    with uow:
        created = brand_service.create_brand(uow=uow, actor=actor, request=None, payload=payload)
    from uuid import UUID

    brand_id = UUID(created["id"])
    with SqlAlchemyUnitOfWork(lambda: db) as uow:
        brand_service.update_brand(
            uow=uow,
            actor=actor,
            request=None,
            brand_id=brand_id,
            payload=SimpleNamespace(
                name="Changed",
                segment=None,
                promise=None,
                goals=None,
                indicators=None,
                inspirations=None,
                restrictions=None,
            ),
        )
    with SqlAlchemyUnitOfWork(lambda: db) as uow:
        brand_service.delete_brand(uow=uow, actor=actor, request=None, brand_id=brand_id)
    rows = db.scalars(select(ActivityEvent).where(ActivityEvent.brand_id == brand_id)).all()
    assert {r.event_type for r in rows} == {"brand.created", "brand.updated", "brand.deleted"}
    assert all(r.metadata_json == {} for r in rows)
    with pytest.raises(RuntimeError), SqlAlchemyUnitOfWork(lambda: db) as uow:
        with patch.object(
            uow.activity_events, "add_brand_event", side_effect=RuntimeError("audit failed")
        ):
            brand_service.create_brand(uow=uow, actor=actor, request=None, payload=payload)
    assert len(db.scalars(select(Brand).where(Brand.name == "New")).all()) == 0


@pytest.mark.parametrize(
    "role,allowed",
    [
        (WorkspaceRole.OWNER, True),
        (WorkspaceRole.MANAGER, True),
        (WorkspaceRole.EDITOR, False),
        (WorkspaceRole.VIEWER, False),
    ],
)
def test_timeline_permissions(db: Session, role: WorkspaceRole, allowed: bool) -> None:
    user, workspace, _ = seed(db)
    membership = db.scalars(
        select(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id)
    ).one()
    membership.role = role
    db.commit()
    with SqlAlchemyUnitOfWork(lambda: db) as uow:
        if allowed:
            assert read(uow, user, workspace)["items"] == []
        else:
            with pytest.raises(ApplicationError) as error:
                read(uow, user, workspace)
            assert error.value.status_code == 403


def test_newer_event_between_pages_is_not_repeated(db: Session) -> None:
    user, workspace, brand = seed(db)
    repo = SqlAlchemyActivityEventRepository(db)
    for _ in range(3):
        repo.add_brand_event(
            workspace_id=workspace.id,
            user_id=user.id,
            brand_id=brand.id,
            event_type="brand.created",
            metadata={},
        )
    db.commit()
    with SqlAlchemyUnitOfWork(lambda: db) as uow:
        first = read(uow, user, workspace, limit=1)
        uow.activity_events.add_brand_event(
            workspace_id=workspace.id,
            user_id=user.id,
            brand_id=brand.id,
            event_type="brand.created",
            metadata={},
        )
        second = read(uow, user, workspace, limit=1, cursor=first["next_cursor"])
        third = read(uow, user, workspace, limit=1, cursor=second["next_cursor"])
        ids = [page["items"][0]["id"] for page in (first, second, third)]  # type: ignore[index]
        assert len(set(ids)) == 3
        assert third["next_cursor"] is None
