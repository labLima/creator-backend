"""Worker entry point for provider-neutral, non-image Generation Jobs."""

from __future__ import annotations

import logging
from uuid import UUID

from creator.config import get_settings
from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.domain.auth import Principal, WorkspaceRole
from creator.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from creator.infrastructure.runtime.observability import correlation_context
from creator.services.agents.contracts import (
    AgentExecutionContext,
    WorkspaceAuthorizationContext,
    WriterCaptionOutput,
    WriterCopyOutput,
)
from creator.services.agents.errors import AgentKickoffError, AgentKickoffErrorCode
from creator.services.agents.factory import create_specialist_executor
from creator.services.ai.provider import ProviderNotConfiguredError

logger = logging.getLogger(__name__)


def run_generation_job(job_id: str, request_id: str | None = None) -> None:
    try:
        parsed_job_id = UUID(job_id)
        parsed_request_id = UUID(request_id) if request_id else None
    except ValueError:
        return
    with correlation_context(request_id=parsed_request_id, job_id=parsed_job_id):
        _run_text_job(parsed_job_id)


def _run_text_job(job_id: UUID) -> None:
    with SqlAlchemyUnitOfWork() as unit_of_work:
        work_item = unit_of_work.generation.image_jobs.claim_pending_by_id(
            job_id, artifact_type="COPY"
        )
        if work_item is None:
            work_item = unit_of_work.generation.image_jobs.claim_pending_by_id(
                job_id, artifact_type="CAPTION"
            )
        if work_item is None:
            return
        unit_of_work.commit()

    try:
        input_data = work_item.parameters.get("request_input")
        if not isinstance(input_data, dict):
            raise ValueError("Generation Job input is missing")
        artifact_type = work_item.job.artifact_type
        role = AgentWorkflowStepRole.WRITER
        settings = get_settings()
        brand_id = UUID(str(input_data["brand_id"]))
        with SqlAlchemyUnitOfWork() as unit_of_work:
            brand = unit_of_work.brand.brands.get_for_user(
                user_id=work_item.requested_by_user.id,
                brand_id=brand_id,
            )
        if brand is None or brand.workspace_id != work_item.job.workspace_id:
            raise ValueError("Brand authorization is no longer valid")
        execution = AgentExecutionContext(
            workspace_id=work_item.job.workspace_id,
            brand_id=brand_id,
            authorization=WorkspaceAuthorizationContext(
                principal=Principal(subject=work_item.requested_by_user.external_id),
                workspace_id=work_item.job.workspace_id,
                workspace_role=WorkspaceRole.EDITOR,
            ),
            role=role,
            inputs={
                "artifact_type": artifact_type,
                "operation": input_data["operation"],
                "briefing": input_data["briefing"],
                "brand_context": {
                    "name": brand.name,
                    "description": brand.description or "",
                    "brand_voice": brand.brand_voice or "",
                },
                "source_content_id": input_data.get("source_content_id"),
                "source_content": input_data.get("source_content"),
                "source_text": work_item.parameters.get("source_text"),
                "preserve_source_facts_and_concept": input_data["operation"] != "CREATE",
            },
            prompt_template_id=(
                "agent.writer.copy.v1" if artifact_type == "COPY" else "agent.writer.caption.v1"
            ),
            prompt_template_version="3.0",
            schema_version="1.0",
            output_contract=artifact_type,
        )
        result = create_specialist_executor(settings).execute(execution)
        if artifact_type == "COPY":
            text = WriterCopyOutput.model_validate(result.output).copy_text
        else:
            text = WriterCaptionOutput.model_validate(result.output).caption
        with SqlAlchemyUnitOfWork() as unit_of_work:
            unit_of_work.contents.append_text_version(
                user_id=work_item.requested_by_user.id,
                content_id=work_item.job.content_id,
                generation_id=work_item.job.generation_id,
                artifact_type=artifact_type,
                text=text,
                metadata={
                    "provider": result.provider,
                    "model": result.model,
                    "prompt_template_id": result.prompt_template_id,
                    "prompt_template_version": result.prompt_template_version,
                    "prompt_input_hash": result.input_hash,
                    "output_hash": result.output_hash,
                    "schema_name": result.schema_name,
                    "schema_version": result.schema_version,
                },
            )
            unit_of_work.generation.image_jobs.complete_text_job(job_id)
            unit_of_work.commit()
    except ProviderNotConfiguredError:
        logger.exception("independent_text_generation_failed", extra={"job_id": str(job_id)})
        with SqlAlchemyUnitOfWork() as unit_of_work:
            unit_of_work.generation.image_jobs.fail_job(
                job_id,
                failure_code="PROVIDER_AUTHENTICATION_FAILED",
                failure_message="Text Generation provider is not configured",
            )
            unit_of_work.commit()
    except AgentKickoffError as error:
        retryable = error.code in {
            AgentKickoffErrorCode.PROVIDER_FAILURE,
            AgentKickoffErrorCode.PROVIDER_UNAVAILABLE,
        }
        if retryable and work_item.job.attempt_count < work_item.job.max_attempts:
            raise
        logger.exception("independent_text_generation_failed", extra={"job_id": str(job_id)})
        with SqlAlchemyUnitOfWork() as unit_of_work:
            unit_of_work.generation.image_jobs.fail_job(
                job_id,
                failure_code=error.code.value,
                failure_message="Text Generation failed",
            )
            unit_of_work.commit()
    except Exception:
        logger.exception("independent_text_generation_failed", extra={"job_id": str(job_id)})
        with SqlAlchemyUnitOfWork() as unit_of_work:
            unit_of_work.generation.image_jobs.fail_job(
                job_id,
                failure_code="TEXT_GENERATION_FAILED",
                failure_message="Text Generation failed",
            )
            unit_of_work.commit()
