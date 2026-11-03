import hashlib

import pytest

from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.prompts.agents import build_agent_prompt
from creator.services.agents.contracts import AGENT_CONTRACTS
from creator.services.agents.design_specs import AGENT_DESIGNS, SPECIALTY_DESIGNS
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
    current = build_agent_prompt("BUSINESS", {"campaign": "Launch"}, version="2.0")
    previous = build_agent_prompt("BUSINESS", {"campaign": "Launch"}, version="1.0")
    assert current.template_id == "agent.business.v2"
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.BUSINESS].instructions in current.text
    assert "Never invent facts" not in previous.text
    assert previous.template_id == "agent.business.v1"
    assert current.input_hash != previous.input_hash
    assert hashlib.sha256(current.text.encode()).hexdigest() == (
        "54b14d955e3f0e3e8ff8c69f1cd60bbd1b3792fecbadb7e6f190811e6c12f827"
    )


@pytest.mark.parametrize("role", list(SPECIALIST_SPECS))
def test_v2_prompt_uses_each_specialist_instructions(role: AgentWorkflowStepRole) -> None:
    rendered = build_agent_prompt(role.value, {"input": "example"}, version="2.0")
    assert SPECIALIST_SPECS[role].instructions in rendered.text
    assert "untrusted data" in rendered.text


def test_all_specialties_have_explicit_designs() -> None:
    assert {item.id for item in SPECIALTY_DESIGNS} == {item.id for item in CREATIVE_SPECIALTIES}
    assert len(SPECIALTY_DESIGNS) == len(CREATIVE_SPECIALTIES)
    for item in SPECIALTY_DESIGNS:
        assert item.title and item.goal and item.backstory and item.task and item.expected_output


@pytest.mark.parametrize("role", list(SPECIALIST_SPECS))
def test_v3_prompt_separates_identity_task_and_expected_output(role: AgentWorkflowStepRole) -> None:
    design = AGENT_DESIGNS[role]
    rendered = build_agent_prompt(role.value, {"input": "example"})
    assert rendered.template_id == f"agent.{role.value.lower()}.v3"
    assert all(
        value in rendered.text
        for value in (
            design.title,
            design.goal,
            design.backstory,
            design.task,
            design.expected_output,
        )
    )
    assert "untrusted data" in rendered.text
