from __future__ import annotations

import json
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

from creator.domain.auth import Principal
from creator.prompts.agents import build_agent_prompt, json_output_instructions
from creator.services.agents.contracts import AgentExecutionContext, AgentExecutionResult
from creator.services.agents.errors import AgentKickoffError, AgentKickoffErrorCode
from creator.services.ai.provider import LLMProvider, ProviderNotConfiguredError

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class StructuredAgentRunner:
    """Provider-neutral runner for specialist contracts.

    CrewAI adapters can replace this runner without changing the workflow state
    machine or persistence boundary.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def run(
        self, context: AgentExecutionContext, output_model: type[OutputModel]
    ) -> AgentExecutionResult:
        _validate_execution_context(context)
        rendered = build_agent_prompt(
            context.role.value,
            {
                **dict(context.inputs),
                "output_instructions": json_output_instructions(output_model.__name__),
            },
            template_id=context.prompt_template_id,
            version=context.prompt_template_version,
            prompt_context={"workspace_id": str(context.workspace_id)},
        )
        try:
            raw = self._provider.generate_text(rendered.text, temperature=0.2)
        except ProviderNotConfiguredError as error:
            raise AgentKickoffError(
                AgentKickoffErrorCode.PROVIDER_UNAVAILABLE,
                "The agent provider is unavailable",
            ) from error
        except Exception as error:
            raise AgentKickoffError(
                AgentKickoffErrorCode.PROVIDER_FAILURE,
                "The agent provider failed",
            ) from error

        try:
            payload = json.loads(_strip_json_fence(raw))
        except (TypeError, json.JSONDecodeError) as error:
            raise AgentKickoffError(
                AgentKickoffErrorCode.OUTPUT_MALFORMED,
                "The agent provider returned malformed JSON",
            ) from error
        if not isinstance(payload, dict):
            raise AgentKickoffError(
                AgentKickoffErrorCode.OUTPUT_MALFORMED,
                "The agent provider returned a non-object JSON value",
            )
        try:
            output = output_model.model_validate(payload)
        except ValidationError as error:
            raise AgentKickoffError(
                AgentKickoffErrorCode.OUTPUT_SCHEMA_INVALID,
                "The agent provider returned output outside the contract",
            ) from error

        output_payload = output.model_dump(mode="json")
        return AgentExecutionResult(
            output=output,
            prompt=rendered.text,
            prompt_template_id=rendered.template_id,
            prompt_template_version=rendered.version,
            input_hash=rendered.input_hash,
            output_hash=_stable_hash(output_payload),
            schema_name=output_model.__name__,
            schema_version=context.schema_version,
            provider=getattr(self._provider, "provider_name", self._provider.__class__.__name__),
            model=getattr(self._provider, "model", None),
            metadata={
                "prompt_template_id": rendered.template_id,
                "prompt_template_version": rendered.version,
                "prompt_input_hash": rendered.input_hash,
            },
        )


def _strip_json_fence(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("Provider output must be text")
    normalized = text.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[-1]
        if normalized.endswith("```"):
            normalized = normalized[:-3]
    return normalized.strip()


def _validate_execution_context(context: AgentExecutionContext) -> None:
    authorization = context.authorization
    principal = getattr(authorization, "principal", None)
    workspace_id = getattr(authorization, "workspace_id", None)
    workspace_role = getattr(authorization, "workspace_role", None)
    role_value = getattr(workspace_role, "value", workspace_role)
    if workspace_id != context.workspace_id or not isinstance(context.workspace_id, UUID):
        raise AgentKickoffError(
            AgentKickoffErrorCode.WORKSPACE_UNAUTHORIZED,
            "Workspace authorization does not match execution scope",
        )
    if not isinstance(principal, Principal) or not principal.subject.strip():
        raise AgentKickoffError(
            AgentKickoffErrorCode.WORKSPACE_UNAUTHORIZED,
            "A Principal is required for agent execution",
        )
    if role_value not in {"owner", "admin", "editor"}:
        raise AgentKickoffError(
            AgentKickoffErrorCode.WORKSPACE_UNAUTHORIZED,
            "Workspace Role is not authorized for agent execution",
        )


def _stable_hash(value: object) -> str:
    import hashlib

    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
