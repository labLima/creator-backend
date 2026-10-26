from creator.config import Settings
from creator.services.agents.contracts import (
    AgentExecutionContext,
    AgentExecutionResult,
    KickoffRequest,
)
from creator.services.agents.crewai_adapter import CrewAIMultiAgentOrchestrator
from creator.services.agents.orchestrator import MultiAgentOrchestrator
from creator.services.ai.factory import create_llm_provider


class AgentOrchestratorNotConfiguredError(RuntimeError):
    """Raised when a multi-agent orchestrator cannot safely be used."""


class UnconfiguredMultiAgentOrchestrator:
    def kickoff(self, request: KickoffRequest) -> AgentExecutionResult:
        raise AgentOrchestratorNotConfiguredError("Multi-agent orchestrator is not configured")

    def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        raise AgentOrchestratorNotConfiguredError("Multi-agent orchestrator is not configured")


def create_multi_agent_orchestrator(settings: Settings) -> MultiAgentOrchestrator:
    if settings.crewai_enabled:
        return CrewAIMultiAgentOrchestrator(create_llm_provider(settings))
    return UnconfiguredMultiAgentOrchestrator()
