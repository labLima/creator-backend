"""SQLAlchemy implementation of the brand persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.workspace.models as workspace_models
from creator.brand.ports import BrandColorRecord, BrandColorRepository, BrandRecord
from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.domain.exceptions import EntityNotFoundError
from creator.infrastructure.persistence.sql import (
    as_datetime,
    as_optional_datetime,
    flush_or_raise,
    json_object,
    now,
    paginate,
    scoped_resource_count,
    scoped_resource_select,
    user_has_workspace_role,
)


def _brand_record(row: brand_models.Brand) -> BrandRecord:
    return BrandRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        created_by_user_id=row.created_by_user_id,
        name=row.name,
        description=row.description,
        brand_voice=row.brand_voice,
        metadata=json_object(row.metadata_json),
        created_at=as_datetime(row.created_at),
        updated_at=as_datetime(row.updated_at),
        deleted_at=as_optional_datetime(row.deleted_at),
    )


class SqlAlchemyBrandRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        workspace_id: UUID,
        created_by_user_id: UUID | None,
        name: str,
        description: str | None = None,
        brand_voice: str | None = None,
        metadata: JsonObject | None = None,
    ) -> BrandRecord:
        if created_by_user_id is not None and not user_has_workspace_role(
            self._session,
            user_id=created_by_user_id,
            workspace_id=workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Workspace not found")
        row = brand_models.Brand(
            workspace_id=workspace_id,
            created_by_user_id=created_by_user_id,
            name=name,
            description=description,
            brand_voice=brand_voice,
            metadata_json=json_object(metadata),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _brand_record(row)

    def get_for_user(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        include_deleted: bool = False,
    ) -> BrandRecord | None:
        statement = self._scoped_select(user_id).where(brand_models.Brand.id == brand_id)
        if not include_deleted:
            statement = statement.where(brand_models.Brand.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _brand_record(row) if row else None

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[BrandRecord]:
        page = page or PageRequest()
        statement = self._scoped_select(user_id).where(brand_models.Brand.deleted_at.is_(None))
        count_statement = self._scoped_count(user_id).where(brand_models.Brand.deleted_at.is_(None))
        if workspace_id is not None:
            statement = statement.where(brand_models.Brand.workspace_id == workspace_id)
            count_statement = count_statement.where(brand_models.Brand.workspace_id == workspace_id)
        rows, total = paginate(
            self._session, statement, count_statement, brand_models.Brand.created_at, page
        )
        return Page(
            items=[_brand_record(row) for row in rows],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def update(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        name: str | None = None,
        description: str | None = None,
        brand_voice: str | None = None,
        metadata: JsonObject | None = None,
    ) -> BrandRecord:
        row = self._writable_brand(user_id=user_id, brand_id=brand_id)
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        if brand_voice is not None:
            row.brand_voice = brand_voice
        if metadata is not None:
            row.metadata_json = json_object(metadata)
        row.updated_at = now()
        flush_or_raise(self._session)
        return _brand_record(row)

    def soft_delete(self, *, user_id: UUID, brand_id: UUID) -> None:
        row = self._writable_brand(user_id=user_id, brand_id=brand_id)
        timestamp = now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        flush_or_raise(self._session)

    def _writable_brand(self, *, user_id: UUID, brand_id: UUID) -> brand_models.Brand:
        row = self._session.scalars(
            self._scoped_select(user_id).where(
                brand_models.Brand.id == brand_id,
                brand_models.Brand.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None or not user_has_workspace_role(
            self._session,
            user_id=user_id,
            workspace_id=row.workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Brand not found")
        return cast(brand_models.Brand, row)

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return scoped_resource_select(user_id, brand_models.Brand)

    def _scoped_count(self, user_id: UUID) -> Select[Any]:
        return scoped_resource_count(user_id, brand_models.Brand)


class SqlAlchemyBrandColorRepository(BrandColorRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x):
        return BrandColorRecord(
            x.id,
            x.brand_id,
            x.workspace_id,
            x.created_by,
            x.order,
            x.color_name,
            x.hex_code,
            x.created_at,
            x.updated_at,
            x.deleted_at,
        )

    def _q(self, uid):
        return (
            select(brand_models.BrandColor)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.BrandColor.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == uid,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                brand_models.BrandColor.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id, brand_id=None):
        q = self._q(user_id)
        if brand_id is not None:
            q = q.where(brand_models.BrandColor.brand_id == brand_id)
        return [self._r(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id, color_id):
        x = self.s.scalar(self._q(user_id).where(brand_models.BrandColor.id == color_id))
        return self._r(x) if x else None

    def add(self, *, fields):
        x = brand_models.BrandColor(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, color_id, fields):
        x = self.s.get(brand_models.BrandColor, color_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Brand color not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, color_id):
        x = self.s.get(brand_models.BrandColor, color_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Brand color not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
