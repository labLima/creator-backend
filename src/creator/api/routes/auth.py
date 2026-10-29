from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from creator.api.auth import (
    FastApiCookieTransport,
    clear_auth_cookies,
    csrf_for_session,
    set_auth_cookies,
    set_csrf_cookie,
)
from creator.api.dependencies import (
    get_current_user,
    get_optional_current_user,
    get_optional_principal,
    get_principal,
    get_uow,
)
from creator.api.dtos import AuthLoginRequest, AuthSignupRequest
from creator.application.auth import (
    AuthConfigurationError,
    EmailAlreadyRegisteredError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidTokenError,
    LocalSignupResult,
    RefreshInProgressError,
    RevokedSessionError,
)
from creator.application.auth import (
    login as login_local,
)
from creator.application.auth import (
    logout as logout_local,
)
from creator.application.auth import (
    refresh as refresh_local,
)
from creator.application.auth import (
    signup as signup_local,
)
from creator.application.auth_ports import AuthTokenServices
from creator.application.auth_types import AuthSignupResult, IssuedSession
from creator.application.unit_of_work import UnitOfWork
from creator.config import Settings, get_settings
from creator.domain.auth import Principal
from creator.domain.exceptions import PersistenceError
from creator.infrastructure.auth import auth_token_services
from creator.repositories import UserRecord, WorkspaceMembershipRecord, WorkspaceRecord

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _request_id(request: Request) -> UUID:
    existing = getattr(request.state, "request_id", None)
    return existing if isinstance(existing, UUID) else uuid4()


def _success(data: dict[str, Any], request: Request, *, status_code: int = 200) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "data": data, "meta": {"request_id": str(request_id)}},
        headers={"X-Request-ID": str(request_id)},
    )


def _session_data(
    session: IssuedSession,
    *,
    settings: Settings,
    csrf_token: str,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "token_type": session.token_type,
        "expires_in": session.expires_in,
        "refresh_expires_in": session.refresh_expires_in,
        "csrf_token": csrf_token,
        "principal": {
            "subject": session.principal.subject,
            "email": session.principal.email,
            "role": session.principal.role,
        },
        "provider": session.provider,
        "metadata": session.metadata,
    }
    if settings.auth_token_body_enabled:
        data["access_token"] = session.access_token
        data["refresh_token"] = session.refresh_token
    return data


def _record_data(record: Any) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "name": record.name,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
    }


def _membership_data(record: WorkspaceMembershipRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "workspace_id": str(record.workspace_id),
        "user_id": str(record.user_id),
        "role": record.role,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
    }


def _signup_data(
    result: AuthSignupResult,
    *,
    workspace: WorkspaceRecord,
    membership: WorkspaceMembershipRecord,
    settings: Settings,
    csrf_token: str,
) -> dict[str, Any]:
    return {
        "principal": {
            "subject": result.principal.subject,
            "email": result.principal.email,
            "role": result.principal.role,
        },
        "session": (
            _session_data(result.session, settings=settings, csrf_token=csrf_token)
            if result.session
            else None
        ),
        "workspace": _record_data(workspace),
        "membership": _membership_data(membership),
        "confirmation_required": result.confirmation_required,
        "provider": result.provider,
        "metadata": result.metadata,
    }


@router.post("/login")
def login_with_password(
    payload: AuthLoginRequest,
    request: Request,
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
    token_services: Annotated[AuthTokenServices, Depends(auth_token_services)],
) -> JSONResponse:
    try:
        session = login_local(
            unit_of_work=unit_of_work,
            settings=settings,
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            token_services=token_services,
        )
    except AuthConfigurationError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "AUTHENTICATION_MISCONFIGURED",
                "message": "Authentication is not configured",
            },
        ) from error
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=401,
            detail={"code": "LOGIN_REJECTED", "message": "Invalid email or password"},
        ) from error
    csrf_token = csrf_for_session(session, settings=settings, token_services=token_services)
    response = _success(_session_data(session, settings=settings, csrf_token=csrf_token), request)
    set_auth_cookies(
        FastApiCookieTransport(response), session, csrf_token=csrf_token, settings=settings
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/signup", status_code=201)
def signup_with_password(
    payload: AuthSignupRequest,
    request: Request,
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
    token_services: Annotated[AuthTokenServices, Depends(auth_token_services)],
) -> JSONResponse:
    try:
        result: LocalSignupResult = signup_local(
            unit_of_work=unit_of_work,
            settings=settings,
            email=payload.email,
            password=payload.password,
            workspace_name=payload.workspace.name,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            token_services=token_services,
        )
    except AuthConfigurationError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "AUTHENTICATION_MISCONFIGURED",
                "message": "Authentication is not configured",
            },
        ) from error
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "Email is already registered"},
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail={"code": "WEAK_PASSWORD", "message": str(error)}
        ) from error
    except PersistenceError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SIGNUP_BOOTSTRAP_FAILED",
                "message": "Signup Workspace could not be created",
            },
        ) from error
    csrf_token = (
        csrf_for_session(result.result.session, settings=settings, token_services=token_services)
        if result.result.session
        else ""
    )
    response = _success(
        _signup_data(
            result.result,
            workspace=result.workspace,
            membership=result.membership,
            settings=settings,
            csrf_token=csrf_token,
        ),
        request,
        status_code=201,
    )
    if result.result.session:
        set_auth_cookies(
            FastApiCookieTransport(response),
            result.result.session,
            csrf_token=csrf_token,
            settings=settings,
        )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/refresh")
async def refresh_session(
    request: Request,
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
    token_services: Annotated[AuthTokenServices, Depends(auth_token_services)],
) -> JSONResponse:
    refresh_token = request.cookies.get(settings.auth_cookie_refresh_name)
    if not refresh_token and settings.auth_token_body_enabled:
        try:
            body = await request.json()
        except ValueError:
            body = {}
        if isinstance(body, dict) and isinstance(body.get("refresh_token"), str):
            refresh_token = body["refresh_token"]
    try:
        session = refresh_local(
            unit_of_work=unit_of_work,
            settings=settings,
            refresh_token=refresh_token or "",
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            token_services=token_services,
        )
    except AuthConfigurationError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "AUTHENTICATION_MISCONFIGURED",
                "message": "Authentication is not configured",
            },
        ) from error
    except RefreshInProgressError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "REFRESH_IN_PROGRESS", "message": "Refresh is already in progress"},
        ) from error
    except (InvalidTokenError, ExpiredTokenError, RevokedSessionError) as error:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid"},
        ) from error
    csrf_token = csrf_for_session(session, settings=settings, token_services=token_services)
    response = _success(_session_data(session, settings=settings, csrf_token=csrf_token), request)
    set_auth_cookies(
        FastApiCookieTransport(response), session, csrf_token=csrf_token, settings=settings
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/csrf")
def csrf_token(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    principal: Annotated[Principal | None, Depends(get_principal)],
    settings: Annotated[Settings, Depends(get_settings)],
    token_services: Annotated[AuthTokenServices, Depends(auth_token_services)],
) -> JSONResponse:
    del current_user
    if principal is None or principal.session_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_INVALID", "message": "Authentication failed"},
        )
    token = token_services.csrf.issue(session_id=UUID(principal.session_id), settings=settings)
    response = _success({"csrf_token": token}, request)
    set_csrf_cookie(FastApiCookieTransport(response), token, settings=settings)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/logout")
def logout_session(
    request: Request,
    current_user: Annotated[UserRecord | None, Depends(get_optional_current_user)],
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    session_id: UUID | None = None
    if principal is not None and principal.session_id is not None:
        if current_user is not None:
            session_id = UUID(principal.session_id)
    if session_id is None:
        refresh_token = request.cookies.get(settings.auth_cookie_refresh_name)
        if refresh_token:
            record = unit_of_work.auth_sessions.get_by_refresh_hash(
                hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
            )
            now = datetime.now(UTC)
            if (
                record is not None
                and record.revoked_at is None
                and record.expires_at > now
                and record.absolute_expires_at > now
            ):
                session_id = record.id
    if session_id is None and principal is not None and principal.session_id is not None:
        session_id = UUID(principal.session_id)
    if session_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_INVALID", "message": "Authentication failed"},
        )
    logout_local(unit_of_work=unit_of_work, session_id=session_id)
    response = _success({"logged_out": True}, request)
    clear_auth_cookies(FastApiCookieTransport(response), settings=settings)
    response.headers["Cache-Control"] = "no-store"
    return response
