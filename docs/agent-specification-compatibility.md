# Agent specification compatibility

The source document [Creator_Specs_Agentes_v1.md](Creator_Specs_Agentes_v1.md) describes
a proposed four-agent architecture. Its external file references are not included in the
supplied document. The existing Creator workflow remains governed by ADR-014, ADR-017 and
ADR-018; the source document is not an assertion that the proposed architecture is implemented.

Prompt version 2 adapts the source's responsibilities to the existing workflow:

| Existing role | Source responsibilities |
| --- | --- |
| Business | AGT-01 and SUB-01–04 |
| Planner | AGT-02 and SUB-05 |
| Writer | AGT-02/03 and SUB-06–08 |
| Artist | AGT-03 and the existing image provider |
| Reviewer | AGT-04 and SUB-09–11 |

The existing output schemas, event protocol, review decisions and persistence are unchanged.
In particular, the proposed CreativeBlueprint, structured source evidence, deterministic
weighted QA, exact-text compositor, four-agent execution and eleven independent subagents
are not implemented by these prompt changes. Missing fields cannot be represented in the
existing output contracts; prompts do not create enforcement for those fields. A future
implementation requires versioned contracts, workflow decisions and migration as applicable.
