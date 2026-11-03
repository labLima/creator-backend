# Issue 0034: specialist agent contracts, prompts and RAG

- ADR: [`0014-agent-image-generation-workflow`](../adr/0014-agent-image-generation-workflow.md)
- Labels: `agents`, `provider`, `implementation`
- GitHub: [#58](https://github.com/labLima/creator-backend/issues/58)

## Delivered scope (existing issue)

Implementar schemas e prompts versionados para Business, Planner, Writer, Artist e Reviewer, com outputs JSON validados, hash dos inputs e contexto de Brand/BrandSettings/RAG escopado por Workspace.

O documento [Creator Specs Agentes v1](../Creator_Specs_Agentes_v1.md) propõe quatro
agentes e onze especialidades. A adaptação dos prompts aos contratos atuais e seus limites
estão descritos em [agent-specification-compatibility](../agent-specification-compatibility.md).
Os contratos de `CreativeBlueprint`, QA ponderado e composição determinística ainda não
foram implementados; não considerar os critérios abaixo como aceite dessas capacidades.

## Acceptance criteria met by the delivered increment

- [x] Nenhum raciocínio interno é persistido ou exposto.
- [x] Prompt rendering é determinístico e possui testes golden.
- [x] Output inválido não alcança Content, Generation ou Image.
- [x] RAG indisponível usa somente o contexto persistido; `knowledge_sources` é auto-relato
  do modelo e a proveniência verificada permanece follow-up.

## Follow-up proposal (not accepted by this issue)

The four-agent/eleven-subagent design, `CreativeBlueprint`, weighted QA, exact-text compositor,
and independent subagent outputs remain proposals documented in [docs/agents](../agents/README.md).
They are not covered by the completed criteria above. The current review contract remains
0–1 with `APPROVED`, `REFINE` and `REJECTED`; the 0–100 rubric is not implemented.

Prompt v3 and the design records for the five workflow roles (`AGENT_DESIGNS`) were added after
the original acceptance criteria. The eleven SUB documents under
[docs/agents/subagents](../agents/subagents/) are documentation of logical responsibilities;
they are not separate design records or runtime constants. Current
compatibility and behavior, including terminal review rejection and outbox consumption, are
documented in [agent-specification-compatibility](../agent-specification-compatibility.md).
Do not use this completed issue as approval for a new schema, migration or workflow decision.
