"""Use cases for the content capability.

The generation and improvement pipelines keep their own focused modules; this
module is the single service entry point for the capability.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast
from uuid import UUID

from creator.application.errors import require_workspace_write
from creator.config import Settings
from creator.content.generation_service import (
    GenerateContentCommand,
    generate_content,
)
from creator.content.image_import import authorize_import, import_image
from creator.content.improvement_service import (
    ImproveContentCommand,
    ImprovedContentPreview,
    improve_content,
)
from creator.content.ports import (
    ContentDetailRecord,
    ContentFilters,
    ContentRecord,
    GeneratedTextContentRecord,
)
from creator.core.pagination import Page, PageRequest
from creator.domain.exceptions import EntityNotFoundError
from creator.post_structure.ports import PostStructureRecord
from creator.services.ai.provider import LLMProvider
from creator.services.storage.provider import StorageProvider
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord


class ContentApplication:
    """Application boundary for Content and Post Structure persistence."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def authorize_image_import(self, *, user: UserRecord, brand_id: UUID) -> UUID:
        return authorize_import(self._unit_of_work, user, brand_id)

    def import_image(
        self,
        *,
        storage: StorageProvider,
        user: UserRecord,
        brand_id: UUID,
        workspace_id: UUID,
        content: bytes,
        mime_type: str | None,
        title: str | None,
    ) -> ContentDetailRecord:
        return import_image(
            uow=self._unit_of_work,
            storage=storage,
            user=user,
            brand_id=brand_id,
            workspace_id=workspace_id,
            content=content,
            mime_type=mime_type,
            title=title,
        )

    def generate_content(
        self,
        *,
        settings: Settings,
        llm_provider: LLMProvider,
        user: UserRecord,
        command: GenerateContentCommand,
    ) -> GeneratedTextContentRecord:
        return generate_content(
            unit_of_work=self._unit_of_work,
            settings=settings,
            llm_provider=llm_provider,
            user=user,
            command=command,
        )

    def improve_content(
        self,
        *,
        settings: Settings,
        llm_provider: LLMProvider,
        user: UserRecord,
        command: ImproveContentCommand,
    ) -> ImprovedContentPreview:
        return improve_content(
            unit_of_work=self._unit_of_work,
            settings=settings,
            llm_provider=llm_provider,
            user=user,
            command=command,
        )

    def create_content(
        self,
        *,
        user: UserRecord,
        workspace_id: UUID,
        content_type: str,
        brand_id: UUID | None,
        project_id: UUID | None,
        title: str | None,
        payload: dict[str, object],
        planning_id: UUID | None,
    ) -> ContentRecord | PostStructureRecord:
        require_workspace_write(self._unit_of_work, user_id=user.id, workspace_id=workspace_id)
        if planning_id is not None:
            post_fields = {
                key: value
                for key, value in payload.items()
                if key
                in {
                    "objective",
                    "big_idea",
                    "main_message",
                    "headline",
                    "image_cta",
                    "art_guiding",
                    "status",
                    "format",
                    "ratio",
                    "resolution",
                }
            }
            post_structure = self._unit_of_work.post_structures.add(
                workspace_id=workspace_id,
                planning_id=planning_id,
                created_by=user.id,
                title=title,
                **cast(dict[str, str | None], post_fields),
            )
        else:
            content = self._unit_of_work.contents.add(
                workspace_id=workspace_id,
                created_by_user_id=user.id,
                content_type=content_type,
                brand_id=brand_id,
                project_id=project_id,
                title=title,
                payload=payload,
            )
        self._unit_of_work.commit()
        return post_structure if planning_id is not None else content

    def get_post_structure(self, *, user_id: UUID, item_id: UUID) -> PostStructureRecord | None:
        return self._unit_of_work.post_structures.get_for_user(
            user_id=user_id, post_structure_id=item_id
        )

    def get_detail(self, *, user_id: UUID, content_id: UUID) -> ContentDetailRecord | None:
        detail = self._unit_of_work.contents.get_detail_by_id_for_user(
            user_id=user_id, content_id=content_id
        )
        if detail is None:
            return None
        return replace(detail, content=self._resolve_workflow_status(user_id, [detail.content])[0])

    def get_content(self, *, user_id: UUID, content_id: UUID) -> ContentRecord | None:
        content = self._unit_of_work.contents.get_by_id_for_user(
            user_id=user_id, content_id=content_id
        )
        return self._resolve_workflow_status(user_id, [content])[0] if content else None

    def update_post_structure(
        self,
        *,
        user: UserRecord,
        item_id: UUID,
        title: str | None,
        payload: dict[str, object] | None,
    ) -> PostStructureRecord:
        record = self.get_post_structure(user_id=user.id, item_id=item_id)
        if record is None:
            raise EntityNotFoundError("Content not found")
        require_workspace_write(
            self._unit_of_work, user_id=user.id, workspace_id=record.workspace_id
        )
        allowed = {
            "objective",
            "big_idea",
            "main_message",
            "headline",
            "image_cta",
            "art_guiding",
            "status",
            "format",
            "ratio",
            "resolution",
        }
        fields = {key: value for key, value in (payload or {}).items() if key in allowed}
        if title is not None:
            fields["title"] = title
        updated = self._unit_of_work.post_structures.update(
            post_structure_id=item_id, fields=cast(dict[str, str | None], fields)
        )
        if updated is None:
            raise EntityNotFoundError("Content not found")
        self._unit_of_work.commit()
        return updated

    def update_content(
        self,
        *,
        user: UserRecord,
        content_id: UUID,
        brand_id: UUID | None,
        project_id: UUID | None,
        title: str | None,
        payload: dict[str, object] | None,
    ) -> ContentRecord:
        existing = self.get_content(user_id=user.id, content_id=content_id)
        if existing is None:
            raise EntityNotFoundError("Content not found")
        require_workspace_write(
            self._unit_of_work, user_id=user.id, workspace_id=existing.workspace_id
        )
        updated = self._unit_of_work.contents.update(
            content_id,
            user_id=user.id,
            brand_id=brand_id,
            project_id=project_id,
            title=title,
            payload=payload,
        )
        self._unit_of_work.commit()
        return self._resolve_workflow_status(user.id, [updated])[0]

    def delete_post_structure(self, *, user: UserRecord, item_id: UUID) -> None:
        record = self.get_post_structure(user_id=user.id, item_id=item_id)
        if record is None:
            raise EntityNotFoundError("Content not found")
        require_workspace_write(
            self._unit_of_work, user_id=user.id, workspace_id=record.workspace_id
        )
        self._unit_of_work.post_structures.soft_delete(post_structure_id=item_id)
        self._unit_of_work.commit()

    def delete_content(self, *, user: UserRecord, content_id: UUID) -> None:
        record = self._unit_of_work.contents.get_by_id_for_user(
            user_id=user.id, content_id=content_id, include_deleted=True
        )
        if record is None:
            raise EntityNotFoundError("Content not found")
        require_workspace_write(
            self._unit_of_work, user_id=user.id, workspace_id=record.workspace_id
        )
        self._unit_of_work.contents.soft_delete(user_id=user.id, content_id=content_id)
        self._unit_of_work.commit()

    def list_post_structures(
        self, *, user_id: UUID, planning_id: UUID, page: PageRequest
    ) -> Page[PostStructureRecord]:
        return self._unit_of_work.post_structures.list_for_user(
            user_id=user_id, planning_id=planning_id, page=page
        )

    def list_content(
        self, *, user_id: UUID, filters: ContentFilters, page: PageRequest
    ) -> Page[ContentRecord]:
        results = self._unit_of_work.contents.list_for_user(
            user_id=user_id, filters=filters, page=page
        )
        return replace(results, items=self._resolve_workflow_status(user_id, results.items))

    def _resolve_workflow_status(
        self, user_id: UUID, items: list[ContentRecord]
    ) -> list[ContentRecord]:
        candidates = [item.id for item in items if "workflow_status" in item.payload]
        if not candidates:
            return items
        statuses = self._unit_of_work.agent_workflow.workflows.statuses_for_content(
            user_id=user_id, content_ids=candidates
        )
        return [
            replace(item, payload={**item.payload, "workflow_status": statuses[item.id].value})
            if item.id in statuses
            else item
            for item in items
        ]


__all__ = [
    "GenerateContentCommand",
    "ImproveContentCommand",
    "ImprovedContentPreview",
    "generate_content",
    "improve_content",
]
