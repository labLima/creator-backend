import pytest

from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.prompts.agents import build_agent_prompt
from creator.services.agents.contracts import AGENT_CONTRACTS
from creator.services.agents.specs import CREATIVE_SPECIALTIES, SPECIALIST_SPECS


def test_image_workflow_has_a_versioned_spec_for_every_specialist() -> None:
    roles = set(AgentWorkflowStepRole) - {AgentWorkflowStepRole.DELIVERY}
    assert set(SPECIALIST_SPECS) == roles
    for role, spec in SPECIALIST_SPECS.items():
        assert spec.role == role
        assert spec.version and spec.goal and spec.instructions and spec.inputs and spec.output
    for role, contract in AGENT_CONTRACTS.items():
        assert SPECIALIST_SPECS[role].output == contract.output_model.__name__
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.ARTIST].permitted_tools == ("image_generation",)
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.REVIEWER].permitted_tools == ("image_review",)


def test_specialties_match_documented_parent_agents() -> None:
    assert [item.id for item in CREATIVE_SPECIALTIES] == [f"SUB-{i:02}" for i in range(1, 12)]
    assert [item.parent for item in CREATIVE_SPECIALTIES] == (
        ["AGT-01"] * 4 + ["AGT-02"] * 3 + ["AGT-03"] + ["AGT-04"] * 3
    )


def test_prompt_v2_uses_role_spec_and_v1_remains_reproducible() -> None:
    current = build_agent_prompt("BUSINESS", {"campaign": "Launch"})
    previous = build_agent_prompt("BUSINESS", {"campaign": "Launch"}, version="1.0")
    assert current.template_id == "agent.business.v2"
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.BUSINESS].instructions in current.text
    assert "Never invent facts" not in previous.text
    assert previous.template_id == "agent.business.v1"
    assert current.input_hash != previous.input_hash


@pytest.mark.parametrize("role", list(SPECIALIST_SPECS))
def test_v2_prompt_uses_each_specialist_instructions(role: AgentWorkflowStepRole) -> None:
    rendered = build_agent_prompt(role.value, {"input": "example"})
    assert SPECIALIST_SPECS[role].instructions in rendered.text
    assert "untrusted data" in rendered.text
