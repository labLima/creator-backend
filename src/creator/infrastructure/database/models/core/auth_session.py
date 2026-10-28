from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from creator.infrastructure.database.db import Base

from ..types import timestamp_tz, uuid_default, uuid_pk


class AuthSession(Base):
    """A revocable refresh-token family, as defined in CONTEXT.md."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("refresh_token_hash", name="uq_auth_sessions_refresh_token_hash"),
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_family_id", "family_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
        Index("ix_auth_sessions_absolute_expires_at", "absolute_expires_at"),
    )

    id: Mapped[UUID] = mapped_column(uuid_pk, primary_key=True, default=uuid_default)
    user_id: Mapped[UUID] = mapped_column(
        uuid_pk, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    family_id: Mapped[UUID] = mapped_column(uuid_pk, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_refresh_token_hash: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(timestamp_tz, nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(timestamp_tz, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(timestamp_tz)
    replaced_by_id: Mapped[UUID | None] = mapped_column(uuid_pk)
    rotated_at: Mapped[datetime | None] = mapped_column(timestamp_tz)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        timestamp_tz, nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(timestamp_tz)
