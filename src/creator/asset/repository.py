"""SQLAlchemy repositories for the asset capability."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.orm import Session

from creator.asset import models as asset_tables
from creator.asset.ports import AssetRecord
from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.domain.exceptions import EntityNotFoundError
from creator.infrastructure.persistence.sql import as_datetime as _datetime
from creator.infrastructure.persistence.sql import as_optional_datetime as _optional_datetime
from creator.infrastructure.persistence.sql import flush_or_raise
from creator.infrastructure.persistence.sql import json_object as _json
from creator.infrastructure.persistence.sql import now as _now
from creator.infrastructure.persistence.sql import paginate as _page
from creator.infrastructure.persistence.sql import scoped_resource_count as _scoped_resource_count
from creator.infrastructure.persistence.sql import scoped_resource_select as _scoped_resource_select
from creator.infrastructure.persistence.sql import (
    user_has_workspace_role as _user_has_workspace_role,
)


def _asset_record(row: asset_tables.Asset) -> AssetRecord:
    return AssetRecord(
        id=row.id,
        workspace_id=row.workspace_id,
        brand_id=row.brand_id,
        project_id=row.project_id,
        content_id=row.content_id,
        uploaded_by_user_id=row.uploaded_by_user_id,
        asset_type=row.asset_type,
        storage_path=row.storage_path,
        public_url=row.public_url,
        mime_type=row.mime_type,
        byte_size=row.byte_size,
        checksum=row.checksum,
        metadata=_json(row.metadata_json),
        created_at=_datetime(row.created_at),
        updated_at=_datetime(row.updated_at),
        deleted_at=_optional_datetime(row.deleted_at),
    )


class SqlAlchemyAssetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        workspace_id: UUID,
        uploaded_by_user_id: UUID | None,
        asset_type: str,
        storage_path: str,
        mime_type: str,
        byte_size: int,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        content_id: UUID | None = None,
        public_url: str | None = None,
        checksum: str | None = None,
        metadata: JsonObject | None = None,
    ) -> AssetRecord:
        if uploaded_by_user_id is not None and not _user_has_workspace_role(
            self._session,
            user_id=uploaded_by_user_id,
            workspace_id=workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Workspace not found")
        row = asset_tables.Asset(
            workspace_id=workspace_id,
            brand_id=brand_id,
            project_id=project_id,
            content_id=content_id,
            uploaded_by_user_id=uploaded_by_user_id,
            asset_type=asset_type,
            storage_path=storage_path,
            public_url=public_url,
            mime_type=mime_type,
            byte_size=byte_size,
            checksum=checksum,
            metadata_json=_json(metadata),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _asset_record(row)

    def get_for_user(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        include_deleted: bool = False,
    ) -> AssetRecord | None:
        statement = self._scoped_select(user_id).where(asset_tables.Asset.id == asset_id)
        if not include_deleted:
            statement = statement.where(asset_tables.Asset.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _asset_record(row) if row else None

    def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        brand_id: UUID | None = None,
        project_id: UUID | None = None,
        content_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[AssetRecord]:
        page = page or PageRequest()
        statement = self._scoped_select(user_id).where(asset_tables.Asset.deleted_at.is_(None))
        count_statement = self._scoped_count(user_id).where(asset_tables.Asset.deleted_at.is_(None))
        for column, value in [
            (asset_tables.Asset.workspace_id, workspace_id),
            (asset_tables.Asset.brand_id, brand_id),
            (asset_tables.Asset.project_id, project_id),
            (asset_tables.Asset.content_id, content_id),
        ]:
            if value is not None:
                statement = statement.where(column == value)
                count_statement = count_statement.where(column == value)
        rows, total = _page(
            self._session, statement, count_statement, asset_tables.Asset.created_at, page
        )
        return Page(
            items=[_asset_record(row) for row in rows],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def update(
        self,
        *,
        user_id: UUID,
        asset_id: UUID,
        asset_type: str | None = None,
        public_url: str | None = None,
        metadata: JsonObject | None = None,
    ) -> AssetRecord:
        row = self._writable_asset(user_id=user_id, asset_id=asset_id)
        if asset_type is not None:
            row.asset_type = asset_type
        if public_url is not None:
            row.public_url = public_url
        if metadata is not None:
            row.metadata_json = _json(metadata)
        row.updated_at = _now()
        flush_or_raise(self._session)
        return _asset_record(row)

    def soft_delete(self, *, user_id: UUID, asset_id: UUID) -> None:
        row = self._writable_asset(user_id=user_id, asset_id=asset_id)
        timestamp = _now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        flush_or_raise(self._session)

    def _writable_asset(self, *, user_id: UUID, asset_id: UUID) -> asset_tables.Asset:
        row = self._session.scalars(
            self._scoped_select(user_id).where(
                asset_tables.Asset.id == asset_id,
                asset_tables.Asset.deleted_at.is_(None),
            )
        ).one_or_none()
        if row is None or not _user_has_workspace_role(
            self._session,
            user_id=user_id,
            workspace_id=row.workspace_id,
            minimum_role="editor",
        ):
            raise EntityNotFoundError("Asset not found")
        return cast(asset_tables.Asset, row)

    def _scoped_select(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_select(user_id, asset_tables.Asset)

    def _scoped_count(self, user_id: UUID) -> Select[Any]:
        return _scoped_resource_count(user_id, asset_tables.Asset)
