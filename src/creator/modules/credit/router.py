"""HTTP routes for the credit capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse

from creator.api.dependencies import (
    get_current_user,
    get_uow,
)
from creator.api.errors import (
    not_found,
    require_workspace_write,
)
from creator.api.responses import (
    success_response,
)
from creator.api.serializers import (
    _workspace_credit_transaction_data,
)
from creator.modules.credit.schemas import (
    WorkspaceCreditTransactionCreateRequest,
)
from creator.repositories import (
    UserRecord,
)
from creator.uow import UnitOfWork

router = APIRouter()


@router.get("/api/v1/workspace-credit-transactions", tags=["Workspaces"])
def list_workspace_credit_transactions(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    items = unit_of_work.workspace_credit_transactions.list_for_user(
        user_id=current_user.id, workspace_id=workspace_id
    )
    return success_response(
        {"items": [_workspace_credit_transaction_data(x) for x in items]}, request
    )


@router.post("/api/v1/workspace-credit-transactions", tags=["Workspaces"])
def create_workspace_credit_transaction(
    payload: WorkspaceCreditTransactionCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    item = unit_of_work.workspace_credit_transactions.add(fields=payload.model_dump())
    unit_of_work.commit()
    return success_response(_workspace_credit_transaction_data(item), request, status_code=201)


@router.get("/api/v1/workspace-credit-transactions/{id}", tags=["Workspaces"])
def get_workspace_credit_transaction(
    transaction_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    item = unit_of_work.workspace_credit_transactions.get_for_user(
        user_id=current_user.id, transaction_id=transaction_id
    )
    if item is None:
        raise not_found("Workspace credit transaction")
    return success_response(_workspace_credit_transaction_data(item), request)


@router.delete("/api/v1/workspace-credit-transactions/{id}", tags=["Workspaces"])
def delete_workspace_credit_transaction(
    transaction_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    if (
        unit_of_work.workspace_credit_transactions.get_for_user(
            user_id=current_user.id, transaction_id=transaction_id
        )
        is None
    ):
        raise not_found("Workspace credit transaction")
    unit_of_work.workspace_credit_transactions.soft_delete(transaction_id=transaction_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
