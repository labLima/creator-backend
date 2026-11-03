import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.prompts.agent_designs import (
    AGENT_DESIGN_VERSION,
    AGENT_DESIGNS,
)
from creator.prompts.agents import AGENT_PROMPT_VERSION, build_agent_prompt
from creator.prompts.specialist_specs import SPECIALIST_SPEC_VERSION, SPECIALIST_SPECS
from creator.services.agents.contracts import AGENT_CONTRACTS, contract_for_role
from creator.services.agents.errors import AgentKickoffError, AgentKickoffErrorCode

# Golden hashes for the prompt v3 text. Changing any rendered text requires a prompt version
# bump and a corresponding update to these hashes.
GOLDEN_V3_HASHES = {
    AgentWorkflowStepRole.BUSINESS: (
        "a965e9a1e40c2fd62bcc0c14bdc96289feb643dc0ecd78bd43bb805434ad5a3c"
    ),
    AgentWorkflowStepRole.PLANNER: (
        "e5e90af11646c5f545ebb741214257c37576a1c2ec1c776ccf0ae145f6ef4c20"
    ),
    AgentWorkflowStepRole.WRITER: (
        "bb20c7d209f8775572746fa063b2accd3d3bdc9100cbff984bbd75fea9300917"
    ),
    AgentWorkflowStepRole.ARTIST: (
        "b5d91d1ea41568006d490276d238d1f01b6045e50c38011d6ee616cf513f64fc"
    ),
    AgentWorkflowStepRole.REVIEWER: (
        "9c61f145532b2904da9ea357072b5a9fb86f627ba848935b5f07a87531ba9a73"
    ),
}

# Golden hashes for the prompt v2 text, pinned on specialist spec 2.0 alone.
GOLDEN_V2_HASHES = {
    AgentWorkflowStepRole.BUSINESS: (
        "e4ce0060fae14f3bc8eac4ab5e390a2b1466ed66e79ab993582a3a06e565431d"
    ),
    AgentWorkflowStepRole.PLANNER: (
        "1321f06a73b67b78ed18771182f0674f9050b69790aa8c8d5ce9e98ecd9dc7b6"
    ),
    AgentWorkflowStepRole.WRITER: (
        "90cadfae947e3547a0e31cd28a5b905141f8af2d6e4369787a86dc0735030835"
    ),
    AgentWorkflowStepRole.ARTIST: (
        "adcc74217b57cf8e3ac6d8806fb1c5f1ec84e34c3ab44a3841792175da1a7e16"
    ),
    AgentWorkflowStepRole.REVIEWER: (
        "88da9a8e08e55b170a66cc427e5cf6c327f8c3b6c051a453cbf626ff702eba1a"
    ),
}


def test_image_workflow_has_a_versioned_spec_for_every_specialist() -> None:
    roles = set(AgentWorkflowStepRole) - {AgentWorkflowStepRole.DELIVERY}
    assert set(SPECIALIST_SPECS) == roles
    for role, spec in SPECIALIST_SPECS.items():
        assert spec.role == role
        assert spec.spec_version and spec.goal and spec.instructions and spec.inputs and spec.output
    for role, contract in AGENT_CONTRACTS.items():
        assert SPECIALIST_SPECS[role].output == contract.output_model.__name__
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.ARTIST].permitted_tools == ("image_generation",)
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.REVIEWER].permitted_tools == ("image_review",)


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


def test_prompt_version_composition_is_explicit() -> None:
    assert AGENT_PROMPT_VERSION == "3.0"
    assert AGENT_DESIGN_VERSION == "3.0"
    assert SPECIALIST_SPEC_VERSION == "2.0"
    for role in SPECIALIST_SPECS:
        assert SPECIALIST_SPECS[role].spec_version == "2.0"
        assert AGENT_DESIGNS[role].design_version == "3.0"
    for role in AGENT_CONTRACTS:
        assert AGENT_CONTRACTS[role].prompt_template_version == "3.0"
        assert AGENT_CONTRACTS[role].prompt_template_id.endswith(".v3")


@pytest.mark.parametrize("role", list(SPECIALIST_SPECS))
def test_prompt_v3_matches_golden_hashes(role: AgentWorkflowStepRole) -> None:
    rendered = build_agent_prompt(role.value, {"input": "example"})
    assert hashlib.sha256(rendered.text.encode()).hexdigest() == GOLDEN_V3_HASHES[role]


@pytest.mark.parametrize("role", list(SPECIALIST_SPECS))
def test_prompt_v2_matches_golden_hashes(role: AgentWorkflowStepRole) -> None:
    rendered = build_agent_prompt(role.value, {"input": "example"}, version="2.0")
    assert hashlib.sha256(rendered.text.encode()).hexdigest() == GOLDEN_V2_HASHES[role]


def test_v3_rejects_design_version_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    design = replace(AGENT_DESIGNS[AgentWorkflowStepRole.BUSINESS], design_version="9.0")
    monkeypatch.setitem(AGENT_DESIGNS, AgentWorkflowStepRole.BUSINESS, design)

    with pytest.raises(ValueError):
        build_agent_prompt("BUSINESS", {"input": "example"})


def test_v3_rejects_specialist_spec_version_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = replace(SPECIALIST_SPECS[AgentWorkflowStepRole.BUSINESS], spec_version="9.0")
    monkeypatch.setitem(SPECIALIST_SPECS, AgentWorkflowStepRole.BUSINESS, spec)

    with pytest.raises(ValueError):
        build_agent_prompt("BUSINESS", {"input": "example"})


def test_artist_and_reviewer_are_provider_boundaries_not_kickoff_contracts() -> None:
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.ARTIST].output == "ImageGenerationResult"
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.REVIEWER].output == "ReviewOutput"
    for role in (AgentWorkflowStepRole.ARTIST, AgentWorkflowStepRole.REVIEWER):
        assert role not in AGENT_CONTRACTS
        with pytest.raises(AgentKickoffError) as raised:
            contract_for_role(role)
        assert raised.value.code == AgentKickoffErrorCode.ROLE_UNSUPPORTED


@pytest.mark.parametrize("role", list(SPECIALIST_SPECS))
def test_prompt_v2_does_not_include_v3_design_fields(role: AgentWorkflowStepRole) -> None:
    design = AGENT_DESIGNS[role]
    rendered = build_agent_prompt(role.value, {"input": "example"}, version="2.0")
    assert design.title not in rendered.text
    assert design.task not in rendered.text
    assert design.backstory not in rendered.text


def test_documented_subagents_are_present() -> None:
    subagents = Path(__file__).resolve().parents[1] / "docs" / "agents" / "subagents"
    for index in range(1, 12):
        assert (subagents / f"SUB-{index:02}.md").is_file()
