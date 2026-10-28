from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from creator.application.auth import (
    EmailAlreadyRegisteredError,
    ExpiredTokenError,
    InvalidCredentialsError,
    RefreshInProgressError,
    login,
    logout,
    principal_from_access_token,
    refresh,
    session_is_active,
    signup,
)
from creator.application.auth_ports import (
    AccessTokenCodec,
    Clock,
    CsrfTokenService,
    RefreshTokenGenerator,
)
from creator.config import Settings
from creator.domain.auth import Principal
from creator.infrastructure.auth import auth_token_services
from creator.infrastructure.database.db import create_database_engine
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRET = "test-local-auth-jwt-secret-with-32-bytes"


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_jwt_secret": SECRET,
        "auth_password_min_length": 8,
        "auth_refresh_token_ttl_days": 30,
        "auth_access_token_ttl_seconds": 900,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture()
def engine(tmp_path: Path) -> Engine:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'auth-test.db'}"
    engine = create_database_engine(database_url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def uow(engine: Engine) -> SqlAlchemyUnitOfWork:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SqlAlchemyUnitOfWork(factory) as unit_of_work:
        yield unit_of_work


@pytest.fixture()
def token_services():
    return auth_token_services()


def test_signup_creates_user_workspace_membership_and_session(
    uow: SqlAlchemyUnitOfWork, token_services
) -> None:
    result = signup(
        unit_of_work=uow,
        settings=_settings(),
        email="Owner@Example.com",
        password="correct-password",
        workspace_name="Creator Workspace",
        token_services=token_services,
    )

    assert result.user.email == "owner@example.com"
    assert result.user.password_hash is not None
    assert "correct-password" not in result.user.password_hash
    assert result.workspace.name == "Creator Workspace"
    assert result.membership.role == "owner"
    assert result.result.session is not None
    assert result.result.session.provider == "local"
    assert result.result.session.principal.subject == str(result.user.id)


def test_signup_rejects_duplicate_email(uow: SqlAlchemyUnitOfWork, token_services) -> None:
    signup(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
    )
    with pytest.raises(EmailAlreadyRegisteredError):
        signup(
            unit_of_work=uow,
            settings=_settings(),
            email="OWNER@example.com",
            password="correct-password",
            workspace_name="Another Workspace",
            token_services=token_services,
        )


def test_login_rejects_wrong_password_and_accepts_correct_one(
    uow: SqlAlchemyUnitOfWork, token_services
) -> None:
    signup(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
    )
    with pytest.raises(InvalidCredentialsError):
        login(
            unit_of_work=uow,
            settings=_settings(),
            email="owner@example.com",
            password="wrong-password",
            token_services=token_services,
        )

    session = login(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        token_services=token_services,
    )
    assert session.access_token
    assert session.refresh_token


def test_refresh_rotates_and_reuse_revokes_family(
    uow: SqlAlchemyUnitOfWork, token_services
) -> None:
    result = signup(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
    )
    assert result.result.session is not None
    original_refresh = result.result.session.refresh_token

    rotated = refresh(
        unit_of_work=uow,
        settings=_settings(),
        refresh_token=original_refresh,
        token_services=token_services,
    )
    assert rotated.refresh_token != original_refresh

    with pytest.raises(RefreshInProgressError):
        refresh(
            unit_of_work=uow,
            settings=_settings(),
            refresh_token=original_refresh,
            token_services=token_services,
        )

    rotated_again = refresh(
        unit_of_work=uow,
        settings=_settings(),
        refresh_token=rotated.refresh_token,
        token_services=token_services,
    )
    assert rotated_again.refresh_token != rotated.refresh_token


def test_logout_revokes_current_session(uow: SqlAlchemyUnitOfWork, token_services) -> None:
    result = signup(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
    )
    assert result.result.session is not None
    session_id = result.result.session.principal.session_id
    assert session_id is not None
    logout(unit_of_work=uow, session_id=UUID(session_id))
    assert (
        session_is_active(
            unit_of_work=uow,
            session_id=UUID(session_id),
            clock=token_services.clock,
        )
        is False
    )


def test_expired_refresh_token_is_rejected(uow: SqlAlchemyUnitOfWork, token_services) -> None:
    class FakeClock:
        current = datetime(2026, 1, 1, tzinfo=UTC)

        def now(self) -> datetime:
            return self.current

    clock = FakeClock()
    settings = _settings(auth_refresh_token_ttl_days=1)
    result = signup(
        unit_of_work=uow,
        settings=settings,
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
        clock=clock,
    )
    assert result.result.session is not None
    clock.current += timedelta(days=1, seconds=1)
    with pytest.raises(ExpiredTokenError):
        refresh(
            unit_of_work=uow,
            settings=settings,
            refresh_token=result.result.session.refresh_token,
            token_services=token_services,
            clock=clock,
        )


def test_application_auth_accepts_replaceable_token_ports(uow: SqlAlchemyUnitOfWork) -> None:
    class FakeAccessTokenCodec:
        def issue(self, *, user_id: UUID, session_id: UUID, role: str, settings: Settings) -> str:
            return f"fake-access:{user_id}:{session_id}:{role}"

        def principal(self, token: str, settings: Settings) -> Principal:
            assert token == "fake-token"
            return Principal(subject="fake-user", session_id="fake-session")

    class FakeRefreshTokenGenerator:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self) -> str:
            self.calls += 1
            return f"fake-refresh-{self.calls}"

    class FakeCsrfTokenService:
        def issue(self, *, session_id: UUID, settings: Settings) -> str:
            return f"fake-csrf-{session_id}"

        def verify(self, *, token: str, session_id: UUID, settings: Settings) -> bool:
            return token == f"fake-csrf-{session_id}"

    class FakeServices:
        access: AccessTokenCodec = FakeAccessTokenCodec()
        refresh: RefreshTokenGenerator = FakeRefreshTokenGenerator()
        csrf: CsrfTokenService = FakeCsrfTokenService()
        clock: Clock = type(
            "FakeClock",
            (),
            {"now": lambda self: datetime(2026, 1, 1, tzinfo=UTC)},
        )()

    services = FakeServices()
    result = signup(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=services,
    )

    assert result.result.session is not None
    assert result.result.session.access_token.startswith("fake-access:")
    assert result.result.session.refresh_token == "fake-refresh-1"
    assert (
        principal_from_access_token("fake-token", _settings(), token_services=services).subject
        == "fake-user"
    )
