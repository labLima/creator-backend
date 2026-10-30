from __future__ import annotations

# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator.modules.brand.adapters import tables as brand_tables
from creator.modules.workspace.adapters import tables as workspace_tables
from creator.repositories.brand_color import BrandColorRecord, BrandColorRepository


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
            select(brand_tables.BrandColor)
            .join(
                workspace_tables.WorkspaceMembership,
                workspace_tables.WorkspaceMembership.workspace_id
                == brand_tables.BrandColor.workspace_id,
            )
            .where(
                workspace_tables.WorkspaceMembership.user_id == uid,
                workspace_tables.WorkspaceMembership.deleted_at.is_(None),
                brand_tables.BrandColor.deleted_at.is_(None),
            )
        )

    def list_for_user(self, *, user_id, brand_id=None):
        q = self._q(user_id)
        if brand_id is not None:
            q = q.where(brand_tables.BrandColor.brand_id == brand_id)
        return [self._r(x) for x in self.s.scalars(q).all()]

    def get_for_user(self, *, user_id, color_id):
        x = self.s.scalar(self._q(user_id).where(brand_tables.BrandColor.id == color_id))
        return self._r(x) if x else None

    def add(self, *, fields):
        x = brand_tables.BrandColor(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, color_id, fields):
        x = self.s.get(brand_tables.BrandColor, color_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Brand color not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, color_id):
        x = self.s.get(brand_tables.BrandColor, color_id)
        if x is None or x.deleted_at is not None:
            raise ValueError("Brand color not found")
        x.deleted_at = datetime.now(UTC)
        x.updated_at = x.deleted_at
        self.s.flush()
