"""The two derived credit measures of ADR-019 must be reachable as a port.

The final modeling keeps ``workspace_credit_balance`` and
``workspace_credit_lot_available`` as database functions. SQLite has no place to
put them (they are derived reads, not triggers), so T20 exposes them through
``WorkspaceCreditTransactionRepository`` and this file proves the semantics match
the dump: available credit is the sum of the *non-expired* lots, and an expired
lot reports zero even though its row and its grant stay in the ledger.

A Credit Lot is tenant scoped (ADR-019 decision 6, ADR-030), so the availability
read takes the Workspace as well as the lot::

    WorkspaceCreditTransactionRepository.lot_available(workspace_id: UUID, lot_id: UUID) -> int

A lot identifier alone must never be enough to read another Workspace's
availability, exactly like ``workspace_balance``, which already takes the
Workspace. The final modeling's ``workspace_credit_lot_available(p_lot_id)`` did
not carry that filter because PostgreSQL RLS is not part of this port.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from creator.credit.models import WorkspaceCreditLot, WorkspaceCreditTransaction
from creator.credit.ports import WorkspaceCreditTransactionRepository
from creator.credit.repository import SqlAlchemyWorkspaceCreditTransactionRepository
from creator.infrastructure.database import metadata as _metadata  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.workspace.models import Workspace

NOW = datetime.now(UTC)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def _grant(session: Session, *, workspace_id: UUID, amount: int, balance_after: int) -> UUID:
    transaction = WorkspaceCreditTransaction(
        id=uuid4(),
        workspace_id=workspace_id,
        amount=amount,
        balance_after=balance_after,
        type="TOP_UP",
    )
    session.add(transaction)
    session.flush()
    return transaction.id


def _lot(
    session: Session,
    *,
    workspace_id: UUID,
    grant_transaction_id: UUID,
    original_amount: int,
    remaining_amount: int,
    expires_at: datetime | None = None,
) -> UUID:
    lot = WorkspaceCreditLot(
        id=uuid4(),
        workspace_id=workspace_id,
        grant_transaction_id=grant_transaction_id,
        original_amount=original_amount,
        remaining_amount=remaining_amount,
        expires_at=expires_at,
    )
    session.add(lot)
    session.flush()
    return lot.id


def _seed(session: Session) -> tuple[UUID, UUID, UUID, UUID]:
    """One never-expiring, one future and one expired lot in the same workspace."""
    workspace = Workspace(id=uuid4(), name="Credit Measures")
    session.add(workspace)
    session.flush()

    active = _lot(
        session,
        workspace_id=workspace.id,
        grant_transaction_id=_grant(
            session, workspace_id=workspace.id, amount=100, balance_after=100
        ),
        original_amount=100,
        remaining_amount=30,
    )
    future = _lot(
        session,
        workspace_id=workspace.id,
        grant_transaction_id=_grant(
            session, workspace_id=workspace.id, amount=100, balance_after=200
        ),
        original_amount=100,
        remaining_amount=5,
        expires_at=NOW + timedelta(days=1),
    )
    expired = _lot(
        session,
        workspace_id=workspace.id,
        grant_transaction_id=_grant(
            session, workspace_id=workspace.id, amount=100, balance_after=300
        ),
        original_amount=100,
        remaining_amount=100,
        expires_at=NOW - timedelta(days=1),
    )
    session.commit()
    return workspace.id, active, future, expired


def test_workspace_balance_counts_only_the_non_expired_lots(session: Session) -> None:
    workspace_id, _active, _future, _expired = _seed(session)
    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    balance = repository.workspace_balance(workspace_id)

    persisted = sum(
        lot.remaining_amount
        for lot in session.query(WorkspaceCreditLot)
        .filter(WorkspaceCreditLot.workspace_id == workspace_id)
        .all()
    )
    assert persisted == 135, (
        "the fixture must separate the two measures: 135 persisted against 35 available"
    )
    assert balance == 35, (
        "the expired lot (100 remaining) must not count, and expires_at in the future must; "
        f"got {balance}"
    )


def test_workspace_balance_of_an_unknown_workspace_is_zero(session: Session) -> None:
    workspace_id, _active, _future, _expired = _seed(session)
    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    assert repository.workspace_balance(uuid4()) == 0
    assert repository.workspace_balance(workspace_id) > 0, "the seeded workspace must have credit"


def test_lot_available_reports_remaining_amount_of_a_live_lot(session: Session) -> None:
    workspace_id, active, future, _expired = _seed(session)
    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    assert repository.lot_available(workspace_id, active) == 30
    assert repository.lot_available(workspace_id, future) == 5


def test_lot_available_is_zero_for_an_expired_or_unknown_lot(session: Session) -> None:
    workspace_id, _active, _future, expired = _seed(session)
    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    assert repository.lot_available(workspace_id, expired) == 0, (
        "an expired lot still keeps remaining_amount = 100 in the row, but its availability is zero"
    )
    assert repository.lot_available(workspace_id, uuid4()) == 0


def test_lot_available_is_scoped_to_the_workspace(session: Session) -> None:
    """A Credit Lot belongs to one Workspace; the identifier alone is not authority.

    The API boundary derives the Workspace from the authenticated Principal
    (ADR-019 decision 6). A read that accepts only a lot id cannot enforce that, so
    the port takes both and treats a foreign lot as unavailable.
    """
    workspace_id, _active, _future, _expired = _seed(session)
    other_workspace = Workspace(id=uuid4(), name="Other Credit Workspace")
    session.add(other_workspace)
    session.flush()
    foreign_lot = _lot(
        session,
        workspace_id=other_workspace.id,
        grant_transaction_id=_grant(
            session, workspace_id=other_workspace.id, amount=100, balance_after=100
        ),
        original_amount=100,
        remaining_amount=100,
    )
    session.commit()

    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    assert repository.lot_available(other_workspace.id, foreign_lot) == 100, (
        "the owning Workspace must still read its own lot"
    )
    assert repository.lot_available(workspace_id, foreign_lot) == 0, (
        "a lot of another Workspace must read as unavailable, not as 100 credits the caller "
        "may spend"
    )


def test_lot_available_port_signature_is_tenant_scoped() -> None:
    """The port itself must require the Workspace, not only the lot id."""
    parameters = list(
        inspect.signature(WorkspaceCreditTransactionRepository.lot_available).parameters
    )

    assert parameters == ["self", "workspace_id", "lot_id"], (
        "WorkspaceCreditTransactionRepository.lot_available must be declared as "
        "lot_available(self, workspace_id: UUID, lot_id: UUID) -> int so a caller cannot read "
        f"another tenant's availability with the identifier alone; got {parameters}"
    )
