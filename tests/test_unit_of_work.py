from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from creator.domain.exceptions import ConflictError, PersistenceError
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.uow import UnitOfWork


class RecordingSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0
        self.commit_error: Exception | None = None

    def commit(self) -> None:
        self.commits += 1
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


def session_factory(session: RecordingSession) -> Session:
    return cast(Session, session)


def test_unit_of_work_commits_only_when_explicitly_requested() -> None:
    session = RecordingSession()

    with SqlAlchemyUnitOfWork(lambda: session_factory(session)) as unit_of_work:
        unit_of_work.commit()

    assert session.commits == 1
    assert session.rollbacks == 0
    assert session.closes == 1


def test_unit_of_work_rolls_back_when_commit_is_not_requested() -> None:
    session = RecordingSession()

    with SqlAlchemyUnitOfWork(lambda: session_factory(session)):
        pass

    assert session.commits == 0
    assert session.rollbacks == 1
    assert session.closes == 1


def test_unit_of_work_rolls_back_after_exception() -> None:
    session = RecordingSession()

    with pytest.raises(RuntimeError), SqlAlchemyUnitOfWork(lambda: session_factory(session)):
        raise RuntimeError("boom")

    assert session.commits == 0
    assert session.rollbacks == 1
    assert session.closes == 1


def test_unit_of_work_maps_integrity_errors_to_domain_conflicts() -> None:
    session = RecordingSession()
    session.commit_error = IntegrityError("insert", {}, Exception("duplicate key unique"))

    with (
        pytest.raises(ConflictError),
        SqlAlchemyUnitOfWork(lambda: session_factory(session)) as unit_of_work,
    ):
        unit_of_work.commit()

    assert session.rollbacks == 2
    assert session.closes == 1


def test_unit_of_work_rejects_commit_outside_active_context() -> None:
    unit_of_work = SqlAlchemyUnitOfWork(lambda: session_factory(RecordingSession()))

    with pytest.raises(PersistenceError):
        unit_of_work.commit()


def test_sqlalchemy_unit_of_work_implements_the_protocol() -> None:
    """`mypy --strict` only enforces parity if the class inherits the Protocol.

    Before this assertion the concrete class and `creator.uow.UnitOfWork`
    declared the repository list twice and drifted independently, so a missing
    repository was a runtime `AttributeError` instead of a type error.
    """
    annotations = set(getattr(SqlAlchemyUnitOfWork, "__annotations__", {}))
    protocol = set(getattr(UnitOfWork, "__annotations__", {}))

    assert UnitOfWork in SqlAlchemyUnitOfWork.__mro__
    assert protocol <= annotations, protocol - annotations
    assert len(protocol) == 29


def test_unit_of_work_exposes_grouped_repositories_without_flat_aliases() -> None:
    with SqlAlchemyUnitOfWork(lambda: session_factory(RecordingSession())) as unit_of_work:
        assert unit_of_work.user.users is not None
        assert unit_of_work.user.settings is not None
        assert unit_of_work.workspace.invites is not None
        assert unit_of_work.brand.assets is not None
        assert unit_of_work.generation.image_jobs is not None
        assert unit_of_work.notification.preferences is not None
        assert unit_of_work.billing_account.addresses is not None
        assert unit_of_work.billing_provider.webhook_events is not None
        assert unit_of_work.coupon.redemptions is not None
        assert unit_of_work.subscription.history is not None
        assert unit_of_work.agent_workflow.workflows is not None
        assert unit_of_work.auth_sessions is not None
        assert unit_of_work.outbox is not None
        assert not hasattr(unit_of_work, "brands")
        assert not hasattr(unit_of_work, "image_generations")
