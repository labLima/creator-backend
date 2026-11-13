import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.prompts.agent_designs import (
    AGENT_DESIGN_VERSION,
    AGENT_DESIGNS,
)
from creator.prompts.agents import AGENT_PROMPT_VERSION, build_agent_prompt, build_reviewer_prompt
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


def test_independent_artist_v4_adds_art_direction_without_changing_v3() -> None:
    inputs = {"visual_direction": "Photograph a cup of coffee", "briefing": "Use exact copy"}
    previous = build_agent_prompt("ARTIST", inputs, version="3.0")
    current = build_agent_prompt("ARTIST", inputs, version="4.0")

    assert current.template_id == "agent.artist.v4"
    assert "purposeful typography" in current.text
    assert "Preserve exact supplied wording" in current.text
    assert "Never invent a logo" in current.text
    assert "purposeful typography" not in previous.text
    with pytest.raises(ValueError):
        build_agent_prompt("WRITER", inputs, version="4.0")


def test_independent_artist_v5_asks_for_explicit_cta_design() -> None:
    inputs = {"visual_direction": "Photograph a cup of coffee"}
    previous = build_agent_prompt("ARTIST", inputs, version="4.0")
    current = build_agent_prompt("ARTIST", inputs, version="5.0")

    assert current.template_id == "agent.artist.v5"
    assert "rather than incidental body text" in current.text
    assert "rather than incidental body text" not in previous.text


def test_artist_v6_and_reviewer_v4_check_specific_visual_constraints() -> None:
    inputs = {"visual_direction": "Photograph a cup of coffee"}
    previous = build_agent_prompt("ARTIST", inputs, version="5.0")
    current = build_agent_prompt("ARTIST", inputs, version="6.0")
    review = build_reviewer_prompt({"briefing": "A campaign", "image_prompt": "No buttons"})

    assert current.template_id == "agent.artist.v6"
    assert "rounded rectangles, translucent panels, pills" in current.text
    assert "rounded rectangles, translucent panels, pills" not in previous.text
    assert review.template_id == "agent.reviewer.v6"
    assert "REFINE" in review.text
    assert "requirements absent from the brief" in review.text


def test_reviewer_v5_distinguishes_textual_description_from_visual_verification() -> None:
    inputs = {"briefing": "Preserve the official logo", "image_prompt": "Use the Brand"}
    previous = build_agent_prompt("REVIEWER", inputs, version="4.0")
    current = build_agent_prompt("REVIEWER", inputs, version="5.0")

    assert current.version == "5.0"
    assert "cannot prove exact fidelity" in current.text
    assert "Do not claim that such fidelity was visually verified" in current.text
    assert "do not reject solely because no reference was supplied" in current.text
    assert "cannot prove exact fidelity" not in previous.text


def test_reviewer_v6_checks_visual_criteria_and_requires_actionable_refinement() -> None:
    current = build_reviewer_prompt({"briefing": "Launch visual", "image_prompt": "No text"})

    assert current.version == "6.0"
    assert "aspect ratio and framing" in current.text
    assert "cropped or cut off" in current.text
    assert "unexpected visible text" in current.text
    assert "material, visible requirement" in current.text
    assert "cannot prove exact fidelity" in current.text
    assert "concrete visual correction" in current.text
    assert "preserve the approved Creative Concept" in current.text


def test_independent_artist_v7_guides_photography_without_imposing_it() -> None:
    inputs = {"visual_direction": "An illustrated campaign"}
    previous = build_agent_prompt("ARTIST", inputs, version="6.0")
    current = build_agent_prompt("ARTIST", inputs, version="7.0")

    assert current.template_id == "agent.artist.v7"
    assert "When the requested style is photographic" in current.text
    assert "contact shadows, perspective" in current.text
    assert "honor the brief and any requested non-photographic treatment" in current.text
    assert "contact shadows, perspective" not in previous.text
    with pytest.raises(ValueError):
        build_agent_prompt("REVIEWER", inputs, version="7.0")


@pytest.mark.parametrize(
    ("version", "expected_hash"),
    [
        ("6.0", "6fa3a034980961103e5dac540c9d893c01ef394def5db51ff0795c633feaa3ec"),
        ("7.0", "443b137938a4ef3b8207fe5e92b2784f25126f7ca0ffb12fe49bbf086a3b587e"),
    ],
)
def test_versioned_artist_prompts_remain_reproducible(version: str, expected_hash: str) -> None:
    rendered = build_agent_prompt(
        "ARTIST", {"visual_direction": "An illustrated campaign"}, version=version
    )
    assert hashlib.sha256(rendered.text.encode()).hexdigest() == expected_hash


@pytest.mark.parametrize(
    ("version", "expected_hash"),
    [
        ("4.0", "aa784ebc56dd0ecfd021490badd79bc1735a1b3407a459d2828b44d1d9d38519"),
        ("5.0", "92193db0b99ead2f7289556b9162bc0b29fed15b5d0453f8e32ce2e8dde5124f"),
        ("6.0", "1ebf8945d389b7b73e03a91638c97397dd4e8b5b908bbadf46a81c738a002111"),
    ],
)
def test_versioned_reviewer_prompts_remain_reproducible(version: str, expected_hash: str) -> None:
    rendered = build_agent_prompt(
        "REVIEWER", {"briefing": "A campaign", "image_prompt": "No buttons"}, version=version
    )
    assert hashlib.sha256(rendered.text.encode()).hexdigest() == expected_hash


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
