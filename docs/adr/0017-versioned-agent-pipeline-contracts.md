# ADR-017: versioned agent pipeline hand-off contracts

- Status: accepted
- Tracker: [docs/issues/0039](../issues/0039-versioned-agent-pipeline-contracts.md)

## Decision

Business, Planner, Writer, Artist and Reviewer exchange typed JSON envelopes. Each
edge declares its predecessor, successor, schema/version, required fields and the
only permitted transformation. Envelopes carry Workspace/Brand provenance,
correlation and context hashes; prompts are projections and never the workflow
state. Invalid or cross-Workspace envelopes are rejected at the application
boundary. Step audit data stores hashes and lineage, never hidden reasoning.

The provider-facing kickoff boundary is also typed. It accepts an explicit
Principal/Workspace/Workspace Role authorization context and selects its output
schema from a server-owned role registry. Provider text is parsed as JSON and
validated with the selected strict schema before an execution result is returned.
Prompt template identity/version, canonical input hash, output hash, provider and
model are part of that result and the corresponding workflow-step audit record.
Kickoff failures use bounded application error codes and never expose raw provider
output or forward invalid data to Content, Generation, Generation Job or Image.

## Consequences

Retries and resume can use completed validated steps without reconstructing state
from free text. Reviewer refinements remain structured and attributable. Adding an
edge or changing a schema requires a new contract version and migration as needed.
Provider failures remain safe to retry and are distinguishable from invalid agent
output or unauthorized Workspace execution.
