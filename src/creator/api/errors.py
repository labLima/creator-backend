"""HTTP authorization and error helpers shared by module routers."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException

from creator.application.unit_of_work import UnitOfWork
from creator.repositories.user import UserRecord


def require_global_billing_admin(user: UserRecord) -> None:
    if user.global_role not in {"admin", "gestor"}:
        raise HTTPException(status_code=403, detail="Billing administration required")


def require_admin(user: UserRecord) -> None:
    if user.global_role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_REQUIRED", "message": "Administrator role is required"},
        )


def require_workspace_write(
    unit_of_work: UnitOfWork,
    *,
    user_id: UUID,
    workspace_id: UUID,
) -> None:
    if not unit_of_work.workspaces.user_has_workspace_role(
        user_id=user_id,
        workspace_id=workspace_id,
        minimum_role="editor",
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "WORKSPACE_ACCESS_DENIED",
                "message": "Workspace is not writable by the authenticated user",
            },
        )


def not_found(entity: str) -> HTTPException:
    code = entity.upper().replace(" ", "_")
    return HTTPException(
        status_code=404,
        detail={"code": f"{code}_NOT_FOUND", "message": f"{entity} not found"},
    )
