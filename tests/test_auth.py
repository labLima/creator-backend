from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Lock
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, select
from sqlalchemy.orm import sessionmaker

from creator.application.auth import (
    EmailAlreadyRegisteredError,
    ExpiredTokenError,
    InvalidCredentialsError,
    RefreshInProgressError,
    RevokedSessionError,
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
from creator.infrastructure.database import models
from creator.infrastructure.database.db import create_database_engine
from creator.infrastructure.persistence.repositories.auth_session_repositories import (
    SqlAlchemyAuthSessionRepository,
)
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.repositories.auth import AuthSessionRecord

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


def test_concurrent_refresh_has_one_winner(
    engine: Engine, uow: SqlAlchemyUnitOfWork, token_services, monkeypatch: pytest.MonkeyPatch
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
    refresh_token = result.result.session.refresh_token
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    barrier = Barrier(2)
    arrival_lock = Lock()
    arrivals = 0
    original_get = SqlAlchemyAuthSessionRepository.get_by_refresh_hash

    def synchronized_get(
        repository: SqlAlchemyAuthSessionRepository, token_hash: str
    ) -> AuthSessionRecord | None:
        nonlocal arrivals
        record = original_get(repository, token_hash)
        with arrival_lock:
            arrivals += 1
            should_wait = arrivals <= 2
        if should_wait:
            barrier.wait(timeout=5)
        return record

    monkeypatch.setattr(SqlAlchemyAuthSessionRepository, "get_by_refresh_hash", synchronized_get)

    def rotate() -> str:
        with SqlAlchemyUnitOfWork(factory) as concurrent_uow:
            try:
                refresh(
                    unit_of_work=concurrent_uow,
                    settings=_settings(),
                    refresh_token=refresh_token,
                    token_services=token_services,
                )
            except RefreshInProgressError:
                return "in_progress"
            return "rotated"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: rotate(), range(2)))

    assert sorted(outcomes) == ["in_progress", "rotated"]
    with SqlAlchemyUnitOfWork(factory) as verification_uow:
        original = verification_uow.auth_sessions.get_by_refresh_hash(
            hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        )
        assert original is not None
        active_family_sessions = (
            verification_uow._require_session()
            .scalars(
                select(models.AuthSession).where(
                    models.AuthSession.family_id == original.family_id,
                    models.AuthSession.revoked_at.is_(None),
                )
            )
            .all()
        )
        assert len(active_family_sessions) == 1


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


def test_reuse_after_grace_revokes_the_family(uow: SqlAlchemyUnitOfWork, token_services) -> None:
    class FakeClock:
        current = datetime(2026, 1, 1, tzinfo=UTC)

        def now(self) -> datetime:
            return self.current

    clock = FakeClock()
    settings = _settings()
    created = signup(
        unit_of_work=uow,
        settings=settings,
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
        clock=clock,
    )
    assert created.result.session is not None
    first = created.result.session.refresh_token
    rotated = refresh(
        unit_of_work=uow,
        settings=settings,
        refresh_token=first,
        token_services=token_services,
        clock=clock,
    )
    clock.current += timedelta(seconds=31)

    with pytest.raises(RevokedSessionError):
        refresh(
            unit_of_work=uow,
            settings=settings,
            refresh_token=first,
            token_services=token_services,
            clock=clock,
        )

    assert not session_is_active(
        unit_of_work=uow,
        session_id=UUID(rotated.principal.session_id or ""),
        clock=clock,
    )


def test_session_ttl_is_bounded_by_refresh_and_absolute_expiry(
    uow: SqlAlchemyUnitOfWork, token_services
) -> None:
    class FakeClock:
        current = datetime(2026, 1, 1, tzinfo=UTC)

        def now(self) -> datetime:
            return self.current

    clock = FakeClock()
    settings = _settings(auth_refresh_token_ttl_days=30, auth_session_absolute_ttl_days=25)
    created = signup(
        unit_of_work=uow,
        settings=settings,
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
        clock=clock,
    )
    assert created.result.session is not None
    session_id = UUID(created.result.session.principal.session_id or "")
    initial = uow.auth_sessions.get_by_id(session_id)
    assert initial is not None
    assert initial.expires_at == initial.absolute_expires_at
    assert created.result.session.refresh_expires_in == 25 * 86400

    clock.current += timedelta(days=20)
    rotated = refresh(
        unit_of_work=uow,
        settings=settings,
        refresh_token=created.result.session.refresh_token,
        token_services=token_services,
        clock=clock,
    )
    rotated_id = UUID(rotated.principal.session_id or "")
    successor = uow.auth_sessions.get_by_id(rotated_id)
    assert successor is not None
    assert successor.expires_at == successor.absolute_expires_at
    assert rotated.refresh_expires_in == 5 * 86400


def test_cleanup_removes_refresh_expired_before_absolute_expiry(
    uow: SqlAlchemyUnitOfWork, token_services
) -> None:
    created = signup(
        unit_of_work=uow,
        settings=_settings(auth_refresh_token_ttl_days=1, auth_session_absolute_ttl_days=90),
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
    )
    assert created.result.session is not None
    session_id = UUID(created.result.session.principal.session_id or "")
    now = token_services.clock.now()

    assert uow.auth_sessions.purge_expired(before=now + timedelta(days=31)) == 1
    uow.commit()
    assert uow.auth_sessions.get_by_id(session_id) is None


def test_argon2_runs_outside_auth_write_transactions(
    uow: SqlAlchemyUnitOfWork, token_services, monkeypatch: pytest.MonkeyPatch
) -> None:
    import creator.application.auth as auth_module

    original_hash = auth_module.hash_password

    def checked_hash(password: str, settings: Settings) -> str:
        assert not uow._require_session().in_transaction()
        return original_hash(password, settings)

    monkeypatch.setattr(auth_module, "hash_password", checked_hash)
    created = signup(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        workspace_name="Workspace",
        token_services=token_services,
    )
    assert created.result.session is not None

    original_verify = auth_module.verify_password

    def checked_verify(password: str, password_hash: str | None) -> bool:
        assert not uow._require_session().in_transaction()
        return original_verify(password, password_hash)

    monkeypatch.setattr(auth_module, "verify_password", checked_verify)
    assert login(
        unit_of_work=uow,
        settings=_settings(),
        email="owner@example.com",
        password="correct-password",
        token_services=token_services,
    ).refresh_token


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
