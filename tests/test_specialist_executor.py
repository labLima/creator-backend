from __future__ import annotations

from uuid import UUID

import pytest

from creator.config import Settings
from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.domain.auth import Principal, WorkspaceRole
from creator.services.agents.contracts import (
    AgentExecutionContext,
    BusinessOutput,
    WorkspaceAuthorizationContext,
)
from creator.services.agents.factory import (
    StructuredSpecialistExecutor,
    create_specialist_executor,
)
from creator.services.agents.runner import StructuredAgentRunner
from creator.services.ai.provider import LLMAuthenticationError, ProviderNotConfiguredError

WORKSPACE_ID = UUID("10000000-0000-0000-0000-000000000001")


class AuthenticationFailingLLM:
    provider_name = "fake"
    model = "fake-model"

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        raise LLMAuthenticationError("invalid credentials")


def context() -> AgentExecutionContext:
    return AgentExecutionContext(
        workspace_id=WORKSPACE_ID,
        brand_id=None,
        authorization=WorkspaceAuthorizationContext(
            principal=Principal(subject="principal"),
            workspace_id=WORKSPACE_ID,
            workspace_role=WorkspaceRole.EDITOR,
        ),
        role=AgentWorkflowStepRole.BUSINESS,
        inputs={"campaign": "Launch"},
        prompt_template_id="agent.business.v1",
        prompt_template_version="1.0",
        schema_version="1.0",
    )


def test_specialist_executor_uses_structured_runner_with_openai_key() -> None:
    executor = create_specialist_executor(
        Settings(_env_file=None, openai_api_key="test-key", crewai_enabled=False)
    )

    assert isinstance(executor, StructuredSpecialistExecutor)


def test_specialist_executor_honours_crewai_flag() -> None:
    executor = create_specialist_executor(Settings(_env_file=None, crewai_enabled=True))

    assert type(executor).__name__ == "CrewAIMultiAgentOrchestrator"


def test_structured_runner_maps_authentication_failure_to_provider_configuration() -> None:
    runner = StructuredAgentRunner(AuthenticationFailingLLM())

    with pytest.raises(ProviderNotConfiguredError):
        runner.run(context(), BusinessOutput)
