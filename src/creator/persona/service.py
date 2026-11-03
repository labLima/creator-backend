"""Use cases for the persona capability."""

from __future__ import annotations

from typing import Any

from creator.api.errors import not_found, require_workspace_write
from creator.api.responses import page_payload
from creator.api.serializers import _persona_data
from creator.core.pagination import page_request
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


def list_personas(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    brand_id: Any,
    page: Any,
    limit: Any,
    sort: Any,
) -> Any:
    result = uow.personas.list_for_user(
        user_id=actor.id,
        brand_id=brand_id,
        page=page_request(page, limit, sort),
    )

    return page_payload(result, _persona_data)


def create_persona(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    payload: Any,
) -> Any:
    brand = uow.brands.get_for_user(user_id=actor.id, brand_id=payload.brand_id)
    if brand is None:
        raise not_found("Brand")
    require_workspace_write(uow, user_id=actor.id, workspace_id=brand.workspace_id)
    persona = uow.personas.add(
        created_by=actor.id,
        **payload.model_dump(),
    )
    uow.commit()

    return _persona_data(persona)


def get_persona(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    persona_id: Any,
) -> Any:
    persona = uow.personas.get_for_user(user_id=actor.id, persona_id=persona_id)
    if persona is None:
        raise not_found("Persona")

    return _persona_data(persona)


def update_persona(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    persona_id: Any,
    payload: Any,
) -> Any:
    existing = uow.personas.get_for_user(user_id=actor.id, persona_id=persona_id)
    if existing is None:
        raise not_found("Persona")
    brand = uow.brands.get_for_user(user_id=actor.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Persona")
    require_workspace_write(uow, user_id=actor.id, workspace_id=brand.workspace_id)
    updated = uow.personas.update(
        persona_id=persona_id, fields=payload.model_dump(exclude_unset=True)
    )
    uow.commit()

    return _persona_data(updated)


def delete_persona(
    *,
    uow: UnitOfWork,
    actor: UserRecord,
    request: Any,
    persona_id: Any,
) -> Any:
    existing = uow.personas.get_for_user(user_id=actor.id, persona_id=persona_id)
    if existing is None:
        raise not_found("Persona")
    brand = uow.brands.get_for_user(user_id=actor.id, brand_id=existing.brand_id)
    if brand is None:
        raise not_found("Persona")
    require_workspace_write(uow, user_id=actor.id, workspace_id=brand.workspace_id)
    uow.personas.soft_delete(persona_id=persona_id)
    uow.commit()

    return {"deleted": True}
