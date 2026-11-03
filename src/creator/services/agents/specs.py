"""Versioned, server-owned descriptions of the image workflow specialists."""

from dataclasses import dataclass

from creator.domain.agent_workflow import AgentWorkflowStepRole


@dataclass(frozen=True, slots=True)
class SpecialistSpec:
    role: AgentWorkflowStepRole
    version: str
    goal: str
    instructions: str
    inputs: tuple[str, ...]
    output: str
    permitted_tools: tuple[str, ...] = ()
    source_agents: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreativeSpecialty:
    id: str
    parent: str
    responsibility: str


CREATIVE_SPECIALTIES: tuple[CreativeSpecialty, ...] = (
    CreativeSpecialty("SUB-01", "AGT-01", "Extract Brand identity and source-backed rules."),
    CreativeSpecialty("SUB-02", "AGT-01", "Interpret Persona without inventing attributes."),
    CreativeSpecialty("SUB-03", "AGT-01", "Identify Campaign objective, claims and constraints."),
    CreativeSpecialty("SUB-04", "AGT-01", "Classify references and identify what not to copy."),
    CreativeSpecialty("SUB-05", "AGT-02", "Explore direct, metaphorical and unexpected ideas."),
    CreativeSpecialty("SUB-06", "AGT-02", "Create copy that complements the visual idea."),
    CreativeSpecialty("SUB-07", "AGT-02", "Define art direction and an executable layout."),
    CreativeSpecialty(
        "SUB-08", "AGT-03", "Compile the visual direction without changing the idea."
    ),
    CreativeSpecialty("SUB-09", "AGT-04", "Inspect Brand and product fidelity."),
    CreativeSpecialty("SUB-10", "AGT-04", "Inspect visual and technical quality."),
    CreativeSpecialty("SUB-11", "AGT-04", "Recommend the smallest material correction."),
)


SPECIALIST_SPECS: dict[AgentWorkflowStepRole, SpecialistSpec] = {
    AgentWorkflowStepRole.BUSINESS: SpecialistSpec(
        AgentWorkflowStepRole.BUSINESS,
        "2.0",
        "Consolidate strategic context from authorized Brand and Campaign data.",
        "Extract identity, Persona, Campaign and reference evidence. Never invent facts, "
        "prices, claims, permissions or Persona attributes; distinguish unknowns from facts. "
        "Brand rules take precedence over Campaign instructions and references. "
        "Identify principles that may be used without copying third-party identity.",
        ("workflow", "brand", "brand_settings", "knowledge"),
        "BusinessOutput",
        source_agents=("AGT-01", "SUB-01", "SUB-02", "SUB-03", "SUB-04"),
    ),
    AgentWorkflowStepRole.PLANNER: SpecialistSpec(
        AgentWorkflowStepRole.PLANNER,
        "2.0",
        "Plan one coherent advertising idea for each requested item.",
        "Use the validated Brand context and Campaign request. Consider direct, metaphorical "
        "and unexpected territories, select one idea per item, and align the objective, "
        "message and Persona. Do not invent product facts or expose private reasoning.",
        ("workflow", "predecessor"),
        "PlannerOutput",
        source_agents=("AGT-02", "SUB-05"),
    ),
    AgentWorkflowStepRole.WRITER: SpecialistSpec(
        AgentWorkflowStepRole.WRITER,
        "2.0",
        "Develop complementary copy and visual direction for the selected idea.",
        "Preserve the selected idea, Brand constraints and verified facts. Make copy and image "
        "complementary, with a dominant visual device and executable layout. Never invent "
        "offers, benefits or prices; preserve mandatory text. Compile the visual prompt without "
        "changing the idea, and reserve space for exact text or logos when required.",
        ("business_context", "predecessor", "post", "feedback", "item"),
        "WriterOutput",
        source_agents=("AGT-02", "AGT-03", "SUB-06", "SUB-07", "SUB-08"),
    ),
    AgentWorkflowStepRole.ARTIST: SpecialistSpec(
        AgentWorkflowStepRole.ARTIST,
        "2.0",
        "Generate an image from the validated visual direction.",
        "Execute the approved visual direction without inventing a concept, claim or copy. "
        "Use the authorized image-generation boundary and return a persisted image reference.",
        ("direction",),
        "ArtistOutput",
        ("image_generation",),
        ("AGT-03",),
    ),
    AgentWorkflowStepRole.REVIEWER: SpecialistSpec(
        AgentWorkflowStepRole.REVIEWER,
        "2.0",
        "Evaluate the generated image against the Brand and briefing.",
        "Review the actual image against the brief and Brand, not beauty alone. Identify "
        "material Brand, product, safety and technical issues and recommend the smallest "
        "correction. Never silently change the strategy or approve a safety violation.",
        ("image", "briefing", "brand_context"),
        "ReviewOutput",
        ("image_review",),
        ("AGT-04", "SUB-09", "SUB-10", "SUB-11"),
    ),
}
