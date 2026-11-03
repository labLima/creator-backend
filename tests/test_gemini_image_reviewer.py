from types import SimpleNamespace

from creator.config import Settings
from creator.domain.agent_workflow import AgentWorkflowStepRole
from creator.integrations.gemini.image_reviewer import GeminiMultimodalImageReviewer
from creator.services.agents.design_specs import AGENT_DESIGNS
from creator.services.agents.specs import SPECIALIST_SPECS
from creator.services.ai.reviewer import ImageReviewRequest


def test_review_uses_creative_critic_instructions_with_existing_contract() -> None:
    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            text='{"decision":"REFINE","score":0.7,"feedback":["Fix crop"],"safety_issues":[]}'
        )

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    reviewer = GeminiMultimodalImageReviewer(Settings(), client=client)
    result = reviewer.review(
        ImageReviewRequest(
            image_bytes=b"image",
            mime_type="image/png",
            prompt="prompt",
            briefing="brief",
            brand_context={"voice": "clear"},
        )
    )
    prompt = calls[0]["contents"][0]
    assert SPECIALIST_SPECS[AgentWorkflowStepRole.REVIEWER].instructions in prompt
    assert AGENT_DESIGNS[AgentWorkflowStepRole.REVIEWER].task in prompt
    assert "untrusted data" in prompt
    assert result.decision == "REFINE"
    assert result.feedback == ("Fix crop",)
