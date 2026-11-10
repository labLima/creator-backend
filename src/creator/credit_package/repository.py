"""SQLAlchemy implementation of the credit_package persistence ports."""

# Legacy exemptions carried over from the split modules.
# mypy: disable-error-code=no-untyped-def

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import creator.credit_package.models as credit_package_models
from creator.credit_package.ports import CreditPackageRecord, CreditPackageRepository


class SqlAlchemyCreditPackageRepository(CreditPackageRepository):
    def __init__(self, session: Session) -> None:
        self.s = session

    def _r(self, x: credit_package_models.CreditPackage) -> CreditPackageRecord:
        return CreditPackageRecord(
            id=x.id,
            code=x.name or "",
            name=x.name or "",
            credits_amount=x.credits,
            price_cents=x.price_cents,
            currency=x.currency,
            is_active=x.is_active,
            created_at=x.created_at,
            updated_at=x.updated_at,
            deleted_at=None,
        )

    def list(self):
        return [
            self._r(x) for x in self.s.scalars(select(credit_package_models.CreditPackage)).all()
        ]

    def get(self, *, package_id: UUID):
        x = self.s.scalar(
            select(credit_package_models.CreditPackage).where(
                credit_package_models.CreditPackage.id == package_id,
            )
        )
        return self._r(x) if x else None

    def add(self, *, fields):
        x = credit_package_models.CreditPackage(**fields)
        self.s.add(x)
        self.s.flush()
        return self._r(x)

    def update(self, *, package_id: UUID, fields):
        x = self.s.get(credit_package_models.CreditPackage, package_id)
        if x is None:
            raise ValueError("Credit package not found")
        for k, v in fields.items():
            setattr(x, k, v)
        x.updated_at = datetime.now(UTC)
        self.s.flush()
        return self._r(x)

    def soft_delete(self, *, package_id: UUID):
        x = self.s.get(credit_package_models.CreditPackage, package_id)
        if x is None:
            raise ValueError("Credit package not found")
        self.s.delete(x)
        self.s.flush()
