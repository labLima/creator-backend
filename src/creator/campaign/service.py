"""Use cases for the campaign capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.responses import page_payload
from creator.api.serializers import _campaign_data
from creator.core.pagination import page_request
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_campaigns(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    workspace_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    campaigns = uow.campaigns.list_for_user(
        user_id=actor.id,
        workspace_id=workspace_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(campaigns, _campaign_data)


def create_campaign(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    require_workspace_write(uow, user_id=actor.id, workspace_id=payload.workspace_id)
    campaign = uow.campaigns.add(
        workspace_id=payload.workspace_id,
        created_by=actor.id,
        name=payload.name,
        description=payload.description,
        target_audience=payload.target_audience,
        objectives=payload.objectives,
        voice=payload.voice,
        start_at=payload.start_at,
        end_at=payload.end_at,
    )
    uow.commit()

    return _campaign_data(campaign)


def get_campaign(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    campaign_id: Any,
) -> Any:
    campaign = uow.campaigns.get_for_user(user_id=actor.id, campaign_id=campaign_id)
    if campaign is None:
        raise not_found("Campaign")

    return _campaign_data(campaign)


def update_campaign(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    campaign_id: Any,
    payload: Any,
) -> Any:
    existing = uow.campaigns.get_for_user(user_id=actor.id, campaign_id=campaign_id)
    if existing is None:
        raise not_found("Campaign")
    require_workspace_write(uow, user_id=actor.id, workspace_id=existing.workspace_id)
    updated = uow.campaigns.update(
        campaign_id=campaign_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _campaign_data(updated)


def delete_campaign(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    campaign_id: Any,
) -> Any:
    existing = uow.campaigns.get_for_user(user_id=actor.id, campaign_id=campaign_id)
    if existing is None:
        raise not_found("Campaign")
    require_workspace_write(uow, user_id=actor.id, workspace_id=existing.workspace_id)
    uow.campaigns.soft_delete(campaign_id=campaign_id)
    uow.commit()

    return {"deleted": True}
