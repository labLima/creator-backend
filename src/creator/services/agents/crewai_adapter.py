from __future__ import annotations

import json
import os
from typing import Any, cast
from uuid import UUID

from pydantic import PrivateAttr, ValidationError

from creator.prompts.agents import build_agent_prompt, json_output_instructions
from creator.prompts.base import PromptValidationError, normalize_json_object
from creator.services.agents.contracts import (
    AgentExecutionContext,
    AgentExecutionResult,
    KickoffRequest,
    contract_for_role,
)
from creator.services.agents.design_specs import AGENT_DESIGNS
from creator.services.agents.errors import AgentKickoffError, AgentKickoffErrorCode
from creator.services.agents.runner import (
    _stable_hash,
    _strip_json_fence,
    _validate_execution_context,
)
from creator.services.ai.provider import LLMProvider, ProviderNotConfiguredError

# CrewAI tracing can persist or offer to upload Workspace prompts. Creator's
# own audit record is the authorized trace for these executions.
os.environ["CREWAI_TRACING_ENABLED"] = "false"

# CrewAI imports python-dotenv and otherwise loads the working directory's
# .env into the process, bypassing Creator's explicit Settings handling.
_dotenv_setting = os.environ.get("PYTHON_DOTENV_DISABLED")
os.environ["PYTHON_DOTENV_DISABLED"] = "true"
try:
    from crewai import Agent, BaseLLM
    from crewai.events.utils.console_formatter import (
        set_suppress_console_output,
        should_suppress_console_output,
    )
finally:
    if _dotenv_setting is None:
        os.environ.pop("PYTHON_DOTENV_DISABLED", None)
    else:
        os.environ["PYTHON_DOTENV_DISABLED"] = _dotenv_setting


class _CreatorLLM(BaseLLM):
    """Bridge CrewAI messages to Creator's provider without exposing vendor SDKs."""

    _creator_provider: LLMProvider = PrivateAttr()
    _prompt: str = PrivateAttr(default="")
    _error: Exception | None = PrivateAttr(default=None)
    _response: object = PrivateAttr(default=None)

    def __init__(self, provider: LLMProvider) -> None:
        super().__init__(
            model=getattr(provider, "model", None) or "creator-provider", temperature=0.2
        )
        self._creator_provider = provider

    def call(self, messages: Any, *args: Any, **kwargs: Any) -> str:
        # The provider interface accepts a string, so preserve the complete ordered
        # CrewAI messages as JSON. This exact string is retained for the audit record.
        self._prompt = (
            messages
            if isinstance(messages, str)
            else json.dumps(messages, ensure_ascii=False, sort_keys=True)
        )
        try:
            response = self._creator_provider.generate_text(self._prompt, temperature=0.2)
        except Exception as error:
            self._error = error
            raise RuntimeError("The agent provider failed") from None
        self._response = response
        # No tools are enabled: the provider's complete response is the final answer.
        # This also lets Creator, rather than CrewAI's parser, classify invalid JSON.
        return "Final Answer: " + (response if isinstance(response, str) else "")


class CrewAIMultiAgentOrchestrator:
    """Run one specialist while Creator owns workflow sequencing and state."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def kickoff(self, request: KickoffRequest) -> AgentExecutionResult:
        contract = contract_for_role(request.role)
        if not isinstance(request.goal, str) or not request.goal.strip():
            raise AgentKickoffError(AgentKickoffErrorCode.INPUT_INVALID, "Agent goal is required")
        if len(request.goal.strip()) > 4_000:
            raise AgentKickoffError(
                AgentKickoffErrorCode.INPUT_INVALID, "Agent goal exceeds the permitted length"
            )
        try:
            normalized_inputs = normalize_json_object(request.inputs)
        except PromptValidationError as error:
            raise AgentKickoffError(
                AgentKickoffErrorCode.INPUT_INVALID, "Agent inputs must be JSON-compatible"
            ) from error
        return self.execute(
            AgentExecutionContext(
                workspace_id=request.authorization.workspace_id,
                brand_id=None,
                authorization=request.authorization,
                role=request.role,
                inputs={"goal": request.goal.strip(), "inputs": normalized_inputs},
                prompt_template_id=contract.prompt_template_id,
                prompt_template_version=contract.prompt_template_version,
                schema_version=contract.schema_version,
            )
        )

    def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        if not isinstance(context.workspace_id, UUID) or (
            context.brand_id is not None and not isinstance(context.brand_id, UUID)
        ):
            raise AgentKickoffError(
                AgentKickoffErrorCode.WORKSPACE_UNAUTHORIZED,
                "Specialist execution requires authorized Workspace and Brand scope",
            )
        _validate_execution_context(context)
        contract = contract_for_role(context.role)
        if (
            context.prompt_template_id != contract.prompt_template_id
            or context.prompt_template_version != contract.prompt_template_version
            or context.schema_version != contract.schema_version
        ):
            raise AgentKickoffError(
                AgentKickoffErrorCode.INPUT_INVALID,
                "Agent prompt contract does not match the server-owned role contract",
            )
        rendered = build_agent_prompt(
            context.role.value,
            {
                **dict(context.inputs),
                "output_instructions": json_output_instructions(contract.output_model.__name__),
            },
            template_id=context.prompt_template_id,
            version=context.prompt_template_version,
            prompt_context={"workspace_id": str(context.workspace_id)},
        )
        llm = _CreatorLLM(self._provider)
        design = AGENT_DESIGNS[context.role]
        try:
            agent = Agent(
                role=design.title,
                goal=design.goal,
                backstory=design.backstory,
                llm=llm,
                tools=[],
                allow_delegation=False,
                verbose=False,
                max_retry_limit=0,
            )
            previous_suppression = should_suppress_console_output()
            set_suppress_console_output(True)
            try:
                agent.kickoff(rendered.text)
            finally:
                set_suppress_console_output(previous_suppression)
            raw = llm._response
        except Exception as error:
            if isinstance(llm._error, ProviderNotConfiguredError):
                raise AgentKickoffError(
                    AgentKickoffErrorCode.PROVIDER_UNAVAILABLE, "The agent provider is unavailable"
                ) from error
            raise AgentKickoffError(
                AgentKickoffErrorCode.PROVIDER_FAILURE, "The agent provider failed"
            ) from error
        try:
            payload = json.loads(_strip_json_fence(cast(str, raw)))
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
            output = contract.output_model.model_validate(payload)
        except ValidationError as error:
            raise AgentKickoffError(
                AgentKickoffErrorCode.OUTPUT_SCHEMA_INVALID,
                "The agent provider returned output outside the contract",
            ) from error
        return AgentExecutionResult(
            output=output,
            prompt=llm._prompt,
            prompt_template_id=rendered.template_id,
            prompt_template_version=rendered.version,
            input_hash=rendered.input_hash,
            output_hash=_stable_hash(output.model_dump(mode="json")),
            schema_name=contract.output_model.__name__,
            schema_version=context.schema_version,
            provider=getattr(self._provider, "provider_name", self._provider.__class__.__name__),
            model=getattr(self._provider, "model", None),
            metadata={
                "prompt_template_id": rendered.template_id,
                "prompt_template_version": rendered.version,
                "prompt_input_hash": rendered.input_hash,
                "runtime": "crewai",
                "execution": "agent-kickoff",
            },
        )
