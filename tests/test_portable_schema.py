from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import JSON, Uuid, create_engine, select
from sqlalchemy.orm import Session

from creator.infrastructure.db import Base
from creator.infrastructure.models import GlobalRole, Settings, User
from creator.infrastructure.models.types import UTCDateTime


def test_registered_schema_creates_on_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    assert {"users", "auth_sessions", "plans", "provider_disputes"} <= set(Base.metadata.tables)
    engine.dispose()


def test_schema_uses_generic_uuid_json_and_python_uuid_defaults() -> None:
    for table in Base.metadata.tables.values():
        for column in table.primary_key.columns:
            assert isinstance(column.type, Uuid)
            assert column.default is not None
            assert column.default.arg.__name__ == uuid4.__name__

        for column in table.columns:
            assert not column.type.__class__.__module__.startswith("sqlalchemy.dialects.postgresql")

    assert isinstance(Base.metadata.tables["settings"].c.default_preferences.type, JSON)
    assert isinstance(Base.metadata.tables["users"].c.created_at.type, UTCDateTime)


def test_sqlite_round_trips_uuid_json_and_utc_timestamp() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    instant = datetime(2026, 10, 26, 15, 0, tzinfo=UTC) - timedelta(hours=3)

    with Session(engine) as session:
        user = User(
            external_id="external-1",
            global_role=GlobalRole.MEMBRO,
            created_at=instant,
            updated_at=instant,
        )
        session.add(user)
        session.flush()
        settings = Settings(
            user_id=user.id,
            default_preferences={"timezone": "America/Fortaleza"},
            created_at=instant,
            updated_at=instant,
        )
        session.add(settings)
        session.commit()

        stored = session.scalar(select(Settings).where(Settings.user_id == user.id))

    assert stored is not None
    assert stored.user_id == user.id
    assert stored.default_preferences == {"timezone": "America/Fortaleza"}
    assert stored.created_at == instant.astimezone(UTC)
    assert stored.created_at.tzinfo is not None
    engine.dispose()


def test_enums_are_string_checks_and_partial_indexes_target_sqlite() -> None:
    user_role = Base.metadata.tables["users"].c.global_role.type
    assert user_role.native_enum is False
    assert user_role.create_constraint is True

    index = next(
        index
        for index in Base.metadata.tables["workspace_memberships"].indexes
        if index.name == "uq_workspace_memberships_active_user_workspace"
    )
    assert str(index.dialect_options["sqlite"]["where"]) == "deleted_at IS NULL"

    completed_step_index = next(
        index
        for index in Base.metadata.tables["agent_workflow_steps"].indexes
        if index.name == "uq_agent_workflow_steps_completed_source_role_item"
    )
    predicate = "status = 'COMPLETED' AND source_event_id IS NOT NULL"
    assert str(completed_step_index.dialect_options["sqlite"]["where"]) == predicate
    assert str(completed_step_index.dialect_options["postgresql"]["where"]) == predicate
