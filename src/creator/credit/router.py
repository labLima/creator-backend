"""HTTP routes for the credit capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.

The Credit Transaction ledger is append-only (ADR-019), so only the two reads
are published: a client cannot write or delete a ledger entry.
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
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get(
    "/api/v1/workspace-credit-transactions",
    tags=["Workspaces"],
    operation_id="list_workspace_credit_transactions_api_v1_workspace_credit_transactions_get",
)
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


@router.get(
    "/api/v1/workspace-credit-transactions/{id}",
    tags=["Workspaces"],
    operation_id="get_workspace_credit_transaction_api_v1_workspace_credit_transactions__id__get",
)
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
