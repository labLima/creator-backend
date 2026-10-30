"""HTTP routes for the post_structure capability.

Extracted verbatim from `creator.main.create_app`; handler names are part of
the published `operationId` contract and must not be renamed.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
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
    page_payload,
    success_response,
)
from creator.api.serializers import (
    _post_structure_data,
)
from creator.core.pagination import page_request
from creator.post_structure.schemas import (
    PostStructureCreateRequest,
    PostStructureUpdateRequest,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

router = APIRouter()


@router.get("/api/v1/post-structures", tags=["Post Structures"])
def list_post_structures(
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
    workspace_id: UUID | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^-?created_at$")] = "-created_at",
) -> JSONResponse:
    result = unit_of_work.post_structures.list_for_user(
        user_id=current_user.id,
        workspace_id=workspace_id,
        page=page_request(page, limit, sort),
    )
    return success_response(page_payload(result, _post_structure_data), request)


@router.post("/api/v1/post-structures", tags=["Post Structures"])
def create_post_structure(
    payload: PostStructureCreateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=payload.workspace_id
    )
    fields = payload.model_dump(exclude={"workspace_id", "planning_id"})
    post_structure = unit_of_work.post_structures.add(
        workspace_id=payload.workspace_id,
        planning_id=payload.planning_id,
        created_by=current_user.id,
        **fields,
    )
    unit_of_work.commit()
    return success_response(_post_structure_data(post_structure), request, status_code=201)


@router.get("/api/v1/post-structures/{id}", tags=["Post Structures"])
def get_post_structure(
    post_structure_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    post_structure = unit_of_work.post_structures.get_for_user(
        user_id=current_user.id, post_structure_id=post_structure_id
    )
    if post_structure is None:
        raise not_found("Post structure")
    return success_response(_post_structure_data(post_structure), request)


@router.put("/api/v1/post-structures/{id}", tags=["Post Structures"])
def update_post_structure(
    post_structure_id: Annotated[UUID, Path(alias="id")],
    payload: PostStructureUpdateRequest,
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.post_structures.get_for_user(
        user_id=current_user.id, post_structure_id=post_structure_id
    )
    if existing is None:
        raise not_found("Post structure")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    updated = unit_of_work.post_structures.update(
        post_structure_id=post_structure_id,
        fields=payload.model_dump(exclude_unset=True),
    )
    unit_of_work.commit()
    return success_response(_post_structure_data(updated), request)


@router.delete("/api/v1/post-structures/{id}", tags=["Post Structures"])
def delete_post_structure(
    post_structure_id: Annotated[UUID, Path(alias="id")],
    request: Request,
    current_user: Annotated[UserRecord, Depends(get_current_user)],
    unit_of_work: Annotated[UnitOfWork, Depends(get_uow)],
) -> JSONResponse:
    existing = unit_of_work.post_structures.get_for_user(
        user_id=current_user.id, post_structure_id=post_structure_id
    )
    if existing is None:
        raise not_found("Post structure")
    require_workspace_write(
        unit_of_work, user_id=current_user.id, workspace_id=existing.workspace_id
    )
    unit_of_work.post_structures.soft_delete(post_structure_id=post_structure_id)
    unit_of_work.commit()
    return success_response({"deleted": True}, request)
