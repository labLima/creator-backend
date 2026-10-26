from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from creator.application.unit_of_work import UnitOfWork
from creator.config import Settings
from creator.domain.auth import AuthSession, AuthSignupResult, Principal
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
        return _PASSWORD_HASHER.verify(password_hash or _DUMMY_HASH, password)
    except VerifyMismatchError:
        return False


def _require_secret(settings: Settings) -> str:
    if not settings.auth_jwt_secret:
        raise AuthConfigurationError("AUTH_JWT_SECRET is required")
    return settings.auth_jwt_secret


def _access_token(*, user: UserRecord, session_id: UUID, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": settings.auth_jwt_issuer,
        "aud": settings.auth_jwt_audience,
        "sub": str(user.id),
        "session_id": str(session_id),
        "role": user.global_role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.auth_access_token_ttl_seconds)).timestamp()),
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, _require_secret(settings), algorithm="HS256")


def principal_from_access_token(token: str, settings: Settings) -> Principal:
    try:
        claims = jwt.decode(
            token,
            _require_secret(settings),
            algorithms=["HS256"],
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            options={"require": ["iss", "aud", "exp", "iat", "sub", "session_id", "type"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise ExpiredTokenError("access token is expired") from error
    except jwt.InvalidTokenError as error:
        raise InvalidTokenError("access token is invalid") from error
    if claims.get("type") != "access":
        raise InvalidTokenError("access token type is invalid")
    return Principal(
        subject=str(claims["sub"]),
        email=claims.get("email"),
        role=claims.get("role"),
        session_id=str(claims["session_id"]),
        claims=dict(claims),
    )


def _refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_for(
    *, user: UserRecord, session_id: UUID, refresh_token: str, settings: Settings
) -> AuthSession:
    return AuthSession(
        access_token=_access_token(user=user, session_id=session_id, settings=settings),
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.auth_access_token_ttl_seconds,
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
) -> LocalSignupResult:
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
        refresh_token = secrets.token_urlsafe(48)
        session = unit_of_work.auth_sessions.add(
            user_id=user.id,
            family_id=uuid4(),
            refresh_token_hash=_refresh_hash(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.auth_refresh_token_ttl_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        unit_of_work.commit()
    except (PersistenceError, ValueError):
        unit_of_work.rollback()
        raise
    auth_session = _session_for(
        user=user, session_id=session.id, refresh_token=refresh_token, settings=settings
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
) -> AuthSession:
    user = unit_of_work.users.get_by_email(normalize_email(email))
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("invalid email or password")
    refresh_token = secrets.token_urlsafe(48)
    session = unit_of_work.auth_sessions.add(
        user_id=user.id,
        family_id=uuid4(),
        refresh_token_hash=_refresh_hash(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.auth_refresh_token_ttl_days),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    unit_of_work.commit()
    return _session_for(
        user=user, session_id=session.id, refresh_token=refresh_token, settings=settings
    )


def refresh(
    *,
    unit_of_work: UnitOfWork,
    settings: Settings,
    refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> AuthSession:
    record = unit_of_work.auth_sessions.get_by_refresh_hash(_refresh_hash(refresh_token))
    if record is None:
        raise InvalidTokenError("refresh token is invalid")
    if record.revoked_at is not None:
        if record.replaced_by_id is not None:
            unit_of_work.auth_sessions.revoke_family(record.family_id)
            unit_of_work.commit()
        raise RevokedSessionError("refresh token was revoked")
    if record.expires_at <= datetime.now(UTC):
        unit_of_work.auth_sessions.revoke(record.id)
        unit_of_work.commit()
        raise ExpiredTokenError("refresh token is expired")

    user = unit_of_work.users.get_by_id(record.user_id)
    if user is None:
        raise InvalidTokenError("refresh token user is invalid")
    new_token = secrets.token_urlsafe(48)
    new_session = unit_of_work.auth_sessions.add(
        user_id=user.id,
        family_id=record.family_id,
        refresh_token_hash=_refresh_hash(new_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.auth_refresh_token_ttl_days),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    unit_of_work.auth_sessions.revoke(record.id, replaced_by_id=new_session.id)
    unit_of_work.auth_sessions.touch(new_session.id, at=datetime.now(UTC))
    unit_of_work.commit()
    return _session_for(
        user=user, session_id=new_session.id, refresh_token=new_token, settings=settings
    )


def logout(*, unit_of_work: UnitOfWork, session_id: UUID) -> None:
    unit_of_work.auth_sessions.revoke(session_id)
    unit_of_work.commit()


def session_is_active(*, unit_of_work: UnitOfWork, session_id: UUID) -> bool:
    session = unit_of_work.auth_sessions.get_by_id(session_id)
    if session is None:
        return False
    return session.revoked_at is None and session.expires_at > datetime.now(UTC)
