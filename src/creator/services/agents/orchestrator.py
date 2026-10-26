from typing import Protocol

from creator.services.agents.contracts import (
    AgentExecutionContext,
    AgentExecutionResult,
    KickoffRequest,
)


class MultiAgentOrchestrator(Protocol):
    def kickoff(self, request: KickoffRequest) -> AgentExecutionResult:
        """Run a validated multi-agent workflow for a Workspace-scoped goal."""

    def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """Execute one validated specialist role behind the provider boundary."""
