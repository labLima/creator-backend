"""Use cases for the planning capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.responses import page_payload
from creator.api.serializers import _planning_data
from creator.core.pagination import page_request
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_planning(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    campaign_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    result = uow.planning.list_for_user(
        user_id=actor.id,
        campaign_id=campaign_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(result, _planning_data)


def create_planning(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    campaign = uow.campaigns.get_for_user(user_id=actor.id, campaign_id=payload.campaign_id)
    if campaign is None:
        raise not_found("Campaign")
    require_workspace_write(uow, user_id=actor.id, workspace_id=campaign.workspace_id)
    planning = uow.planning.add(
        created_by=actor.id,
        **payload.model_dump(),
    )
    uow.commit()

    return _planning_data(planning)


def get_planning(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    planning_id: Any,
) -> Any:
    planning = uow.planning.get_for_user(user_id=actor.id, planning_id=planning_id)
    if planning is None:
        raise not_found("Planning")

    return _planning_data(planning)


def update_planning(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    planning_id: Any,
    payload: Any,
) -> Any:
    existing = uow.planning.get_for_user(user_id=actor.id, planning_id=planning_id)
    if existing is None:
        raise not_found("Planning")
    campaign = uow.campaigns.get_for_user(user_id=actor.id, campaign_id=existing.campaign_id)
    if campaign is None:
        raise not_found("Planning")
    require_workspace_write(uow, user_id=actor.id, workspace_id=campaign.workspace_id)
    updated = uow.planning.update(
        planning_id=planning_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _planning_data(updated)


def delete_planning(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    planning_id: Any,
) -> Any:
    existing = uow.planning.get_for_user(user_id=actor.id, planning_id=planning_id)
    if existing is None:
        raise not_found("Planning")
    campaign = uow.campaigns.get_for_user(user_id=actor.id, campaign_id=existing.campaign_id)
    if campaign is None:
        raise not_found("Planning")
    require_workspace_write(uow, user_id=actor.id, workspace_id=campaign.workspace_id)
    uow.planning.soft_delete(planning_id=planning_id)
    uow.commit()

    return {"deleted": True}
