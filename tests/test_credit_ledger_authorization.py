"""Authorization for the Credit Transaction reads (issue #162).

CONTEXT.md: a Principal reaches Workspace data only through a Membership. The
final modeling replaced ``deleted_at`` with ``status`` (``member_status``), so the
read path has to filter ``status = ACTIVE`` instead of ``deleted_at IS NULL``.
Without that filter a Member who was removed or suspended keeps reading the
Workspace's Credit Wallet ledger, which is exactly the leak these tests fail on.

The ledger is seeded through the mapped table because the pending alignment
changes ``transaction_type`` into ``type`` and adds ``balance_after``; the
authorization filter must not depend on that shape, so the helper fills whichever
required columns the model declares.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from creator.credit.models import WorkspaceCreditTransaction
from creator.credit.repository import SqlAlchemyWorkspaceCreditTransactionRepository
from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.enums import MemberStatus, WorkspaceRole
from creator.user.models import User
from creator.workspace.models import Workspace, WorkspaceMembership


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _seed_user(session: Session) -> UUID:
    user_id = uuid4()
    session.add(
        User(
            id=user_id,
            auth_provider_id=None,
            display_name="Ledger Reader",
            global_role="membro",
        )
    )
    session.flush()
    return user_id


def _seed_workspace(session: Session, *, deleted_at: datetime | None = None) -> UUID:
    workspace_id = uuid4()
    session.add(Workspace(id=workspace_id, name="Credit Ledger", deleted_at=deleted_at))
    session.flush()
    return workspace_id


def _seed_membership(session: Session, *, workspace_id: UUID, user_id: UUID, status: str) -> None:
    session.add(
        WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=user_id,
            role=WorkspaceRole.OWNER,
            status=status,
        )
    )
    session.flush()


def _insert_ledger_entry(session: Session, *, workspace_id: UUID, amount: int = 100) -> UUID:
    """Seed one ledger row without depending on the column shape under migration."""
    table = WorkspaceCreditTransaction.__table__
    transaction_id = uuid4()
    values: dict[str, object] = {
        "id": transaction_id,
        "workspace_id": workspace_id,
        "amount": amount,
    }
    for column in table.columns:
        if column.name in values or column.primary_key or column.nullable:
            continue
        if column.server_default is not None:
            continue
        if column.name == "balance_after":
            values[column.name] = amount
        elif column.name in {"type", "transaction_type"}:
            values[column.name] = "TOP_UP"
        else:
            raise AssertionError(
                f"unexpected required column {column.name!r} on "
                "workspace_credit_transactions; extend the seed helper"
            )
    session.execute(table.insert().values(**values))
    session.flush()
    return transaction_id


@pytest.mark.parametrize("status", [MemberStatus.REMOVED, MemberStatus.SUSPENDED])
def test_inactive_membership_cannot_list_or_get_a_credit_transaction(
    session: Session, status: str
) -> None:
    workspace_id = _seed_workspace(session)
    inactive_user = _seed_user(session)
    _seed_membership(session, workspace_id=workspace_id, user_id=inactive_user, status=str(status))
    transaction_id = _insert_ledger_entry(session, workspace_id=workspace_id)

    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    listed = repository.list_for_user(user_id=inactive_user)
    assert listed == [], (
        f"a Workspace Membership with status={status!r} must not read the credit ledger; "
        f"got {len(listed)} transaction(s)"
    )

    fetched = repository.get_for_user(user_id=inactive_user, transaction_id=transaction_id)
    assert fetched is None, (
        f"a Workspace Membership with status={status!r} must not read a credit "
        f"transaction by id; got {fetched!r}"
    )


@pytest.mark.parametrize("status", [MemberStatus.REMOVED, MemberStatus.SUSPENDED])
def test_inactive_membership_is_denied_even_with_a_workspace_filter(
    session: Session, status: str
) -> None:
    workspace_id = _seed_workspace(session)
    inactive_user = _seed_user(session)
    _seed_membership(session, workspace_id=workspace_id, user_id=inactive_user, status=str(status))
    _insert_ledger_entry(session, workspace_id=workspace_id)

    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    listed = repository.list_for_user(user_id=inactive_user, workspace_id=workspace_id)
    assert listed == [], (
        "asking for the exact workspace must not bypass the Membership status check; "
        f"got {len(listed)} transaction(s)"
    )


def test_active_membership_still_reads_its_ledger(session: Session) -> None:
    """The status filter must not hide the ledger from an authorized member."""
    workspace_id = _seed_workspace(session)
    active_user = _seed_user(session)
    _seed_membership(
        session, workspace_id=workspace_id, user_id=active_user, status=MemberStatus.ACTIVE
    )
    transaction_id = _insert_ledger_entry(session, workspace_id=workspace_id)

    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    listed = repository.list_for_user(user_id=active_user)
    assert [record.id for record in listed] == [transaction_id], (
        "an ACTIVE member must keep reading the Workspace credit ledger; got "
        f"{[record.id for record in listed]}"
    )

    fetched = repository.get_for_user(user_id=active_user, transaction_id=transaction_id)
    assert fetched is not None and fetched.id == transaction_id


def test_member_without_a_membership_cannot_read_the_ledger(session: Session) -> None:
    """No Membership at all is the baseline denial the status filter relies on."""
    workspace_id = _seed_workspace(session)
    outsider = _seed_user(session)
    _insert_ledger_entry(session, workspace_id=workspace_id)

    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    assert repository.list_for_user(user_id=outsider) == []


def test_deleted_workspace_ledger_is_not_readable(session: Session) -> None:
    """A soft-deleted Workspace must not expose its Credit Wallet.

    ``Workspace.deleted_at`` is the Workspace-level soft delete (CONTEXT.md, Soft
    Delete). A Membership row that is still ``ACTIVE`` — because the Workspace was
    deleted before the memberships were cleaned up — must not turn into a read
    grant: the repository has to require a live Workspace as well as an ACTIVE
    Membership.
    """
    workspace_id = _seed_workspace(session, deleted_at=datetime(2026, 1, 1, tzinfo=UTC))
    user_id = _seed_user(session)
    _seed_membership(
        session, workspace_id=workspace_id, user_id=user_id, status=MemberStatus.ACTIVE
    )
    transaction_id = _insert_ledger_entry(session, workspace_id=workspace_id)

    repository = SqlAlchemyWorkspaceCreditTransactionRepository(session)

    listed = repository.list_for_user(user_id=user_id)
    assert listed == [], (
        "a soft-deleted Workspace must not expose its credit ledger even to an ACTIVE "
        f"member; got {len(listed)} transaction(s)"
    )

    fetched = repository.get_for_user(user_id=user_id, transaction_id=transaction_id)
    assert fetched is None, (
        f"a soft-deleted Workspace must not expose a credit transaction by id; got {fetched!r}"
    )
