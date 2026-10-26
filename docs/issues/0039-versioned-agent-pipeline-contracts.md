# Issue 0039: versioned agent pipeline contracts

- ADR: [`0017-versioned-agent-pipeline-contracts`](../adr/0017-versioned-agent-pipeline-contracts.md)
- Labels: `agents`, `architecture`, `implementation`

## Scope

Garantir que cada etapa consuma somente o output validado da etapa anterior, com
provenance, hashes, refinamento estruturado e auditoria de lineage.

## Acceptance criteria

- [x] Edges versionados e validação de Workspace/schema.
- [x] Envelopes estruturados sem hidden reasoning.
- [x] Feedback de Reviewer preserva origem e precedência.
- [x] Auditoria registra hashes, schema, predecessor e correlation.
- [x] Testes cobrem handoff, mismatch e isolamento.
- [x] `kickoff()` usa contrato tipado, registry de schemas e contexto explícito de Workspace.
- [x] Saída do provider é JSON estrito, com erros limitados e metadados de prompt/provider/model.
- [x] Saída inválida não é encaminhada para Content, Generation, Generation Job ou Image.
