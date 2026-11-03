"""SQLAlchemy implementation of the brand persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.workspace.models as workspace_models
from creator.brand import models as brand_tables
from creator.brand.ports import (
    BrandAssetRecord,
    BrandColorRecord,
    BrandColorRepository,
    BrandRecord,
    BrandSettingsRecord,
)
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
from creator.infrastructure.persistence.sql import as_datetime as _datetime
from creator.infrastructure.persistence.sql import as_optional_datetime as _optional_datetime
from creator.infrastructure.persistence.sql import json_object as _json
from creator.infrastructure.persistence.sql import now as _now
from creator.infrastructure.persistence.sql import scoped_resource_select as _scoped_resource_select
from creator.infrastructure.persistence.sql import (
    user_has_workspace_role as _user_has_workspace_role,
)
from creator.workspace import models as workspace_tables


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


def _brand_settings_record(row: brand_tables.BrandSettings) -> BrandSettingsRecord:
    return BrandSettingsRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        brand_id=row.brand_id,
        voice_settings=_json(row.voice_settings),
        visual_settings=_json(row.visual_settings),
        generation_defaults=_json(row.generation_defaults),
        metadata=_json(row.metadata_json),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


class SqlAlchemyBrandSettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_user(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        include_deleted: bool = False,
    ) -> BrandSettingsRecord | None:
        statement = self._scoped_select(user_id).where(
            brand_tables.BrandSettings.brand_id == brand_id
        )
        if not include_deleted:
            statement = statement.where(brand_tables.BrandSettings.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _brand_settings_record(row) if row else None

    def upsert(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        brand_id: UUID,
        voice_settings: JsonObject | None = None,
        visual_settings: JsonObject | None = None,
        generation_defaults: JsonObject | None = None,
        metadata: JsonObject | None = None,
    ) -> BrandSettingsRecord:
        if not _user_has_workspace_role(
            self._session,
            user_id=user_id,
            workspace_id=workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Brand not found")
        row = self._session.scalars(
            select(brand_tables.BrandSettings).where(
                brand_tables.BrandSettings.brand_id == brand_id
            )
        ).one_or_none()
        if row is None:
            row = brand_tables.BrandSettings(
                workspace_id=workspace_id,
                brand_id=brand_id,
                voice_settings=_json(voice_settings),
                visual_settings=_json(visual_settings),
                generation_defaults=_json(generation_defaults),
                metadata_json=_json(metadata),
            )
            self._session.add(row)
        else:
            row.deleted_at = None
            if voice_settings is not None:
                row.voice_settings = _json(voice_settings)
            if visual_settings is not None:
                row.visual_settings = _json(visual_settings)
            if generation_defaults is not None:
                row.generation_defaults = _json(generation_defaults)
            if metadata is not None:
                row.metadata_json = _json(metadata)
            row.updated_at = _now()
        flush_or_raise(self._session)
        return _brand_settings_record(row)

    def update(
        self,
        *,
        user_id: UUID,
        brand_id: UUID,
        voice_settings: JsonObject | None = None,
        visual_settings: JsonObject | None = None,
        generation_defaults: JsonObject | None = None,
        metadata: JsonObject | None = None,
    ) -> BrandSettingsRecord:
        row = self._writable_settings(user_id=user_id, brand_id=brand_id)
        if voice_settings is not None:
            row.voice_settings = _json(voice_settings)
        if visual_settings is not None:
            row.visual_settings = _json(visual_settings)
        if generation_defaults is not None:
            row.generation_defaults = _json(generation_defaults)
        if metadata is not None:
            row.metadata_json = _json(metadata)
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _brand_settings_record(row)

    def soft_delete(self, *, user_id: UUID, brand_id: UUID) -> None:
        row = self._writable_settings(user_id=user_id, brand_id=brand_id)
        timestamp = _now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        flush_or_raise(self._session)

    def _writable_settings(self, *, user_id: UUID, brand_id: UUID) -> brand_tables.BrandSettings:
        row = self._session.scalars(
            self._scoped_select(user_id).where(
                brand_tables.BrandSettings.brand_id == brand_id,
                brand_tables.BrandSettings.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None or not _user_has_workspace_role(
            self._session,
            user_id=user_id,
            workspace_id=row.workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Brand settings not found")
        return cast(brand_tables.BrandSettings, row)

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_select(user_id, brand_tables.BrandSettings)


def _brand_asset_record(row: brand_tables.BrandAsset) -> BrandAssetRecord:
    return BrandAssetRecord(
        id=row.id,
        brand_id=row.brand_id,
        type=row.type,
        file_url=row.file_url,
        file_name=row.file_name,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyBrandAssetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        brand_id: UUID,
        type: str,
        file_url: str,
        file_name: str | None = None,
        description: str | None = None,
    ) -> BrandAssetRecord:
        row = brand_tables.BrandAsset(
            brand_id=brand_id,
            type=type,
            file_url=file_url,
            file_name=file_name,
            description=description,
        )
        self._session.add(row)
        self._session.flush()
        return _brand_asset_record(row)

    def get_for_user(self, *, user_id: UUID, asset_id: UUID) -> BrandAssetRecord | None:
        row = self._session.scalars(
            self._select(user_id).where(brand_tables.BrandAsset.id == asset_id)
        ).one_or_none()
        return _brand_asset_record(row) if row else None

    def list_for_user(
        self,
        *,
        user_id: UUID,
        brand_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[BrandAssetRecord]:
        page = page or PageRequest()
        statement = self._select(user_id)
        count = (
            select(func.count())
            .select_from(brand_tables.BrandAsset)
            .join(brand_tables.Brand, brand_tables.Brand.id == brand_tables.BrandAsset.brand_id)
            .join(
                workspace_tables.WorkspaceMembership,
                workspace_tables.WorkspaceMembership.workspace_id
                == brand_tables.Brand.workspace_id,
            )
            .where(
                workspace_tables.WorkspaceMembership.user_id == user_id,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                brand_tables.BrandAsset.deleted_at.is_(None),
                brand_tables.Brand.deleted_at.is_(None),
            )
        )
        if brand_id is not None:
            statement = statement.where(brand_tables.BrandAsset.brand_id == brand_id)
            count = count.where(brand_tables.BrandAsset.brand_id == brand_id)
        order = (
            asc(brand_tables.BrandAsset.created_at)
            if page.sort == "asc"
            else desc(brand_tables.BrandAsset.created_at)
        )
        rows = self._session.scalars(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        return Page(
            items=[_brand_asset_record(row) for row in rows],
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def update(self, *, asset_id: UUID, fields: dict[str, object]) -> BrandAssetRecord:
        row = self._session.get(brand_tables.BrandAsset, asset_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Brand asset not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _brand_asset_record(row)

    def soft_delete(self, *, asset_id: UUID) -> None:
        row = self._session.get(brand_tables.BrandAsset, asset_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Brand asset not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()

    def _select(self, user_id: UUID) -> Select[brand_tables.BrandAsset]:
        return (
            select(brand_tables.BrandAsset)
            .join(brand_tables.Brand, brand_tables.Brand.id == brand_tables.BrandAsset.brand_id)
            .join(
                workspace_tables.WorkspaceMembership,
                workspace_tables.WorkspaceMembership.workspace_id
                == brand_tables.Brand.workspace_id,
            )
            .where(
                workspace_tables.WorkspaceMembership.user_id == user_id,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                brand_tables.BrandAsset.deleted_at.is_(None),
                brand_tables.Brand.deleted_at.is_(None),
            )
        )
