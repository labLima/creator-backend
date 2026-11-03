# Agent specification compatibility

The source document [Creator_Specs_Agentes_v1.md](Creator_Specs_Agentes_v1.md) describes
a proposed four-agent architecture. Its external file references are not included in the
supplied document. The existing Creator workflow remains governed by ADR-014, ADR-017 and
ADR-018; the source document is not an assertion that the proposed architecture is implemented.

The adopted runtime model is the five roles and delivery lifecycle in ADR-014/017/018. The proposed four-agent architecture is not adopted as a replacement. This mapping is normative for interpreting the existing roles, not a promise of independent subagent calls:

| Source proposal | Current role / contract | Implemented? |
| --- | --- | --- |
| AGT-01, SUB-01–04 | Business / `BusinessOutput` | Yes; one role, logical sub-responsibilities only. |
| AGT-02, SUB-05 | Planner / `PlannerOutput` | Yes; one role, logical sub-responsibility only. |
| AGT-02/03, SUB-06–08 | Writer / `WriterOutput` then Artist / image Provider | Partly; SUB-08 has no independent contract or invocation. |
| AGT-03, ADP-01 | Artist / image Provider and workflow artifact | Yes; Artist is not a kickoff `Agent` contract. |
| ADP-02 | Deterministic compositor | No. |
| AGT-04, SUB-09–11 | Reviewer / `ReviewOutput` and multimodal Provider | Reviewer yes; SUBs are not independent calls. |
| ORC-00 / DELIVERY | Creator-owned Agent Workflow and worker | Yes; state transitions and delivery remain Creator-owned. |

Prompt version 3 adds a specific role, outcome, backstory, task and expected output
for each current specialist, following the `design-agent` guidance. The eleven
specialties are documented responsibilities in [docs/agents/subagents](agents/subagents/);
`SPECIALIST_SPECS.instructions` consolidates them, and there are no separate runtime
constants or independent calls. Version 2 remains available
to reproduce earlier text prompts. The version 3 adapter executes Business, Planner and
Writer with individual CrewAI Agents through the configured Creator LLM Provider. Artist and
Reviewer continue to use their existing image and multimodal Provider boundaries.
RAG remains a boundary rather than an active capability: Creator owns the Workspace-scoped
retrieval interface, but the retrieval factory currently returns an unconfigured provider,
so the knowledge base is empty until retrieval is configured. `knowledge_sources` is
model-reported, not verified provenance. The design does not enable CrewAI memory,
delegation or knowledge stores, and this delivery does not claim real retrieval.

The v3 prompt changes do not introduce a CreativeBlueprint, structured source evidence,
weighted QA, exact-text compositor, four-agent execution or eleven independent subagents.
The Reviewer contract still returns a 0–1 score and `APPROVED`/`REFINE`/`REJECTED`; the
proposed nine-axis score, 0–100 thresholds and server-calculated rubric are not implemented.
The worker does have terminal rejection behavior: safety findings and `REJECTED` produce
terminal rejection and consume the source outbox event; bounded `REFINE` continues through
the workflow's refinement limit. Those transitions are covered by workflow tests and are
part of the current behavior, not a claim of unchanged review decisions.

No persisted schema was changed for the prompt v3 work. Artist and Reviewer remain provider
boundaries outside `AGENT_CONTRACTS`; `ArtistOutput` is not a Pydantic model. The detailed
proposal and current contracts are indexed in [docs/agents](agents/README.md).

Version composition is explicit: prompt v2 = specialist spec 2.0; prompt v3 = agent design 3.0
+ specialist spec 2.0. The rendered prompt text is pinned by golden sha256 hashes in
`tests/test_specialist_specs.py`, so any text change requires a version bump. The workflow-step
audit key remains `prompt_template_version` = 3.0; design and spec versions are not persisted
separately in this delivery.
