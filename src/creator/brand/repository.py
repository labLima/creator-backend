"""SQLAlchemy implementation of the brand persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def
# mypy: disallow_untyped_calls=False

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.workspace.models as workspace_models
from creator.brand.ports import BrandColorRecord, BrandColorRepository


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
