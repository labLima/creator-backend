from __future__ import annotations

from typing import Any
from uuid import UUID

from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


class ApplicationError(Exception):
    def __init__(
        self, status_code: int, detail: Any, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


HTTPException = ApplicationError


def require_global_billing_admin(user: UserRecord) -> None:
    if user.global_role not in {"admin", "gestor"}:
        raise ApplicationError(
            403,
            {
                "code": "BILLING_ADMIN_REQUIRED",
                "message": "Billing administration role is required",
            },
        )


def require_admin(user: UserRecord) -> None:
    if user.global_role != "admin":
        raise ApplicationError(
            403, {"code": "ADMIN_REQUIRED", "message": "Administrator role is required"}
        )


def require_workspace_write(unit_of_work: UnitOfWork, *, user_id: UUID, workspace_id: UUID) -> None:
    if not unit_of_work.workspace.workspaces.user_has_workspace_role(
        user_id=user_id, workspace_id=workspace_id, minimum_role="editor"
    ):
        raise ApplicationError(
            403,
            {
                "code": "WORKSPACE_ACCESS_DENIED",
                "message": "Workspace is not writable by the authenticated user",
            },
        )


def not_found(entity: str) -> ApplicationError:
    code = entity.upper().replace(" ", "_")
    return ApplicationError(404, {"code": f"{code}_NOT_FOUND", "message": f"{entity} not found"})
