from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException, Request

from creator.api.dependencies import get_current_user, get_principal
from creator.config import Settings, get_settings
from creator.domain.auth import Principal
from creator.infrastructure.database.db import get_db
from creator.infrastructure.runtime import queue as queue_module
from creator.infrastructure.runtime.queue import get_generation_queue
from creator.services.agents.factory import UnconfiguredMultiAgentOrchestrator
from creator.services.ai.factory import UnconfiguredLLMProvider
from creator.services.retrieval.factory import (
    UnconfiguredEmbeddingProvider,
    UnconfiguredSemanticRetriever,
    UnconfiguredToolCallingProvider,
)


def test_settings_are_cached() -> None:
    assert get_settings() is get_settings()


SECRET = "test-local-auth-jwt-secret-with-32-bytes"


def local_token(*, subject: str = "00000000-0000-0000-0000-000000000001") -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "creator",
            "aud": "creator-api",
            "sub": subject,
            "session_id": "00000000-0000-0000-0000-000000000099",
            "role": "membro",
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        SECRET,
        algorithm="HS256",
    )


def cookie_request(token: str | None = None, *, authorization: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if token is not None:
        headers.append((b"cookie", f"creator_access={token}".encode()))
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return Request({"type": "http", "headers": headers})


def test_required_auth_without_configuration_fails_closed() -> None:
    with pytest.raises(HTTPException) as error:
        get_principal(cookie_request("token"), Settings(_env_file=None, auth_required=True))

    assert error.value.status_code == 500
    assert error.value.detail["code"] == "AUTHENTICATION_MISCONFIGURED"


def test_optional_auth_without_configuration_returns_none() -> None:
    assert (
        get_principal(cookie_request("token"), Settings(_env_file=None, auth_required=False))
        is None
    )


def test_optional_auth_without_credentials_returns_none() -> None:
    assert get_principal(cookie_request(), Settings(auth_required=False)) is None


def test_principal_is_created_from_local_token() -> None:
    principal = get_principal(
        cookie_request(local_token()),
        Settings(_env_file=None, auth_required=True, auth_jwt_secret=SECRET),
    )

    assert principal is not None
    assert principal.subject == "00000000-0000-0000-0000-000000000001"
    assert principal.session_id == "00000000-0000-0000-0000-000000000099"


def test_invalid_cookie_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        get_principal(
            cookie_request("not-a-jwt"),
            Settings(_env_file=None, auth_required=True, auth_jwt_secret=SECRET),
        )

    assert error.value.status_code == 401


def test_current_user_requires_active_session() -> None:
    user = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        external_id="local:test",
        email="person@example.com",
        display_name="Person",
        deleted_at=None,
    )

    class FakeUsers:
        def get_by_id(self, user_id: object, *, include_deleted: bool) -> SimpleNamespace:
            return user

    class FakeAuthSessions:
        def get_by_id(self, session_id: object) -> SimpleNamespace:
            return SimpleNamespace(
                revoked_at=None, expires_at=datetime.now(UTC) + timedelta(days=1)
            )

    class FakeUnitOfWork:
        users = FakeUsers()
        auth_sessions = FakeAuthSessions()

    principal = Principal(
        subject="00000000-0000-0000-0000-000000000001",
        session_id="00000000-0000-0000-0000-000000000099",
    )

    assert get_current_user(principal, FakeUnitOfWork()) is user


def test_current_user_rejects_revoked_session() -> None:
    class FakeUsers:
        def get_by_id(self, user_id: object, *, include_deleted: bool) -> None:
            return None

    class FakeAuthSessions:
        def get_by_id(self, session_id: object) -> SimpleNamespace:
            return SimpleNamespace(
                revoked_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )

    class FakeUnitOfWork:
        users = FakeUsers()
        auth_sessions = FakeAuthSessions()

    with pytest.raises(HTTPException) as error:
        get_current_user(
            Principal(
                subject="00000000-0000-0000-0000-000000000001",
                session_id="00000000-0000-0000-0000-000000000099",
            ),
            FakeUnitOfWork(),
        )

    assert error.value.status_code == 401


def test_current_user_rejects_missing_principal() -> None:
    with pytest.raises(HTTPException) as error:
        get_current_user(None, SimpleNamespace())

    assert error.value.status_code == 401


def test_missing_required_auth_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        get_principal(cookie_request(), Settings(auth_required=True))

    assert error.value.status_code == 401


def test_authorization_header_does_not_authenticate() -> None:
    with pytest.raises(HTTPException) as error:
        get_principal(
            cookie_request(authorization=f"Bearer {local_token()}"),
            Settings(_env_file=None, auth_required=True, auth_jwt_secret=SECRET),
        )

    assert error.value.status_code == 401


def test_db_dependency_yields_a_session() -> None:
    session: Iterator[object] = get_db()

    assert next(session).__class__.__name__ == "Session"
    session.close()


def test_queue_factory_uses_generation_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        queue_module,
        "get_settings",
        lambda: Settings(_env_file=None),
    )
    queue = get_generation_queue()

    assert queue.name == "creator:rq:generations"


def test_unconfigured_provider_is_explicit() -> None:
    assert isinstance(UnconfiguredLLMProvider(), UnconfiguredLLMProvider)


def test_unconfigured_multi_agent_orchestrator_is_explicit() -> None:
    assert isinstance(UnconfiguredMultiAgentOrchestrator(), UnconfiguredMultiAgentOrchestrator)


def test_unconfigured_retrieval_providers_are_explicit() -> None:
    assert isinstance(UnconfiguredEmbeddingProvider(), UnconfiguredEmbeddingProvider)
    assert isinstance(UnconfiguredSemanticRetriever(), UnconfiguredSemanticRetriever)
    assert isinstance(UnconfiguredToolCallingProvider(), UnconfiguredToolCallingProvider)
