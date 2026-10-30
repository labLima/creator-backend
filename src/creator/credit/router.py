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
from creator.api.responses import (
    success_response,
)
from creator.credit import service
from creator.credit.schemas import (
    WorkspaceCreditTransactionCreateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/workspace-credit-transactions", tags=["Workspaces"])
def list_workspace_credit_transactions(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
) -> JSONResponse:
    return success_response(
        service.list_workspace_credit_transactions(
            uow=unit_of_work, actor=current_user, workspace_id=workspace_id, request=request
        ),
        request,
    )


@router.post("/api/v1/workspace-credit-transactions", tags=["Workspaces"])
def create_workspace_credit_transaction(
    payload: WorkspaceCreditTransactionCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.create_workspace_credit_transaction(
            uow=unit_of_work, actor=current_user, payload=payload, request=request
        ),
        request,
        status_code=201,
    )


@router.get("/api/v1/workspace-credit-transactions/{id}", tags=["Workspaces"])
def get_workspace_credit_transaction(
    transaction_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.get_workspace_credit_transaction(
            uow=unit_of_work, actor=current_user, transaction_id=transaction_id, request=request
        ),
        request,
    )


@router.delete("/api/v1/workspace-credit-transactions/{id}", tags=["Workspaces"])
def delete_workspace_credit_transaction(
    transaction_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    return success_response(
        service.delete_workspace_credit_transaction(
            uow=unit_of_work, actor=current_user, transaction_id=transaction_id, request=request
        ),
        request,
    )
