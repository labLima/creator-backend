"""Generic SQLAlchemy helpers shared by every capability repository.

This module may never import a repository port or implementation: it is the
bottom of the persistence stack, so capabilities can depend on it freely.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, and_, asc, desc, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from creator.core.pagination import PageRequest
from creator.core.types import JsonObject
from creator.domain.exceptions import ConcurrencyError, ConflictError, PersistenceError
from creator.workspace import models as workspace_tables


def now() -> datetime:
    return datetime.now(UTC)


def enum_value(value: object) -> str:
    return cast(str, getattr(value, "value", value))


def as_datetime(value: object) -> datetime:
    return cast(datetime, value)


def as_optional_datetime(value: object | None) -> datetime | None:
    return cast(datetime | None, value)


def json_object(value: dict[str, object] | None) -> JsonObject:
    return dict(value or {})


def map_sqlalchemy_error(error: SQLAlchemyError) -> PersistenceError:
    if isinstance(error, IntegrityError):
        message = str(error.orig).lower()
        if "unique" in message or "duplicate" in message:
            return ConflictError(str(error.orig))
        return ConcurrencyError(str(error.orig))
    return PersistenceError(str(error))


def flush_or_raise(session: Session) -> None:
    try:
        session.flush()
    except SQLAlchemyError as error:
        raise map_sqlalchemy_error(error) from error


def scoped_resource_select(user_id: UUID, model: type[Any]) -> Select[Any]:
    return (
        select(model)
        .join(
            workspace_tables.WorkspaceMembership,
            and_(
                workspace_tables.WorkspaceMembership.workspace_id == model.workspace_id,
                workspace_tables.WorkspaceMembership.user_id == user_id,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
            ),
        )
        .join(
            workspace_tables.Workspace,
            and_(
                workspace_tables.Workspace.id == model.workspace_id,
                workspace_tables.Workspace.deleted_at.is_(None),
            ),
        )
    )


def scoped_resource_count(user_id: UUID, model: type[Any]) -> Select[Any]:
    return (
        select(func.count())
        .select_from(model)
        .join(
            workspace_tables.WorkspaceMembership,
            and_(
                workspace_tables.WorkspaceMembership.workspace_id == model.workspace_id,
                workspace_tables.WorkspaceMembership.user_id == user_id,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
            ),
        )
        .join(
            workspace_tables.Workspace,
            and_(
                workspace_tables.Workspace.id == model.workspace_id,
                workspace_tables.Workspace.deleted_at.is_(None),
            ),
        )
    )


def paginate(
    session: Session,
    statement: Select[Any],
    count_statement: Select[Any],
    order_by: Any,
    page: PageRequest,
) -> tuple[list[Any], int]:
    order_column = asc(order_by) if page.sort == "asc" else desc(order_by)
    rows = session.scalars(
        statement.order_by(order_column).offset(page.offset).limit(page.limit)
    ).all()
    total: int = session.execute(count_statement).scalar_one()
    return list(rows), total
