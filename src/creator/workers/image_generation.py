from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from creator.brand.ports import BrandRecord
from creator.config import Settings, get_settings
from creator.core.types import JsonObject
from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.domain.auth import Principal, WorkspaceRole
from creator.domain.exceptions import InvalidStateTransitionError
from creator.generation.ports import ImageGenerationWorkItem
from creator.generation.storage_service import GeneratedImage, persist_generated_image
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.infrastructure.runtime.observability import correlation_context
from creator.infrastructure.runtime.storage import create_storage_provider
from creator.integrations.gemini.exceptions import (
    GeminiAuthenticationError,
    GeminiBlockedContentError,
    GeminiInvalidResponseError,
    GeminiProviderError,
    GeminiQuotaError,
    GeminiTimeoutError,
    GeminiTransientError,
)
from creator.services.agents.contracts import (
    AgentExecutionContext,
    ArtistOutput,
    WorkspaceAuthorizationContext,
)
from creator.services.agents.errors import AgentKickoffError, AgentKickoffErrorCode
from creator.services.agents.factory import create_specialist_executor
from creator.services.ai.factory import create_image_reviewer
from creator.services.ai.image_provider import (
    ImageGenerationRequest,
    ImageProviderAuthenticationError,
    ImageProviderBlockedError,
    ImageProviderError,
    ImageProviderInvalidResponseError,
    ImageProviderQuotaError,
    ImageProviderTimeoutError,
    ImageProviderTransientError,
    create_image_generator,
    normalize_image_model,
)
from creator.services.ai.provider import ProviderNotConfiguredError
from creator.services.ai.reviewer import ImageReviewRequest
from creator.services.storage.provider import StorageError

logger = logging.getLogger(__name__)


def run_image_generation(job_id: str, request_id: str | None = None) -> None:
    try:
        parsed_job_id = UUID(job_id)
    except ValueError:
        return
    parsed_request_id = _safe_uuid(request_id)
    with correlation_context(request_id=parsed_request_id, job_id=parsed_job_id):
        _run_image_generation(parsed_job_id, parsed_request_id)


def _run_image_generation(parsed_job_id: UUID, parsed_request_id: UUID | None) -> None:
    started_at = time.perf_counter()

    work_item = _claim_work_item(parsed_job_id)
    if work_item is None:
        return

    _log(
        "image_generation_started",
        request_id=parsed_request_id,
        job_id=parsed_job_id,
        attempt=work_item.job.attempt_count,
    )
    settings = get_settings()
    try:
        request_input = work_item.parameters.get("request_input")
        artist_metadata: dict[str, object] = {}
        prompt = work_item.prompt
        briefing: str | None = None
        if isinstance(request_input, dict) and request_input.get("artifact_type") == "IMAGE":
            brand = _authorized_brand(work_item)
            if brand is None:
                _settle_failure(
                    parsed_job_id,
                    "BRAND_CONTEXT_UNAVAILABLE",
                    request_id=parsed_request_id,
                    attempt=work_item.job.attempt_count,
                    started_at=started_at,
                )
                return
            prompt_inputs = _prompt_inputs(work_item, request_input)
            if prompt_inputs is None:
                _settle_failure(
                    parsed_job_id,
                    "PROMPT_CONTEXT_UNAVAILABLE",
                    request_id=parsed_request_id,
                    attempt=work_item.job.attempt_count,
                    started_at=started_at,
                )
                return
            briefing, direction = prompt_inputs
            operation = request_input.get("operation")
            if not isinstance(operation, str):
                operation = "CREATE"
            artist_result = create_specialist_executor(settings).execute(
                AgentExecutionContext(
                    workspace_id=work_item.job.workspace_id,
                    brand_id=brand.id,
                    authorization=WorkspaceAuthorizationContext(
                        principal=Principal(subject=work_item.requested_by_user.external_id),
                        workspace_id=work_item.job.workspace_id,
                        workspace_role=WorkspaceRole.EDITOR,
                    ),
                    role=AgentWorkflowStepRole.ARTIST,
                    inputs={
                        "briefing": briefing,
                        "visual_direction": direction,
                        "operation": operation,
                        "source_content": work_item.parameters.get("source_content"),
                        "preserve_source_concept": operation != "CREATE",
                        "brand_context": {
                            "name": brand.name,
                            "description": brand.description or "",
                            "brand_voice": brand.brand_voice or "",
                        },
                        "restrictions": request_input.get("restrictions", []),
                    },
                    prompt_template_id="agent.artist.v3",
                    prompt_template_version="3.0",
                    schema_version="1.0",
                    output_contract="IMAGE",
                )
            )
            artist_output = ArtistOutput.model_validate(artist_result.output)
            prompt = artist_output.visual_prompt
            artist_metadata = {
                "artist": {
                    "provider": artist_result.provider,
                    "model": artist_result.model,
                    "prompt_template_id": artist_result.prompt_template_id,
                    "prompt_template_version": artist_result.prompt_template_version,
                    "prompt_input_hash": artist_result.input_hash,
                    "output_hash": artist_result.output_hash,
                    "schema_name": artist_result.schema_name,
                    "schema_version": artist_result.schema_version,
                }
            }
        model = normalize_image_model(work_item.model, default_model=settings.openai_image_model)
        if model != work_item.model:
            logger.info(
                "image_model_normalized",
                extra={
                    "requested_model": work_item.model,
                    "model": model,
                    "generation_job_id": str(work_item.job.id),
                },
            )
        result = create_image_generator(settings).generate(
            ImageGenerationRequest(
                prompt=prompt,
                model=model,
                metadata=_image_request_metadata(work_item),
                size=_image_request_size(work_item),
                aspect_ratio=_image_request_option(work_item, "aspect_ratio"),
                resolution=_image_request_option(work_item, "resolution"),
            )
        )
        image_metadata = dict(result.metadata)
        image_metadata.update(artist_metadata)
        if isinstance(request_input, dict) and request_input.get("review_image") is True:
            image_metadata["review"] = _review_generated_image(
                settings=settings,
                work_item=work_item,
                image_bytes=result.image_bytes,
                mime_type=result.mime_type,
                prompt=result.prompt,
                briefing=briefing,
                request_id=parsed_request_id,
            )
        with SqlAlchemyUnitOfWork() as unit_of_work:
            persist_generated_image(
                unit_of_work=unit_of_work,
                storage=create_storage_provider(settings),
                job=work_item.job,
                user=work_item.requested_by_user,
                image=GeneratedImage(
                    content=result.image_bytes,
                    mime_type=result.mime_type,
                    width=result.width,
                    height=result.height,
                    model=result.model,
                    prompt=result.prompt,
                    metadata=image_metadata,
                ),
            )
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        _log(
            "image_generation_completed",
            request_id=parsed_request_id,
            job_id=parsed_job_id,
            attempt=work_item.job.attempt_count,
            duration_ms=duration_ms,
        )
    except StorageError:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        # Storage validation/configuration failures are not transient.  The
        # persistence layer handles upload failures when it can recover an
        # already-uploaded object; every other storage failure must still
        # terminally settle the Generation Job.
        _fail_job(parsed_job_id, "STORAGE_UPLOAD_FAILED")
        _log(
            "image_generation_failed",
            request_id=parsed_request_id,
            job_id=parsed_job_id,
            attempt=work_item.job.attempt_count,
            duration_ms=duration_ms,
            failure_code="STORAGE_UPLOAD_FAILED",
        )
        return
    except ProviderNotConfiguredError:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        _fail_job(parsed_job_id, "PROVIDER_AUTHENTICATION_FAILED")
        _log(
            "image_generation_failed",
            request_id=parsed_request_id,
            job_id=parsed_job_id,
            attempt=work_item.job.attempt_count,
            duration_ms=duration_ms,
            failure_code="PROVIDER_AUTHENTICATION_FAILED",
        )
    except AgentKickoffError as error:
        retryable = error.code in {
            AgentKickoffErrorCode.PROVIDER_FAILURE,
            AgentKickoffErrorCode.PROVIDER_UNAVAILABLE,
        }
        failure_code = error.code.value
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        if retryable and work_item.job.attempt_count < work_item.job.max_attempts:
            _log(
                "image_generation_retryable_failure",
                request_id=parsed_request_id,
                job_id=parsed_job_id,
                attempt=work_item.job.attempt_count,
                duration_ms=duration_ms,
                failure_code=failure_code,
            )
            raise
        _fail_job(parsed_job_id, failure_code)
        _log(
            "image_generation_failed",
            request_id=parsed_request_id,
            job_id=parsed_job_id,
            attempt=work_item.job.attempt_count,
            duration_ms=duration_ms,
            failure_code=failure_code,
        )
    except (GeminiProviderError, ImageProviderError) as error:
        failure_code = _provider_failure_code(error)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        if error.retryable and work_item.job.attempt_count < work_item.job.max_attempts:
            _log(
                "image_generation_retryable_failure",
                request_id=parsed_request_id,
                job_id=parsed_job_id,
                attempt=work_item.job.attempt_count,
                duration_ms=duration_ms,
                failure_code=failure_code,
            )
            raise
        _fail_job(parsed_job_id, failure_code)
        _log(
            "image_generation_failed",
            request_id=parsed_request_id,
            job_id=parsed_job_id,
            attempt=work_item.job.attempt_count,
            duration_ms=duration_ms,
            failure_code=failure_code,
        )
    except Exception:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        # Only provider errors explicitly classified as retryable are raised
        # above.  Unknown application errors are permanent from the queue's
        # perspective: retrying them can duplicate side effects and hides a
        # programming/configuration defect behind RQ retries.
        _fail_job(parsed_job_id, "IMAGE_GENERATION_FAILED")
        _log(
            "image_generation_failed",
            request_id=parsed_request_id,
            job_id=parsed_job_id,
            attempt=work_item.job.attempt_count,
            duration_ms=duration_ms,
            failure_code="IMAGE_GENERATION_FAILED",
        )


def recover_stale_processing_jobs() -> int:
    settings = get_settings()
    older_than = datetime.now(UTC) - timedelta(
        seconds=settings.image_generation_stale_processing_seconds
    )
    with SqlAlchemyUnitOfWork() as unit_of_work:
        recovered = unit_of_work.generation.image_jobs.fail_stale_processing(
            older_than=older_than,
            failure_code="IMAGE_GENERATION_STALE_PROCESSING",
            failure_message="Image generation did not finish before the processing timeout",
        )
        unit_of_work.commit()
        if recovered:
            logger.warning(
                "image_generation_stale_jobs_failed",
                extra={"recovered_count": recovered},
            )
        return recovered


def _review_generated_image(
    *,
    settings: Settings,
    work_item: ImageGenerationWorkItem,
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    briefing: str | None,
    request_id: UUID | None,
) -> dict[str, object]:
    if briefing is None:
        return _review_failure("PROMPT_CONTEXT_UNAVAILABLE", work_item, request_id)
    brand = _authorized_brand(work_item)
    if brand is None:
        return _review_failure("BRAND_CONTEXT_UNAVAILABLE", work_item, request_id)
    try:
        review = create_image_reviewer(settings).review(
            ImageReviewRequest(
                image_bytes=image_bytes,
                mime_type=mime_type,
                prompt=prompt,
                briefing=briefing,
                brand_context={
                    "brand_id": str(brand.id),
                    "name": brand.name,
                    "description": brand.description or "",
                    "brand_voice": brand.brand_voice or "",
                },
            )
        )
    except (ImageProviderError, GeminiProviderError, ProviderNotConfiguredError) as error:
        return _review_failure(_review_failure_code(error), work_item, request_id)
    except Exception:
        # Automated Review is best-effort: SDK/transport failures from a
        # legacy reviewer must not fail an image that was already generated.
        return _review_failure("IMAGE_REVIEW_FAILED", work_item, request_id)
    return {
        "decision": review.decision,
        "score": review.score,
        "feedback": list(review.feedback),
        "safety_issues": list(review.safety_issues),
        "provider": review.provider,
        "model": review.model,
    }


def _review_failure(
    error_code: str,
    work_item: ImageGenerationWorkItem,
    request_id: UUID | None,
) -> dict[str, object]:
    _log(
        "image_review_failed",
        request_id=request_id,
        job_id=work_item.job.id,
        attempt=work_item.job.attempt_count,
        failure_code=error_code,
    )
    return {"status": "failed", "error_code": error_code}


def _review_failure_code(
    error: ImageProviderError | GeminiProviderError | ProviderNotConfiguredError,
) -> str:
    if isinstance(error, ProviderNotConfiguredError):
        return "PROVIDER_AUTHENTICATION_FAILED"
    return _provider_failure_code(error)


def _prompt_inputs(
    work_item: ImageGenerationWorkItem, request_input: object
) -> tuple[str, str] | None:
    resolved_input = work_item.parameters.get("resolved_input")
    briefing = _text_input(resolved_input, "briefing") or _text_input(request_input, "briefing")
    direction = _text_input(resolved_input, "direction") or _text_input(request_input, "direction")
    if briefing is None or direction is None:
        return None
    return briefing, direction


def _text_input(source: object, key: str) -> str | None:
    if not isinstance(source, dict):
        return None
    value = source.get(key)
    return value if isinstance(value, str) and value else None


def _authorized_brand(work_item: ImageGenerationWorkItem) -> BrandRecord | None:
    if work_item.brand_id is None:
        return None
    with SqlAlchemyUnitOfWork() as unit_of_work:
        brand = unit_of_work.brand.brands.get_for_user(
            user_id=work_item.requested_by_user.id,
            brand_id=work_item.brand_id,
        )
    if brand is None or brand.workspace_id != work_item.job.workspace_id:
        return None
    return brand


def _settle_failure(
    job_id: UUID,
    failure_code: str,
    *,
    request_id: UUID | None,
    attempt: int,
    started_at: float,
) -> None:
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    _fail_job(job_id, failure_code)
    _log(
        "image_generation_failed",
        request_id=request_id,
        job_id=job_id,
        attempt=attempt,
        duration_ms=duration_ms,
        failure_code=failure_code,
    )


def _claim_work_item(job_id: UUID) -> ImageGenerationWorkItem | None:
    with SqlAlchemyUnitOfWork() as unit_of_work:
        work_item = unit_of_work.generation.image_jobs.claim_pending_by_id(job_id)
        if work_item is None:
            return None
        unit_of_work.commit()
        return work_item


def _fail_job(job_id: UUID, failure_code: str) -> None:
    with SqlAlchemyUnitOfWork() as unit_of_work:
        try:
            unit_of_work.generation.image_jobs.fail_job(
                job_id,
                failure_code=failure_code,
                failure_message="Image generation failed",
            )
        except InvalidStateTransitionError:
            return
        unit_of_work.commit()


def _image_request_metadata(work_item: ImageGenerationWorkItem) -> JsonObject:
    metadata: JsonObject = {}
    style = work_item.parameters.get("style")
    if isinstance(style, str):
        metadata["style"] = style

    prompt_template = work_item.parameters.get("prompt_template")
    if isinstance(prompt_template, dict):
        template_id = prompt_template.get("id")
        template_version = prompt_template.get("version")
        input_hash = prompt_template.get("input_hash")
        if isinstance(template_id, str):
            metadata["prompt_template_id"] = template_id
        if isinstance(template_version, str):
            metadata["prompt_template_version"] = template_version
        if isinstance(input_hash, str):
            metadata["prompt_input_hash"] = input_hash
    return metadata


def _image_request_size(work_item: ImageGenerationWorkItem) -> str | None:
    value = work_item.parameters.get("image_size")
    return value if isinstance(value, str) else None


def _image_request_option(work_item: ImageGenerationWorkItem, name: str) -> str | None:
    options = work_item.parameters.get("image_options")
    if not isinstance(options, dict):
        return None
    value = options.get(name)
    return value if isinstance(value, str) else None


def _provider_failure_code(error: GeminiProviderError | ImageProviderError) -> str:
    if isinstance(error, (GeminiAuthenticationError, ImageProviderAuthenticationError)):
        return "PROVIDER_AUTHENTICATION_FAILED"
    if isinstance(error, (GeminiQuotaError, ImageProviderQuotaError)):
        return "PROVIDER_QUOTA_EXCEEDED"
    if isinstance(error, (GeminiTimeoutError, ImageProviderTimeoutError)):
        return "PROVIDER_TIMEOUT"
    if isinstance(error, (GeminiBlockedContentError, ImageProviderBlockedError)):
        return "PROVIDER_CONTENT_BLOCKED"
    if isinstance(error, (GeminiInvalidResponseError, ImageProviderInvalidResponseError)):
        return "PROVIDER_INVALID_RESPONSE"
    if isinstance(error, (GeminiTransientError, ImageProviderTransientError)):
        return "PROVIDER_TRANSIENT_FAILED"
    return "PROVIDER_FAILED"


def _safe_uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _log(
    event: str,
    *,
    request_id: UUID | None,
    job_id: UUID,
    attempt: int,
    duration_ms: int | None = None,
    failure_code: str | None = None,
) -> None:
    payload: dict[str, object] = {
        "request_id": str(request_id) if request_id else None,
        "generation_job_id": str(job_id),
        "attempt": attempt,
    }
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if failure_code is not None:
        payload["failure_code"] = failure_code
    if failure_code is None and event.endswith("completed"):
        logger.info(event, extra=payload)
    elif event.endswith("started"):
        logger.info(event, extra=payload)
    else:
        logger.warning(event, extra=payload)
