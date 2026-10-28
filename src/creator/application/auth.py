from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from typing import cast
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from creator.application.auth_ports import AuthTokenServices, Clock
from creator.application.auth_types import AuthSignupResult, IssuedSession
from creator.application.unit_of_work import UnitOfWork
from creator.config import Settings
from creator.domain.auth import Principal
from creator.domain.exceptions import PersistenceError
from creator.repositories import UserRecord, WorkspaceMembershipRecord, WorkspaceRecord

_PASSWORD_HASHER = PasswordHasher()
_DUMMY_HASH = _PASSWORD_HASHER.hash("creator-dummy-password")


class AuthError(Exception):
    """Base class for authentication failures at the Creator boundary."""


class AuthConfigurationError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class EmailAlreadyRegisteredError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class ExpiredTokenError(AuthError):
    pass


class RevokedSessionError(AuthError):
    pass


class RefreshInProgressError(AuthError):
    pass


@dataclass(frozen=True, slots=True)
class LocalSignupResult:
    user: UserRecord
    workspace: WorkspaceRecord
    membership: WorkspaceMembershipRecord
    result: AuthSignupResult


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str, settings: Settings) -> str:
    if len(password) < settings.auth_password_min_length:
        raise ValueError(
            f"password must have at least {settings.auth_password_min_length} characters"
        )
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return bool(_PASSWORD_HASHER.verify(password_hash or _DUMMY_HASH, password))
    except VerifyMismatchError:
        return False


def principal_from_access_token(
    token: str, settings: Settings, *, token_services: AuthTokenServices
) -> Principal:
    try:
        return token_services.access.principal(token, settings)
    except AuthConfigurationError:
        raise
    except (ExpiredTokenError, InvalidTokenError):
        raise
    except ValueError as error:
        raise AuthConfigurationError("AUTH_JWT_SECRET is required") from error


def _refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_for(
    *,
    user: UserRecord,
    session_id: UUID,
    refresh_token: str,
    settings: Settings,
    token_services: AuthTokenServices,
    refresh_expires_in: int,
) -> IssuedSession:
    return IssuedSession(
        access_token=token_services.access.issue(
            user_id=user.id,
            session_id=session_id,
            role=user.global_role,
            settings=settings,
        ),
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.auth_access_token_ttl_seconds,
        refresh_expires_in=refresh_expires_in,
        principal=Principal(
            subject=str(user.id),
            email=user.email,
            role=user.global_role,
            session_id=str(session_id),
        ),
        provider="local",
        metadata={"user_id": str(user.id)},
    )


def signup(
    *,
    unit_of_work: UnitOfWork,
    settings: Settings,
    email: str,
    password: str,
    workspace_name: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
    token_services: AuthTokenServices,
    clock: Clock | None = None,
) -> LocalSignupResult:
    clock = _resolve_clock(token_services, clock)
    normalized = normalize_email(email)
    if unit_of_work.users.get_by_email(normalized, include_deleted=True) is not None:
        raise EmailAlreadyRegisteredError("email is already registered")
    try:
        user = unit_of_work.users.add(
            external_id=f"local:{uuid4().hex}",
            email=normalized,
            password_hash=hash_password(password, settings),
            display_name=None,
        )
        workspace = unit_of_work.workspaces.create_for_user(
            user_id=user.id,
            name=workspace_name,
        )
        refresh_token = token_services.refresh.generate()
        now = clock.now()
        session = unit_of_work.auth_sessions.add(
            user_id=user.id,
            family_id=uuid4(),
            refresh_token_hash=_refresh_hash(refresh_token),
            expires_at=now + timedelta(days=settings.auth_refresh_token_ttl_days),
            absolute_expires_at=now + timedelta(days=settings.auth_session_absolute_ttl_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        unit_of_work.commit()
    except (PersistenceError, ValueError):
        unit_of_work.rollback()
        raise
    auth_session = _session_for(
        user=user,
        session_id=session.id,
        refresh_token=refresh_token,
        settings=settings,
        token_services=token_services,
        refresh_expires_in=max(0, int((session.absolute_expires_at - clock.now()).total_seconds())),
    )
    return LocalSignupResult(
        user=user,
        workspace=workspace.workspace,
        membership=workspace.membership,
        result=AuthSignupResult(
            principal=auth_session.principal,
            session=auth_session,
            confirmation_required=False,
            provider="local",
        ),
    )


def login(
    *,
    unit_of_work: UnitOfWork,
    settings: Settings,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
    token_services: AuthTokenServices,
    clock: Clock | None = None,
) -> IssuedSession:
    clock = _resolve_clock(token_services, clock)
    user = unit_of_work.users.get_by_email(normalize_email(email))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("invalid email or password")
    refresh_token = token_services.refresh.generate()
    now = clock.now()
    session = unit_of_work.auth_sessions.add(
        user_id=user.id,
        family_id=uuid4(),
        refresh_token_hash=_refresh_hash(refresh_token),
        expires_at=now + timedelta(days=settings.auth_refresh_token_ttl_days),
        absolute_expires_at=now + timedelta(days=settings.auth_session_absolute_ttl_days),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    unit_of_work.commit()
    return _session_for(
        user=user,
        session_id=session.id,
        refresh_token=refresh_token,
        settings=settings,
        token_services=token_services,
        refresh_expires_in=max(0, int((session.absolute_expires_at - clock.now()).total_seconds())),
    )


def refresh(
    *,
    unit_of_work: UnitOfWork,
    settings: Settings,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
    token_services: AuthTokenServices,
    clock: Clock | None = None,
) -> IssuedSession:
    clock = _resolve_clock(token_services, clock)
    record = unit_of_work.auth_sessions.get_by_refresh_hash(_refresh_hash(refresh_token))
    if record is None:
        raise InvalidTokenError("refresh token is invalid")
    now = clock.now()
    if record.revoked_at is not None:
        if (
            record.replaced_by_id is not None
            and record.rotated_at is not None
            and now - record.rotated_at
            <= timedelta(seconds=settings.auth_refresh_rotation_grace_seconds)
        ):
            raise RefreshInProgressError("refresh token rotation is already in progress")
        if record.replaced_by_id is not None:
            unit_of_work.auth_sessions.revoke_family(record.family_id)
            unit_of_work.commit()
        raise RevokedSessionError("refresh token was revoked")
    if record.expires_at <= now or record.absolute_expires_at <= now:
        unit_of_work.auth_sessions.revoke(record.id)
        unit_of_work.commit()
        raise ExpiredTokenError("refresh token is expired")

    user = unit_of_work.users.get_by_id(record.user_id)
    if user is None:
        raise InvalidTokenError("refresh token user is invalid")
    new_token = token_services.refresh.generate()
    new_session_id = uuid4()
    absolute_expires_at = record.absolute_expires_at
    expires_at = min(
        now + timedelta(days=settings.auth_refresh_token_ttl_days),
        absolute_expires_at,
    )
    new_session = unit_of_work.auth_sessions.rotate(
        record.id,
        new_session_id=new_session_id,
        new_refresh_token_hash=_refresh_hash(new_token),
        expires_at=expires_at,
        absolute_expires_at=absolute_expires_at,
        now=now,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    if new_session is None:
        current = unit_of_work.auth_sessions.get_by_id(record.id)
        if (
            current is not None
            and current.replaced_by_id is not None
            and current.rotated_at is not None
            and now - current.rotated_at
            <= timedelta(seconds=settings.auth_refresh_rotation_grace_seconds)
        ):
            raise RefreshInProgressError("refresh token rotation is already in progress")
        unit_of_work.auth_sessions.revoke_family(record.family_id)
        unit_of_work.commit()
        raise RevokedSessionError("refresh token was revoked")
    unit_of_work.auth_sessions.touch(new_session.id, at=now)
    unit_of_work.commit()
    return _session_for(
        user=user,
        session_id=new_session.id,
        refresh_token=new_token,
        settings=settings,
        token_services=token_services,
        refresh_expires_in=max(0, int((absolute_expires_at - now).total_seconds())),
    )


def logout(*, unit_of_work: UnitOfWork, session_id: UUID) -> None:
    record = unit_of_work.auth_sessions.get_by_id(session_id)
    if record is not None:
        unit_of_work.auth_sessions.revoke_family(record.family_id)
    unit_of_work.commit()


def session_is_active(*, unit_of_work: UnitOfWork, session_id: UUID, clock: Clock) -> bool:
    session = unit_of_work.auth_sessions.get_by_id(session_id)
    if session is None:
        return False
    now = clock.now()
    absolute_expires_at = getattr(session, "absolute_expires_at", session.expires_at)
    return session.revoked_at is None and session.expires_at > now and absolute_expires_at > now


def _resolve_clock(
    token_services: AuthTokenServices,
    clock: Clock | None,
) -> Clock:
    if clock is not None:
        return clock
    candidate = getattr(token_services, "clock", None)
    if candidate is None:
        raise AuthConfigurationError("authentication clock is not configured")
    return cast(Clock, candidate)
