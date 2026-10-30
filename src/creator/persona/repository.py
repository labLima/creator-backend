"""SQLAlchemy implementation of the persona persistence ports."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

import creator.brand.models as brand_models
import creator.persona.models as persona_models
import creator.workspace.models as workspace_models
from creator.core.pagination import Page, PageRequest
from creator.persona.ports import PersonaRecord


def _persona_record(row: persona_models.Persona) -> PersonaRecord:
    return PersonaRecord(
        id=row.id,
        brand_id=row.brand_id,
        created_by=row.created_by,
        name=row.name,
        age=row.age,
        gender=row.gender,
        main_goal=row.main_goal,
        challenge=row.challenge,
        interest=row.interest,
        routine=row.routine,
        journey=row.journey,
        trigger=row.trigger,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyPersonaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, *, created_by: UUID, **fields: object) -> PersonaRecord:
        row = persona_models.Persona(created_by=created_by, **fields)
        self._session.add(row)
        self._session.flush()
        return _persona_record(row)

    def list_for_user(
        self,
        *,
        user_id: UUID,
        brand_id: UUID | None = None,
        page: PageRequest | None = None,
    ) -> Page[PersonaRecord]:
        page = page or PageRequest()
        statement = self._select(user_id)
        count = (
            select(func.count())
            .select_from(persona_models.Persona)
            .join(brand_models.Brand, brand_models.Brand.id == persona_models.Persona.brand_id)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.Brand.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                persona_models.Persona.deleted_at.is_(None),
                brand_models.Brand.deleted_at.is_(None),
            )
        )
        if brand_id is not None:
            statement = statement.where(persona_models.Persona.brand_id == brand_id)
            count = count.where(persona_models.Persona.brand_id == brand_id)
        order = (
            asc(persona_models.Persona.created_at)
            if page.sort == "asc"
            else desc(persona_models.Persona.created_at)
        )
        rows = self._session.scalars(
            statement.order_by(order).offset(page.offset).limit(page.limit)
        ).all()
        return Page(
            items=[_persona_record(row) for row in rows],
            total=self._session.scalar(count) or 0,
            page=page.page,
            limit=page.limit,
        )

    def get_for_user(self, *, user_id: UUID, persona_id: UUID) -> PersonaRecord | None:
        row = self._session.scalars(
            self._select(user_id).where(persona_models.Persona.id == persona_id)
        ).one_or_none()
        return _persona_record(row) if row else None

    def update(self, *, persona_id: UUID, fields: dict[str, object]) -> PersonaRecord:
        row = self._session.get(persona_models.Persona, persona_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Persona not found")
        for name, value in fields.items():
            setattr(row, name, value)
        row.updated_at = datetime.now(UTC)
        self._session.flush()
        return _persona_record(row)

    def soft_delete(self, *, persona_id: UUID) -> None:
        row = self._session.get(persona_models.Persona, persona_id)
        if row is None or row.deleted_at is not None:
            raise ValueError("Persona not found")
        timestamp = datetime.now(UTC)
        row.deleted_at = timestamp
        row.updated_at = timestamp
        self._session.flush()

    def _select(self, user_id: UUID) -> Select[persona_models.Persona]:
        return (
            select(persona_models.Persona)
            .join(brand_models.Brand, brand_models.Brand.id == persona_models.Persona.brand_id)
            .join(
                workspace_models.WorkspaceMembership,
                workspace_models.WorkspaceMembership.workspace_id
                == brand_models.Brand.workspace_id,
            )
            .where(
                workspace_models.WorkspaceMembership.user_id == user_id,
                workspace_models.WorkspaceMembership.deleted_at.is_(None),
                persona_models.Persona.deleted_at.is_(None),
                brand_models.Brand.deleted_at.is_(None),
            )
        )
