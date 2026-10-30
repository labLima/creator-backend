"""SQLAlchemy implementation of the user persistence ports."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import creator.user.models as user_models
from creator.core.pagination import Page, PageRequest
from creator.core.types import JsonObject
from creator.domain.exceptions import ConflictError, EntityNotFoundError
from creator.infrastructure.database.enums import GlobalRole
from creator.infrastructure.persistence.sql import (
    as_datetime,
    as_optional_datetime,
    enum_value,
    flush_or_raise,
    json_object,
    now,
    paginate,
)
from creator.user.ports import SettingsRecord, UserRecord


def _user_record(row: user_models.User) -> UserRecord:
    return UserRecord(
        id=row.id,
        external_id=row.external_id,
        email=row.email,
        display_name=row.display_name,
        global_role=enum_value(row.global_role),
        created_at=as_datetime(row.created_at),
        updated_at=as_datetime(row.updated_at),
        deleted_at=as_optional_datetime(row.deleted_at),
        password_hash=row.password_hash,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        *,
        external_id: str,
        email: str | None = None,
        display_name: str | None = None,
        global_role: str = "membro",
        password_hash: str | None = None,
    ) -> UserRecord:
        row = user_models.User(
            external_id=external_id,
            email=email,
            display_name=display_name,
            global_role=global_role,
            password_hash=password_hash,
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _user_record(row)

    def get_by_id(self, user_id: UUID, *, include_deleted: bool = False) -> UserRecord | None:
        statement = select(user_models.User).where(user_models.User.id == user_id)
        if not include_deleted:
            statement = statement.where(user_models.User.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _user_record(row) if row else None

    def get_by_external_id(
        self, external_id: str, *, include_deleted: bool = False
    ) -> UserRecord | None:
        statement = select(user_models.User).where(user_models.User.external_id == external_id)
        if not include_deleted:
            statement = statement.where(user_models.User.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _user_record(row) if row else None

    def get_by_email(self, email: str, *, include_deleted: bool = False) -> UserRecord | None:
        statement = select(user_models.User).where(
            func.lower(user_models.User.email) == email.lower()
        )
        if not include_deleted:
            statement = statement.where(user_models.User.deleted_at.is_(None))
        row = self._session.scalars(statement).one_or_none()
        return _user_record(row) if row else None

    def list(
        self,
        *,
        include_deleted: bool = False,
        page: PageRequest | None = None,
    ) -> Page[UserRecord]:
        page = page or PageRequest()
        statement = select(user_models.User)
        count_statement = select(func.count()).select_from(user_models.User)
        if not include_deleted:
            statement = statement.where(user_models.User.deleted_at.is_(None))
            count_statement = count_statement.where(user_models.User.deleted_at.is_(None))
        rows, total = paginate(
            self._session,
            statement,
            count_statement,
            user_models.User.created_at,
            page,
        )
        return Page(
            items=[_user_record(row) for row in rows],
            total=total,
            page=page.page,
            limit=page.limit,
        )

    def update_profile(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> UserRecord:
        row = self._session.get(user_models.User, user_id)
        if row is None or row.deleted_at is not None:
            raise EntityNotFoundError("User not found")
        if email is not None:
            row.email = email
        if display_name is not None:
            row.display_name = display_name
        row.updated_at = now()
        flush_or_raise(self._session)
        return _user_record(row)

    def update(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        display_name: str | None = None,
        global_role: str | None = None,
    ) -> UserRecord:
        row = self._session.get(user_models.User, user_id)
        if row is None or row.deleted_at is not None:
            raise EntityNotFoundError("User not found")
        if email is not None:
            row.email = email
        if display_name is not None:
            row.display_name = display_name
        if global_role is not None:
            row.global_role = GlobalRole(global_role)
        row.updated_at = now()
        flush_or_raise(self._session)
        return _user_record(row)

    def soft_delete(self, user_id: UUID) -> None:
        row = self._session.get(user_models.User, user_id)
        if row is None or row.deleted_at is not None:
            raise EntityNotFoundError("User not found")
        timestamp = now()
        row.deleted_at = timestamp
        row.updated_at = timestamp
        flush_or_raise(self._session)


def _settings_record(row: user_models.Settings) -> SettingsRecord:
    return SettingsRecord(
        id=row.id,
        user_id=row.user_id,
        brand_name=row.brand_name,
        segment=row.segment,
        tone=row.tone,
        voice=row.voice,
        visual_style=row.visual_style,
        default_preferences=json_object(row.default_preferences),
        created_at=as_datetime(row.created_at),
        updated_at=as_datetime(row.updated_at),
    )


class SqlAlchemySettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_user_id(self, user_id: UUID) -> SettingsRecord | None:
        row = self._session.scalars(
            select(user_models.Settings).where(user_models.Settings.user_id == user_id)
        ).one_or_none()
        return _settings_record(row) if row else None

    def get_or_create_for_user(self, user_id: UUID) -> SettingsRecord:
        row = self._session.scalars(
            select(user_models.Settings)
            .where(user_models.Settings.user_id == user_id)
            .with_for_update()
        ).one_or_none()
        if row is not None:
            return _settings_record(row)
        try:
            return self.create_for_user(user_id)
        except ConflictError:
            row = self._session.scalars(
                select(user_models.Settings)
                .where(user_models.Settings.user_id == user_id)
                .with_for_update()
            ).one_or_none()
            if row is None:
                raise
            return _settings_record(row)

    def create_for_user(
        self,
        user_id: UUID,
        *,
        brand_name: str | None = None,
        segment: str | None = None,
        tone: str = "professional",
        voice: str = "Clear and useful",
        visual_style: str = "photographic",
        default_preferences: JsonObject | None = None,
    ) -> SettingsRecord:
        row = user_models.Settings(
            user_id=user_id,
            brand_name=brand_name,
            segment=segment,
            tone=tone,
            voice=voice,
            visual_style=visual_style,
            default_preferences=json_object(default_preferences),
        )
        self._session.add(row)
        flush_or_raise(self._session)
        return _settings_record(row)

    def update_partial(self, user_id: UUID, changes: JsonObject) -> SettingsRecord:
        row = self._session.scalars(
            select(user_models.Settings)
            .where(user_models.Settings.user_id == user_id)
            .with_for_update()
        ).one_or_none()
        if row is None:
            raise EntityNotFoundError("Settings not found")
        for field_name in (
            "brand_name",
            "segment",
            "tone",
            "voice",
            "visual_style",
            "default_preferences",
        ):
            if field_name not in changes:
                continue
            value = changes[field_name]
            if field_name == "default_preferences":
                row.default_preferences = json_object(value if isinstance(value, dict) else None)
            else:
                setattr(row, field_name, value)
        row.updated_at = now()
        flush_or_raise(self._session)
        return _settings_record(row)
