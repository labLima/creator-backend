from __future__ import annotations

from uuid import UUID

import pytest

from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.domain.auth import Principal, WorkspaceRole
from creator.services.agents.contracts import (
    AgentExecutionContext,
    BusinessOutput,
    KickoffRequest,
    WorkspaceAuthorizationContext,
)
from creator.services.agents.crewai_adapter import CrewAIMultiAgentOrchestrator
from creator.services.agents.errors import AgentKickoffError, AgentKickoffErrorCode
from creator.services.ai.factory import UnconfiguredLLMProvider

WORKSPACE_ID = UUID("10000000-0000-0000-0000-000000000001")


class FakeProvider:
    provider_name = "fake"
    model = "fake-model"

    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[str] = []

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        self.calls.append(prompt)
        return self.output


def request(
    *,
    workspace_id: UUID = WORKSPACE_ID,
    role: AgentWorkflowStepRole = AgentWorkflowStepRole.BUSINESS,
    workspace_role: WorkspaceRole = WorkspaceRole.EDITOR,
    goal: str = "Summarize the brand",
    inputs: dict[str, object] | None = None,
) -> KickoffRequest:
    return KickoffRequest(
        authorization=WorkspaceAuthorizationContext(
            principal=Principal(subject="principal"),
            workspace_id=workspace_id,
            workspace_role=workspace_role,
        ),
        role=role,
        goal=goal,
        inputs=inputs or {"campaign": "Launch"},
    )


VALID_BUSINESS = (
    '{"brand_summary":"Brand","voice":"Clear",'
    '"visual_direction":"Bright","constraints":[],"knowledge_sources":[]}'
)


def test_kickoff_returns_typed_output_and_audit_metadata() -> None:
    provider = FakeProvider(VALID_BUSINESS)
    result = CrewAIMultiAgentOrchestrator(provider).kickoff(request())

    assert isinstance(result.output, BusinessOutput)
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.prompt_template_id == "agent.business.v1"
    assert result.prompt_template_version == "1.0"
    assert len(result.input_hash) == 64
    assert len(result.output_hash) == 64
    assert result.metadata["prompt_input_hash"] == result.input_hash
    assert '"goal": "Summarize the brand"' in result.prompt


@pytest.mark.parametrize(
    ("output", "code"),
    [
        ("not json", AgentKickoffErrorCode.OUTPUT_MALFORMED),
        (
            VALID_BUSINESS[:-1] + ',"unexpected":"field"}',
            AgentKickoffErrorCode.OUTPUT_SCHEMA_INVALID,
        ),
        ('{"brand_summary":""}', AgentKickoffErrorCode.OUTPUT_SCHEMA_INVALID),
    ],
)
def test_kickoff_rejects_untrusted_provider_output(
    output: str, code: AgentKickoffErrorCode
) -> None:
    provider = FakeProvider(output)

    with pytest.raises(AgentKickoffError) as raised:
        CrewAIMultiAgentOrchestrator(provider).kickoff(request())

    assert raised.value.code == code


def test_kickoff_maps_provider_failures_to_bounded_error() -> None:
    class FailingProvider(FakeProvider):
        def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
            raise RuntimeError("provider secret should not escape")

    with pytest.raises(AgentKickoffError) as raised:
        CrewAIMultiAgentOrchestrator(FailingProvider(VALID_BUSINESS)).kickoff(request())

    assert raised.value.code == AgentKickoffErrorCode.PROVIDER_FAILURE
    assert str(raised.value) == "The agent provider failed"


def test_kickoff_maps_unconfigured_provider_to_bounded_error() -> None:
    with pytest.raises(AgentKickoffError) as raised:
        CrewAIMultiAgentOrchestrator(UnconfiguredLLMProvider()).kickoff(request())

    assert raised.value.code == AgentKickoffErrorCode.PROVIDER_UNAVAILABLE


def test_kickoff_rejects_unauthorized_workspace_before_provider_call() -> None:
    provider = FakeProvider(VALID_BUSINESS)

    with pytest.raises(AgentKickoffError) as raised:
        CrewAIMultiAgentOrchestrator(provider).kickoff(request(workspace_role=WorkspaceRole.VIEWER))

    assert raised.value.code == AgentKickoffErrorCode.WORKSPACE_UNAUTHORIZED
    assert provider.calls == []


def test_execute_rejects_mismatched_workspace_authorization() -> None:
    provider = FakeProvider(VALID_BUSINESS)
    orchestrator = CrewAIMultiAgentOrchestrator(provider)

    with pytest.raises(AgentKickoffError) as raised:
        orchestrator.execute(
            AgentExecutionContext(
                workspace_id=WORKSPACE_ID,
                brand_id=None,
                authorization=WorkspaceAuthorizationContext(
                    principal=Principal(subject="principal"),
                    workspace_id=UUID("10000000-0000-0000-0000-000000000002"),
                    workspace_role=WorkspaceRole.EDITOR,
                ),
                role=AgentWorkflowStepRole.BUSINESS,
                inputs={"goal": "Goal"},
                prompt_template_id="agent.business.v1",
                prompt_template_version="1.0",
                schema_version="1.0",
            )
        )

    assert raised.value.code == AgentKickoffErrorCode.WORKSPACE_UNAUTHORIZED
    assert provider.calls == []


def test_kickoff_hash_is_deterministic_and_workspace_scoped() -> None:
    provider = FakeProvider(VALID_BUSINESS)
    orchestrator = CrewAIMultiAgentOrchestrator(provider)

    first = orchestrator.kickoff(request(inputs={"b": "two", "a": "one"}))
    second = orchestrator.kickoff(request(inputs={"a": "one", "b": "two"}))
    other_workspace = orchestrator.kickoff(
        request(workspace_id=UUID("10000000-0000-0000-0000-000000000002"))
    )

    assert first.input_hash == second.input_hash
    assert first.input_hash != other_workspace.input_hash


def test_kickoff_rejects_roles_without_a_server_owned_text_contract() -> None:
    provider = FakeProvider(VALID_BUSINESS)

    with pytest.raises(AgentKickoffError) as raised:
        CrewAIMultiAgentOrchestrator(provider).kickoff(request(role=AgentWorkflowStepRole.ARTIST))

    assert raised.value.code == AgentKickoffErrorCode.ROLE_UNSUPPORTED
    assert provider.calls == []
