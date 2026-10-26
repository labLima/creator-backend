from __future__ import annotations

from uuid import UUID

from creator.prompts.base import PromptValidationError, normalize_json_object
from creator.services.agents.contracts import (
    AgentExecutionContext,
    AgentExecutionResult,
    KickoffRequest,
    contract_for_role,
)
from creator.services.agents.errors import AgentKickoffError, AgentKickoffErrorCode
from creator.services.agents.runner import StructuredAgentRunner
from creator.services.ai.provider import LLMProvider


class CrewAIMultiAgentOrchestrator:
    """CrewAI-compatible adapter boundary.

    The workflow engine owns sequencing and persistence. This adapter owns the
    provider-facing specialist execution, so replacing it with a CrewAI Flow or
    another orchestration runtime does not alter application contracts.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._runner = StructuredAgentRunner(provider)
        self._provider = provider

    def kickoff(self, request: KickoffRequest) -> AgentExecutionResult:
        contract = contract_for_role(request.role)
        if not isinstance(request.goal, str) or not request.goal.strip():
            raise AgentKickoffError(
                AgentKickoffErrorCode.INPUT_INVALID,
                "Agent goal is required",
            )
        if len(request.goal.strip()) > 4_000:
            raise AgentKickoffError(
                AgentKickoffErrorCode.INPUT_INVALID,
                "Agent goal exceeds the permitted length",
            )
        try:
            normalized_inputs = normalize_json_object(request.inputs)
        except PromptValidationError as error:
            raise AgentKickoffError(
                AgentKickoffErrorCode.INPUT_INVALID,
                "Agent inputs must be JSON-compatible",
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
        result = self._runner.run(context, contract.output_model)
        # CrewAI/provider responses are untrusted data; enforce the application contract here.
        validated = contract.output_model.model_validate(result.output.model_dump(mode="json"))
        return AgentExecutionResult(
            output=validated,
            prompt=result.prompt,
            prompt_template_id=result.prompt_template_id,
            prompt_template_version=result.prompt_template_version,
            input_hash=result.input_hash,
            output_hash=result.output_hash,
            schema_name=result.schema_name,
            schema_version=result.schema_version,
            provider=result.provider,
            model=result.model,
            metadata={
                **result.metadata,
                "runtime": "crewai-adapter",
                "execution": "deterministic",
            },
        )
