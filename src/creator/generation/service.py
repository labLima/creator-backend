from __future__ import annotations

import hashlib
import json
import logging
from io import BytesIO
from math import gcd
from typing import cast
from uuid import UUID

from PIL import Image as PillowImage
from PIL import UnidentifiedImageError

from creator.application.errors import require_workspace_write
from creator.config import Settings
from creator.content.ports import ContentRecord, ContentTextVersionRecord
from creator.core.pagination import Page, PageRequest
from creator.domain.exceptions import (
    ConflictError,
    EntityNotFoundError,
    InvalidStateTransitionError,
)
from creator.domain.generation import GenerationJobStatus
from creator.generation.ports import (
    GeneratedImageRecord,
    GenerationJobRecord,
    GenerationQueue,
    GenerationRecord,
    ImageGenerationStatusRecord,
)
from creator.generation.schemas import IndependentGenerationRequest
from creator.post_structure.ports import PostStructureRecord
from creator.prompts import (
    RenderedPrompt,
    build_advertising_image_prompt,
    generation_parameters_with_prompt_template,
)
from creator.prompts.agents import build_agent_prompt
from creator.services.ai.image_provider import normalize_image_model
from creator.services.storage.provider import (
    StorageError,
    StorageObjectNotFoundError,
    StorageProvider,
)
from creator.uow import UnitOfWork
from creator.user.ports import UserRecord

MAX_GENERATION_PROMPT_LENGTH = 20_000
logger = logging.getLogger(__name__)


class GenerationApplication:
    """Application boundary for Generation and image job operations."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def list_generations(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None,
        content_id: UUID | None,
        page: PageRequest,
    ) -> Page[GenerationRecord]:
        return self._unit_of_work.generation.generations.list_for_user(
            user_id=user_id, workspace_id=workspace_id, content_id=content_id, page=page
        )

    def create_generation(
        self,
        *,
        user: UserRecord,
        workspace_id: UUID,
        content_id: UUID,
        generation_type: str,
        brand_id: UUID | None,
        project_id: UUID | None,
        model: str,
        prompt: str,
        parameters: dict[str, object] | None,
    ) -> GenerationRecord:
        require_workspace_write(self._unit_of_work, user_id=user.id, workspace_id=workspace_id)
        record = self._unit_of_work.generation.generations.add(
            workspace_id=workspace_id,
            content_id=content_id,
            requested_by_user_id=user.id,
            generation_type=generation_type,
            brand_id=brand_id,
            project_id=project_id,
            model=model,
            prompt=prompt,
            parameters=parameters,
        )
        self._unit_of_work.commit()
        return record

    def get_generation(self, *, user_id: UUID, generation_id: UUID) -> GenerationRecord | None:
        return self._unit_of_work.generation.generations.get_for_user(
            user_id=user_id, generation_id=generation_id
        )

    def update_generation(
        self,
        *,
        user_id: UUID,
        generation_id: UUID,
        model: str | None,
        prompt: str | None,
        parameters: dict[str, object] | None,
    ) -> GenerationRecord:
        record = self._unit_of_work.generation.generations.update(
            user_id=user_id,
            generation_id=generation_id,
            model=model,
            prompt=prompt,
            parameters=parameters,
        )
        self._unit_of_work.commit()
        return record

    def delete_generation(self, *, user_id: UUID, generation_id: UUID) -> None:
        self._unit_of_work.generation.generations.soft_delete(
            user_id=user_id, generation_id=generation_id
        )
        self._unit_of_work.commit()

    def get_generated_image(self, *, user_id: UUID, image_id: UUID) -> GeneratedImageRecord | None:
        return self._unit_of_work.generation.generated_images.get_for_user(
            user_id=user_id, image_id=image_id
        )

    def get_image_generation_status(
        self, *, user_id: UUID, job_id: UUID
    ) -> ImageGenerationStatusRecord | None:
        return self._unit_of_work.generation.image_jobs.get_status_for_user(
            user_id=user_id, job_id=job_id
        )

    def submit_image_generation(self, **kwargs: object) -> ImageGenerationStatusRecord:
        return submit_image_generation(unit_of_work=self._unit_of_work, **kwargs)  # type: ignore[arg-type]

    def submit_image_regeneration(self, **kwargs: object) -> ImageGenerationStatusRecord:
        return submit_image_regeneration(unit_of_work=self._unit_of_work, **kwargs)  # type: ignore[arg-type]

    def submit_independent_generation(self, **kwargs: object) -> GenerationJobRecord:
        return submit_independent_generation(unit_of_work=self._unit_of_work, **kwargs)  # type: ignore[arg-type]

    def get_independent_generation_job(
        self, *, user_id: UUID, job_id: UUID
    ) -> (
        tuple[
            GenerationJobRecord,
            ImageGenerationStatusRecord | None,
            list[ContentTextVersionRecord],
        ]
        | None
    ):
        jobs = self._unit_of_work.generation.image_jobs
        job = jobs.get_job_for_user(user_id=user_id, job_id=job_id)
        if job is None:
            return None
        status = jobs.get_status_for_user(user_id=user_id, job_id=job_id)
        if status is not None:
            request_input = status.parameters.get("request_input")
            if isinstance(request_input, dict) and request_input.get("brand_id"):
                try:
                    brand_id = UUID(str(request_input["brand_id"]))
                except ValueError:
                    return None
                brand = self._unit_of_work.brand.brands.get_for_user(
                    user_id=user_id, brand_id=brand_id
                )
                if brand is None or brand.workspace_id != job.workspace_id:
                    return None
        versions = (
            self._unit_of_work.contents.list_text_versions(
                user_id=user_id,
                content_id=job.content_id,
                generation_id=job.generation_id,
            )
            if job.artifact_type in {"COPY", "CAPTION"}
            else []
        )
        return job, status, versions

    def decide_independent_scene(
        self,
        *,
        user: UserRecord,
        job_id: UUID,
        approve: bool,
        queue: GenerationQueue,
        request_id: UUID,
        storage: StorageProvider,
    ) -> GenerationJobRecord:
        jobs = self._unit_of_work.generation.image_jobs
        details = self.get_independent_generation_job(user_id=user.id, job_id=job_id)
        status = details[1] if details is not None else None
        if status is None or status.job.artifact_type != "IMAGE":
            raise EntityNotFoundError("Generation Job not found")
        if status.job.status != GenerationJobStatus.PROCESSING:
            raise InvalidStateTransitionError("Generation Job is not awaiting scene review")
        require_workspace_write(
            self._unit_of_work, user_id=user.id, workspace_id=status.job.workspace_id
        )
        scene_review = status.parameters.get("scene_review")
        if not isinstance(scene_review, dict) or scene_review.get("status") not in {
            "PENDING",
            "APPROVED",
        }:
            raise InvalidStateTransitionError("Scene is not awaiting review")
        if not approve and scene_review.get("status") == "APPROVED":
            raise InvalidStateTransitionError("Approved scene cannot be rejected")
        updated = (
            jobs.decide_scene_review(job_id, approve=approve)
            if scene_review.get("status") == "PENDING"
            else status.job
        )
        should_enqueue = approve and scene_review.get("status") == "PENDING"
        self._unit_of_work.commit()
        if not approve:
            self._cleanup_rejected_scene(
                job_id=job_id,
                storage_path=scene_review.get("storage_path"),
                storage=storage,
            )
        if should_enqueue:
            try:
                queue.enqueue_image_generation(job_id=job_id, request_id=request_id)
            except Exception as error:
                jobs.reset_scene_review_approval(job_id)
                self._unit_of_work.commit()
                raise QueueEnqueueError("Generation Job could not be queued") from error
        return updated

    def _cleanup_rejected_scene(
        self, *, job_id: UUID, storage_path: object, storage: StorageProvider
    ) -> None:
        if not isinstance(storage_path, str) or not storage_path.startswith("scene-reviews/"):
            return
        try:
            try:
                storage.stat(storage_path)
            except StorageObjectNotFoundError:
                pass
            else:
                storage.delete(storage_path)
            self._unit_of_work.generation.image_jobs.complete_scene_review_cleanup(job_id)
            self._unit_of_work.commit()
        except Exception:
            # Keep cleanup_status=PENDING so the worker's cleanup loop can retry.
            logger.exception(
                "rejected_scene_cleanup_failed",
                extra={"generation_job_id": str(job_id)},
            )


class IdempotencyConflictError(ConflictError):
    """Raised when an idempotency key is reused with a different request."""


class QueueEnqueueError(RuntimeError):
    """Raised when a Generation Job cannot be enqueued."""


def submit_independent_generation(
    *,
    unit_of_work: UnitOfWork,
    queue: GenerationQueue,
    settings: Settings,
    user: UserRecord,
    payload: IndependentGenerationRequest,
    idempotency_key: str,
    request_id: UUID,
    storage: StorageProvider | None = None,
) -> GenerationJobRecord:
    """Authorize and enqueue one independent Content component Generation."""
    planning = None
    post_structure = None
    requested_brand_id = payload.brand_id
    if payload.planning_id is not None and payload.post_structure_id is not None:
        planning = unit_of_work.planning.get_for_user(
            user_id=user.id, planning_id=payload.planning_id
        )
        post_structure = unit_of_work.post_structures.get_for_user(
            user_id=user.id, post_structure_id=payload.post_structure_id
        )
        if (
            planning is None
            or post_structure is None
            or post_structure.planning_id != planning.id
            or (requested_brand_id is not None and requested_brand_id != planning.brand_id)
        ):
            raise EntityNotFoundError("Planning or Post Structure not found")
        requested_brand_id = planning.brand_id

    brand = (
        unit_of_work.brand.brands.get_for_user(user_id=user.id, brand_id=requested_brand_id)
        if requested_brand_id is not None
        else None
    )
    if brand is None:
        raise EntityNotFoundError("Brand not found")
    if post_structure is not None and post_structure.workspace_id != brand.workspace_id:
        raise EntityNotFoundError("Planning or Post Structure not found")

    briefing, direction = _generation_input_from_planning(
        payload=payload,
        planning_info=planning.info if planning is not None else None,
        post_structure=post_structure,
    )
    external_id = independent_generation_external_id(user.id, idempotency_key)
    fingerprint = _independent_generation_fingerprint(payload)
    jobs = unit_of_work.generation.image_jobs
    existing = jobs.get_job_by_external_id_for_user(user_id=user.id, external_id=external_id)
    if existing is not None:
        status = jobs.get_status_for_user(user_id=user.id, job_id=existing.id)
        prior_fingerprint = status.parameters.get("idempotency_fingerprint") if status else None
        if prior_fingerprint != fingerprint:
            raise IdempotencyConflictError("Idempotency key was reused with a different request")
        return existing

    source = None
    if payload.source_content_id is not None:
        source = unit_of_work.contents.get_by_id_for_user(
            user_id=user.id, content_id=payload.source_content_id
        )
        if (
            source is None
            or source.workspace_id != brand.workspace_id
            or source.brand_id != brand.id
        ):
            raise EntityNotFoundError("Source Content not found")
    source_image = None
    if payload.source_image_id is not None and source is not None:
        if storage is None:
            raise EntityNotFoundError("Source Content Version not found")
        if source.content_type != "IMAGE":
            raise EntityNotFoundError("Source Content Version not found")
        source_detail = unit_of_work.contents.get_detail_by_id_for_user(
            user_id=user.id, content_id=source.id
        )
        source_image = next(
            (
                image
                for image in (source_detail.images if source_detail is not None else [])
                if image.id == payload.source_image_id
            ),
            None,
        )
        if source_image is None or source_image.workspace_id != brand.workspace_id:
            raise EntityNotFoundError("Source Content Version not found")
        try:
            source_bytes = storage.download(
                source_image.storage_path, max_bytes=settings.storage_max_object_bytes
            )
            if len(source_bytes) > settings.storage_max_object_bytes:
                raise EntityNotFoundError("Source Content Version not found")
            with PillowImage.open(BytesIO(source_bytes)) as decoded:
                decoded.verify()
            with PillowImage.open(BytesIO(source_bytes)) as decoded:
                expected_format = {
                    "image/png": "PNG",
                    "image/jpeg": "JPEG",
                    "image/webp": "WEBP",
                }.get(source_image.mime_type)
                if (
                    expected_format is None
                    or decoded.format != expected_format
                    or decoded.size != (source_image.width, source_image.height)
                ):
                    raise EntityNotFoundError("Source Content Version not found")
            source_checksum = hashlib.sha256(source_bytes).hexdigest()
            recorded_checksum = source_image.metadata.get("storage_checksum_sha256")
            if recorded_checksum and recorded_checksum != source_checksum:
                raise EntityNotFoundError("Source Content Version not found")
        except (StorageError, UnidentifiedImageError, OSError, ValueError) as error:
            raise EntityNotFoundError("Source Content Version not found") from error
    else:
        source_checksum = None
    if not unit_of_work.contents.user_has_workspace_access(
        user_id=user.id, workspace_id=brand.workspace_id
    ):
        raise EntityNotFoundError("Brand not found")

    content = source
    if content is None:
        content = unit_of_work.contents.add(
            workspace_id=brand.workspace_id,
            created_by_user_id=user.id,
            content_type="IMAGE" if payload.artifact_type == "IMAGE" else "TEXT",
            brand_id=brand.id,
            title=payload.title
            or (post_structure.title if post_structure else None)
            or briefing[:255],
            payload={
                "artifact_type": payload.artifact_type,
                "planning_id": str(planning.id) if planning is not None else None,
                "post_structure_id": str(post_structure.id) if post_structure is not None else None,
            },
        )
    context = {
        "workspace_id": str(brand.workspace_id),
        "brand_id": str(brand.id),
        "brand_name": brand.name,
        "brand_voice": brand.brand_voice or "",
        "brand_description": brand.description or "",
        "artifact_type": payload.artifact_type,
        "operation": payload.operation,
        "source_content_id": str(source.id) if source else None,
    }
    source_text = None
    if source is not None and payload.artifact_type in {"COPY", "CAPTION"}:
        versions = unit_of_work.contents.list_text_versions(user_id=user.id, content_id=source.id)
        source_version = next(
            (item for item in reversed(versions) if item.artifact_type == payload.artifact_type),
            None,
        )
        source_text = source_version.text if source_version else None
    if payload.artifact_type == "IMAGE":
        rendered = build_advertising_image_prompt(
            context=context,
            user_input={
                "briefing": briefing,
                "visual_direction": direction,
                "restrictions": payload.restrictions,
            },
        )
        model = settings.openai_image_model
    else:
        rendered = build_agent_prompt(
            "Writer",
            {
                **context,
                "requested_component": payload.artifact_type,
                "briefing": briefing,
                "operation": payload.operation,
                "source_content": source.payload if source else None,
                "source_text": source_text,
                "preserve_source_facts_and_concept": payload.operation != "CREATE",
            },
            template_id=f"agent.writer.{payload.artifact_type.lower()}.v1",
            version="3.0",
            prompt_context=context,
        )
        model = settings.openai_text_model
    parameters: dict[str, object] = dict(rendered.metadata)
    parameters.update(
        {
            "request_input": payload.model_dump(mode="json"),
            "resolved_input": {"briefing": briefing, "direction": direction},
            "source_content": source.payload if source else None,
            "source_image": (
                {
                    "id": str(source_image.id),
                    "storage_path": source_image.storage_path,
                    "mime_type": source_image.mime_type,
                    "width": source_image.width,
                    "height": source_image.height,
                    "version_number": source_image.version_number,
                    "checksum_sha256": source_checksum,
                }
                if source_image is not None
                else None
            ),
            "destination_preset": payload.destination_preset,
            "destination_dimensions": (
                {
                    "width": int(payload.destination_preset.split("x")[0]),
                    "height": int(payload.destination_preset.split("x")[1]),
                    "ratio": _destination_ratio(payload.destination_preset),
                }
                if payload.destination_preset is not None
                else None
            ),
            "source_text": source_text,
            "review_image": payload.review_image,
            "idempotency_fingerprint": fingerprint,
            "prompt_template": {
                "id": rendered.template_id,
                "version": rendered.version,
                "input_hash": rendered.input_hash,
            },
        }
    )
    if post_structure is not None:
        parameters["image_options"] = {
            "aspect_ratio": post_structure.ratio,
            "resolution": post_structure.resolution,
        }
    try:
        job = jobs.create_image_generation(
            workspace_id=brand.workspace_id,
            content_id=content.id,
            brand_id=brand.id,
            requested_by_user_id=user.id,
            model=model,
            prompt=rendered.text,
            parameters=parameters,
            external_id=external_id,
            max_attempts=settings.image_generation_job_max_attempts,
            request_id=request_id,
            artifact_type=payload.artifact_type,
            operation=payload.operation,
            idempotency_key=idempotency_key,
        )
    except ConflictError as conflict_error:
        unit_of_work.rollback()
        existing = jobs.get_job_by_external_id_for_user(user_id=user.id, external_id=external_id)
        if existing is None:
            raise
        status = jobs.get_status_for_user(user_id=user.id, job_id=existing.id)
        prior_fingerprint = status.parameters.get("idempotency_fingerprint") if status else None
        if prior_fingerprint != fingerprint:
            raise IdempotencyConflictError(
                "Idempotency key was reused with a different request"
            ) from conflict_error
        return existing
    try:
        if payload.artifact_type == "IMAGE":
            queue.enqueue_image_generation(job_id=job.id, request_id=request_id)
        else:
            queue.enqueue_generation_job(job_id=job.id, request_id=request_id)
    except Exception as error:
        unit_of_work.rollback()
        raise QueueEnqueueError("Generation Job could not be queued") from error
    unit_of_work.commit()
    return job


def independent_generation_external_id(user_id: UUID, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"independent-generation:{user_id}:{digest}"


def _generation_input_from_planning(
    *,
    payload: IndependentGenerationRequest,
    planning_info: str | None,
    post_structure: PostStructureRecord | None,
) -> tuple[str, str | None]:
    if post_structure is None:
        return payload.briefing or "", payload.direction

    fields = {
        "Objetivo": post_structure.objective,
        "Ideia central": post_structure.big_idea,
        "Mensagem principal": post_structure.main_message,
        "Headline": post_structure.headline,
        "Chamada para ação": post_structure.image_cta,
    }
    briefing_parts = [f"{label}: {value}" for label, value in fields.items() if value]
    if planning_info:
        briefing_parts.insert(0, f"Contexto do Planning: {planning_info}")
    supplied_briefing = payload.briefing
    if supplied_briefing:
        briefing_parts.insert(0, supplied_briefing)
    if not briefing_parts:
        briefing_parts.append(post_structure.title or "Peça do Planning")

    direction_parts = [post_structure.art_guiding]
    direction_parts.extend(
        value
        for value in (
            f"Formato: {post_structure.format}" if post_structure.format else None,
            f"Proporção: {post_structure.ratio}" if post_structure.ratio else None,
            f"Resolução: {post_structure.resolution}" if post_structure.resolution else None,
        )
        if value
    )
    if payload.direction:
        direction_parts.append(payload.direction)
    direction = "\n".join(part for part in direction_parts if part) or (
        "Criar uma imagem publicitária coerente com o objetivo, a mensagem e o formato da peça."
    )
    return "\n".join(briefing_parts), direction


def _independent_generation_fingerprint(payload: IndependentGenerationRequest) -> str:
    normalized = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _destination_ratio(preset: str) -> str:
    width, height = (int(value) for value in preset.split("x"))
    divisor = gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def submit_image_generation(
    *,
    unit_of_work: UnitOfWork,
    queue: GenerationQueue,
    settings: Settings,
    user: UserRecord,
    content_id: UUID,
    style: str | None,
    idempotency_key: str,
    request_id: UUID,
) -> ImageGenerationStatusRecord:
    stored_settings = unit_of_work.user.settings.get_by_user_id(user.id)
    resolved_style = style or (stored_settings.visual_style if stored_settings else "photographic")
    external_id = image_generation_external_id(user.id, idempotency_key)
    request_fingerprint = image_generation_request_fingerprint(
        content_id=content_id,
        style=resolved_style,
    )
    existing = unit_of_work.generation.image_jobs.get_status_by_external_id_for_user(
        user_id=user.id,
        external_id=external_id,
    )
    if existing is not None:
        _raise_for_idempotency_mismatch(existing, request_fingerprint)
        return existing

    content = unit_of_work.contents.get_by_id_for_user(user_id=user.id, content_id=content_id)
    if content is None:
        raise EntityNotFoundError("Content not found")

    rendered_prompt = build_image_generation_prompt(
        content=content,
        style=resolved_style,
        settings_context={
            "brand_name": stored_settings.brand_name,
            "segment": stored_settings.segment,
            "tone": stored_settings.tone,
            "voice": stored_settings.voice,
            "visual_style": stored_settings.visual_style,
            "default_preferences": stored_settings.default_preferences,
        }
        if stored_settings
        else {},
    )
    parameters = generation_parameters_with_prompt_template(
        {
            "style": resolved_style,
            "idempotency": {"request_fingerprint": request_fingerprint},
        },
        rendered_prompt,
    )
    generation_parameters = cast(dict[str, object], parameters)

    try:
        job = unit_of_work.generation.image_jobs.create_image_generation(
            workspace_id=content.workspace_id,
            content_id=content.id,
            requested_by_user_id=user.id,
            model=settings.openai_image_model,
            prompt=rendered_prompt.text,
            parameters=generation_parameters,
            external_id=external_id,
            max_attempts=settings.image_generation_job_max_attempts,
            request_id=request_id,
        )
    except ConflictError:
        unit_of_work.rollback()
        existing = unit_of_work.generation.image_jobs.get_status_by_external_id_for_user(
            user_id=user.id,
            external_id=external_id,
        )
        if existing is None:
            raise
        _raise_for_idempotency_mismatch(existing, request_fingerprint)
        return existing

    try:
        queue.enqueue_image_generation(job_id=job.id, request_id=request_id)
    except Exception as error:
        unit_of_work.rollback()
        raise QueueEnqueueError("Image Generation Job could not be enqueued") from error

    unit_of_work.commit()
    return ImageGenerationStatusRecord(job=job, parameters=generation_parameters)


def submit_image_regeneration(
    *,
    unit_of_work: UnitOfWork,
    queue: GenerationQueue,
    settings: Settings,
    user: UserRecord,
    image_id: UUID,
    style: str | None,
    idempotency_key: str,
    request_id: UUID,
) -> ImageGenerationStatusRecord:
    original_image = unit_of_work.generation.image_jobs.get_image_for_user(
        user_id=user.id,
        image_id=image_id,
    )
    if original_image is None:
        raise EntityNotFoundError("Image not found")

    if original_image.prompt is None or original_image.generation_id is None:
        raise EntityNotFoundError("Generated image not found")

    stored_settings = unit_of_work.user.settings.get_by_user_id(user.id)
    resolved_style = (
        style
        or _style_from_metadata(original_image.metadata)
        or (stored_settings.visual_style if stored_settings else "photographic")
    )
    external_id = image_regeneration_external_id(user.id, idempotency_key)
    request_fingerprint = image_regeneration_request_fingerprint(
        image_id=image_id,
        style=resolved_style,
    )
    existing = unit_of_work.generation.image_jobs.get_status_by_external_id_for_user(
        user_id=user.id,
        external_id=external_id,
    )
    if existing is not None:
        _raise_for_idempotency_mismatch(existing, request_fingerprint)
        return existing

    regeneration_prompt = build_image_regeneration_prompt(
        original_prompt=original_image.prompt,
        style=resolved_style,
    )
    parameters = generation_parameters_with_prompt_template(
        {
            "style": resolved_style,
            "regenerated_from_image_id": str(original_image.id),
            "regenerated_from_generation_id": str(original_image.generation_id),
            "regenerated_from_version_number": original_image.version_number,
            "regenerated_from_model": original_image.model,
            "regenerated_from_prompt_sha256": hashlib.sha256(
                original_image.prompt.encode("utf-8")
            ).hexdigest(),
            "idempotency": {"request_fingerprint": request_fingerprint},
        },
        regeneration_prompt,
    )
    generation_parameters = cast(dict[str, object], parameters)
    model = normalize_image_model(original_image.model, default_model=settings.openai_image_model)
    if model != original_image.model:
        logger.info(
            "image_model_normalized",
            extra={
                "requested_model": original_image.model,
                "model": model,
                "image_id": str(original_image.id),
            },
        )

    try:
        job = unit_of_work.generation.image_jobs.create_image_generation(
            workspace_id=original_image.workspace_id,
            content_id=original_image.content_id,
            requested_by_user_id=user.id,
            model=model,
            prompt=regeneration_prompt.text,
            parameters=generation_parameters,
            external_id=external_id,
            max_attempts=settings.image_generation_job_max_attempts,
            request_id=request_id,
        )
    except ConflictError:
        unit_of_work.rollback()
        existing = unit_of_work.generation.image_jobs.get_status_by_external_id_for_user(
            user_id=user.id,
            external_id=external_id,
        )
        if existing is None:
            raise
        _raise_for_idempotency_mismatch(existing, request_fingerprint)
        return existing

    try:
        queue.enqueue_image_generation(job_id=job.id, request_id=request_id)
    except Exception as error:
        unit_of_work.rollback()
        raise QueueEnqueueError("Image Generation Job could not be enqueued") from error

    unit_of_work.commit()
    return ImageGenerationStatusRecord(job=job, parameters=generation_parameters)


def build_image_generation_prompt(
    *,
    content: ContentRecord,
    style: str,
    settings_context: dict[str, object] | None = None,
) -> RenderedPrompt:
    return build_advertising_image_prompt(
        context={
            "workspace_id": str(content.workspace_id),
            "content_type": content.content_type,
            "settings": settings_context or {},
        },
        user_input={
            "content_id": str(content.id),
            "title": content.title,
            "content": content.payload,
            "style": style,
        },
    )


def build_image_regeneration_prompt(*, original_prompt: str, style: str) -> RenderedPrompt:
    prompt = _render_image_regeneration_prompt(original_prompt=original_prompt, style=style)
    while len(prompt.text) > MAX_GENERATION_PROMPT_LENGTH and len(original_prompt) > 1:
        overflow = len(prompt.text) - MAX_GENERATION_PROMPT_LENGTH
        original_prompt = original_prompt[: max(1, len(original_prompt) - overflow - 256)]
        prompt = _render_image_regeneration_prompt(
            original_prompt=f"{original_prompt}\n[truncated to fit Generation prompt limit]",
            style=style,
        )
    return prompt


def _render_image_regeneration_prompt(*, original_prompt: str, style: str) -> RenderedPrompt:
    return build_advertising_image_prompt(
        context={
            "operation": "image_regeneration",
            "source": "original_image_prompt",
            "preserve_original_content_context": True,
        },
        user_input={
            "style": style,
            "instruction": (
                "Regenerate a new image version from the original prompt below. "
                "Preserve the original content, business context, composition intent, and "
                "constraints. Apply only the requested style change when it differs from "
                "the original."
            ),
            "original_prompt": original_prompt,
        },
        metadata={"regeneration": True},
    )


def image_generation_external_id(user_id: UUID, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"image-generate:{user_id}:{digest}"


def image_regeneration_external_id(user_id: UUID, idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"image-regenerate:{user_id}:{digest}"


def image_generation_request_fingerprint(*, content_id: UUID, style: str) -> str:
    payload = json.dumps(
        {"content_id": str(content_id), "style": style},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def image_regeneration_request_fingerprint(*, image_id: UUID, style: str) -> str:
    payload = json.dumps(
        {"image_id": str(image_id), "style": style},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _style_from_metadata(metadata: dict[str, object]) -> str | None:
    style = metadata.get("style")
    return style if isinstance(style, str) else None


def _raise_for_idempotency_mismatch(
    status: ImageGenerationStatusRecord,
    request_fingerprint: str,
) -> None:
    idempotency = status.parameters.get("idempotency")
    if not isinstance(idempotency, dict):
        raise IdempotencyConflictError("Idempotency metadata is missing")
    if idempotency.get("request_fingerprint") != request_fingerprint:
        raise IdempotencyConflictError("Idempotency key was reused with a different request")
