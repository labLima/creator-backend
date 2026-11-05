from creator.config import Settings
from creator.services.agents.contracts import (
    AgentExecutionContext,
    AgentExecutionResult,
    KickoffRequest,
    contract_for_execution,
)
from creator.services.agents.orchestrator import MultiAgentOrchestrator, SpecialistExecutor
from creator.services.agents.runner import StructuredAgentRunner
from creator.services.ai.factory import create_llm_provider
from creator.services.ai.provider import ProviderNotConfiguredError


class AgentOrchestratorNotConfiguredError(RuntimeError):
    """Raised when a multi-agent orchestrator cannot safely be used."""


class UnconfiguredMultiAgentOrchestrator:
    def kickoff(self, request: KickoffRequest) -> AgentExecutionResult:
        raise AgentOrchestratorNotConfiguredError("Multi-agent orchestrator is not configured")

    def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        raise AgentOrchestratorNotConfiguredError("Multi-agent orchestrator is not configured")


def create_multi_agent_orchestrator(settings: Settings) -> MultiAgentOrchestrator:
    if settings.crewai_enabled:
        # Imported lazily so the API and worker start without CrewAI when the
        # feature is disabled and the optional dependency is not installed.
        from creator.services.agents.crewai_adapter import CrewAIMultiAgentOrchestrator

        return CrewAIMultiAgentOrchestrator(create_llm_provider(settings))
    return UnconfiguredMultiAgentOrchestrator()


class UnconfiguredSpecialistExecutor:
    def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        raise ProviderNotConfiguredError("Specialist provider is not configured")


class StructuredSpecialistExecutor:
    def __init__(self, runner: StructuredAgentRunner) -> None:
        self._runner = runner

    def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        contract = contract_for_execution(context)
        return self._runner.run(context, contract.output_model)


def create_specialist_executor(settings: Settings) -> SpecialistExecutor:
    if settings.crewai_enabled:
        return create_multi_agent_orchestrator(settings)
    if settings.openai_api_key:
        return StructuredSpecialistExecutor(StructuredAgentRunner(create_llm_provider(settings)))
    return UnconfiguredSpecialistExecutor()
