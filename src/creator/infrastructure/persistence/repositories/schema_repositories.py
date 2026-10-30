"""Repository ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

from creator.brand import models as brand_tables
from creator.brand.ports import BrandAssetRecord
from creator.campaign.repository import SqlAlchemyCampaignRepository
from creator.core.pagination import Page, PageRequest
from creator.generation.repository import SqlAlchemyGeneratedImageRepository
from creator.persona.repository import SqlAlchemyPersonaRepository
from creator.planning.repository import SqlAlchemyPlanningRepository
from creator.post_structure.repository import SqlAlchemyPostStructureRepository
from creator.workspace import models as workspace_tables


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


__all__ = [
    "SqlAlchemyBrandAssetRepository",
    "SqlAlchemyCampaignRepository",
    "SqlAlchemyGeneratedImageRepository",
    "SqlAlchemyPersonaRepository",
    "SqlAlchemyPlanningRepository",
    "SqlAlchemyPostStructureRepository",
]
