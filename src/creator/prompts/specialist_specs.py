"""Versioned, server-owned descriptions of the image workflow specialists."""

from dataclasses import dataclass

from creator.domain.agent_workflow import AgentWorkflowStepRole

SPECIALIST_SPEC_VERSION = "2.0"


@dataclass(frozen=True, slots=True)
class SpecialistSpec:
    role: AgentWorkflowStepRole
    spec_version: str
    goal: str
    instructions: str
    inputs: tuple[str, ...]
    output: str
    permitted_tools: tuple[str, ...] = ()


SPECIALIST_SPECS: dict[AgentWorkflowStepRole, SpecialistSpec] = {
    AgentWorkflowStepRole.BUSINESS: SpecialistSpec(
        AgentWorkflowStepRole.BUSINESS,
        SPECIALIST_SPEC_VERSION,
        "Consolidate strategic context from authorized Brand and Campaign data.",
        "Extract identity, Persona, Campaign and reference evidence. Never invent facts, "
        "prices, claims, permissions or Persona attributes; distinguish unknowns from facts. "
        "Brand rules take precedence over Campaign instructions and references. "
        "Identify principles that may be used without copying third-party identity.",
        ("workflow", "brand", "brand_settings", "knowledge"),
        "BusinessOutput",
    ),
    AgentWorkflowStepRole.PLANNER: SpecialistSpec(
        AgentWorkflowStepRole.PLANNER,
        SPECIALIST_SPEC_VERSION,
        "Plan one coherent advertising idea for each requested item.",
        "Use the validated Brand context and Campaign request. Consider direct, metaphorical "
        "and unexpected territories, select one idea per item, and align the objective, "
        "message and Persona. Do not invent product facts or expose private reasoning.",
        ("workflow", "predecessor"),
        "PlannerOutput",
    ),
    AgentWorkflowStepRole.WRITER: SpecialistSpec(
        AgentWorkflowStepRole.WRITER,
        SPECIALIST_SPEC_VERSION,
        "Develop complementary copy and visual direction for the selected idea.",
        "Preserve the selected idea, Brand constraints and verified facts. Make copy and image "
        "complementary, with a dominant visual device and executable layout. Never invent "
        "offers, benefits or prices; preserve mandatory text. Compile the visual prompt without "
        "changing the idea, and reserve space for exact text or logos when required.",
        ("business_context", "predecessor", "post", "feedback", "item"),
        "WriterOutput",
    ),
    AgentWorkflowStepRole.ARTIST: SpecialistSpec(
        AgentWorkflowStepRole.ARTIST,
        SPECIALIST_SPEC_VERSION,
        "Generate an image from the validated visual direction.",
        "Execute the approved visual direction without inventing a concept, claim or copy. "
        "Use the authorized image-generation boundary and return a persisted image reference.",
        ("direction",),
        "ImageGenerationResult",
        ("image_generation",),
    ),
    AgentWorkflowStepRole.REVIEWER: SpecialistSpec(
        AgentWorkflowStepRole.REVIEWER,
        SPECIALIST_SPEC_VERSION,
        "Evaluate the generated image against the Brand and briefing.",
        "Review the actual image against the brief and Brand, not beauty alone. Identify "
        "material Brand, product, safety and technical issues and recommend the smallest "
        "correction. Never silently change the strategy or approve a safety violation.",
        ("image", "briefing", "brand_context"),
        "ReviewOutput",
        ("image_review",),
    ),
}
