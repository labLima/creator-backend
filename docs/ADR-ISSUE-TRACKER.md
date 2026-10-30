# Tracker de ADRs e Issues

Este arquivo é o índice versionado da relação entre decisões arquiteturais e trabalho de implementação. Uma ADR registra uma decisão; ela pode ter várias issues. Uma issue tem uma ADR primária e pode referenciar ADRs relacionadas.

As issues #34 a #43 são trackers de ADR-001..010. As issues #108 a #113 são épicos de fase. As tarefas executáveis incluem #2–#33, #49–#54 e #56–#82. A issue #44 controla a descoberta e a migração do legado.

A implementação de observabilidade e correlação desta entrega estende ADR-006 e
ADR-008, mantendo o tracker ADR-006 (#39) como decisão primária e exigindo issue
de implementação vinculada antes do fechamento do tracker.

## Milestones

| Milestone | Propósito |
| --- | --- |
| `00 · Fase -1` | Correções e fundação técnica (CI, containers, auth própria, SQLite) |
| `01 · Fase 0` | Arquitetura e governança |
| `02 · Fase 1` | Fundação e plataforma |
| `03 · Fase 2` | Produto core |
| `04 · Fase 3` | IA, agentes e mídia |
| `05 · Fase 4` | Produção e operação |
| `06 · Fase 5` | Performance e avaliação |

## ADRs

| ADR | Issue tracker | Issues de implementação |
| --- | --- | --- |
| [ADR-001](adr/0001-llm-provider.md) | [#34](https://github.com/labLima/creator-backend/issues/34) | #3, #9, #11, #17, #19, #23, #27, #53 |
| [ADR-002](adr/0002-image-storage.md) | [#35](https://github.com/labLima/creator-backend/issues/35) | #3, #5, #10, #16, #33 |
| [ADR-003](adr/0003-async-image-generation.md) | [#36](https://github.com/labLima/creator-backend/issues/36) | #3, #5, #7, #8, #12, #16, #25, #33, #79 |
| [ADR-004](adr/0004-supabase-auth.md) | [#37](https://github.com/labLima/creator-backend/issues/37) | #3, #14, #15, #20, #25; substituída por ADR-020 |
| [ADR-005](adr/0005-postgresql-sqlalchemy-alembic.md) | [#38](https://github.com/labLima/creator-backend/issues/38) | #2, #3, #5, #6, #29, #50, #51, #52, #53, #54 |
| [ADR-006](adr/0006-versioned-api-envelope.md) | [#39](https://github.com/labLima/creator-backend/issues/39) | #4, #13, #16, #17, #18, #19, #25, #28, #52, [0043](issues/0043-observability-correlation.md) |
| [ADR-007](adr/0007-openapi-first.md) | [#40](https://github.com/labLima/creator-backend/issues/40) | #4, #13, #16, #17, #18, #19, #25, #30, #31, #49, #50, #51, #52, #53, #54, #88 |
| [ADR-008](adr/0008-api-limits-and-soft-delete.md) | [#41](https://github.com/labLima/creator-backend/issues/41) | #5, #13, #15, #18, #22, #25, #49, #50, #51, #52, #53, #54, [0024](issues/0024-api-rate-limiting.md), [0043](issues/0043-observability-correlation.md) |
| [ADR-009](adr/0009-cloud-run-deployment.md) | [#42](https://github.com/labLima/creator-backend/issues/42) | #3, #7, #24, #30, #31, #32, #87, #90, #91 |
| [ADR-010](adr/0010-architecture-governance.md) | [#43](https://github.com/labLima/creator-backend/issues/43) | #1, #21, #26, #30, #31, #44, #52, #104, [0025](issues/0025-quality-controls.md), [0042](issues/0042-security-gate-hardening.md) |
| [ADR-011 Core Resource CRUD](adr/0011-core-resource-crud.md) | [docs/issues/0041](issues/0041-ownership-enforcement.md) | [docs/issues/0041](issues/0041-ownership-enforcement.md), #20 |
| [ADR-011 CrewAI (alias 011A)](adr/0011-crewai-multi-agent-orchestration.md) | [docs/issues/0012](issues/0012-crewai-multi-agent-orchestration.md) | #64, [docs/issues/0013](issues/0013-crewai-adapter.md) |
| [ADR-012](adr/0012-langchain-rag-tool-calling.md) | [docs/issues/0021](issues/0021-langchain-rag-tool-calling.md) | [docs/issues/0022](issues/0022-langchain-retrieval-adapters.md), #49, #73–#77 |
| [ADR-013](adr/0013-content-improvement-preview.md) | [docs/issues/0023](issues/0023-content-improvement-preview.md) | #17, [docs/issues/0023](issues/0023-content-improvement-preview.md) |
| [ADR-014](adr/0014-agent-image-generation-workflow.md) | [#56](https://github.com/labLima/creator-backend/issues/56), [docs/issues/0032](issues/0032-agent-image-generation-workflow.md) | #57, #58, #59, #60, #62–#72; [docs/issues/0033](issues/0033-agent-workflow-persistence.md)–[0036](issues/0036-agent-workflow-api-worker.md) |
| [ADR-015](adr/0015-database-diagram-alignment.md) | [docs/issues/0037](issues/0037-database-diagram-alignment.md) | [#106](https://github.com/labLima/creator-backend/issues/106), [docs/issues/0037](issues/0037-database-diagram-alignment.md) |
| [ADR-016](adr/0016-polymorphic-generation-job-artifacts.md) | [docs/issues/0038](issues/0038-polymorphic-generation-job-artifacts.md) | #79, #80, [docs/issues/0038](issues/0038-polymorphic-generation-job-artifacts.md) |
| [ADR-017](adr/0017-versioned-agent-pipeline-contracts.md) | [docs/issues/0039](issues/0039-versioned-agent-pipeline-contracts.md) | #81, [docs/issues/0039](issues/0039-versioned-agent-pipeline-contracts.md) |
| [ADR-018](adr/0018-event-driven-agent-pipeline.md) | [docs/issues/0040](issues/0040-event-driven-agent-pipeline.md) | [#107](https://github.com/labLima/creator-backend/issues/107), [docs/issues/0040](issues/0040-event-driven-agent-pipeline.md) |
| [ADR-019](adr/0019-credit-ledger.md) | [#54](https://github.com/labLima/creator-backend/issues/54) | #54, [docs/issues/0031](issues/0031-credits.md) |
| [ADR-020](adr/0020-self-hosted-authentication.md) | [#92](https://github.com/labLima/creator-backend/issues/92) | [#93](https://github.com/labLima/creator-backend/issues/93), [#94](https://github.com/labLima/creator-backend/issues/94), [#95](https://github.com/labLima/creator-backend/issues/95), [#96](https://github.com/labLima/creator-backend/issues/96) |
| [ADR-021](adr/0021-sqlite-default-database.md) | [#97](https://github.com/labLima/creator-backend/issues/97) | [#98](https://github.com/labLima/creator-backend/issues/98), [#99](https://github.com/labLima/creator-backend/issues/99), [#100](https://github.com/labLima/creator-backend/issues/100), [#101](https://github.com/labLima/creator-backend/issues/101), [#102](https://github.com/labLima/creator-backend/issues/102) |
| [ADR-022](adr/0022-cookie-auth-provider.md) | [#116](https://github.com/labLima/creator-backend/issues/116) | [0044](issues/0044-cookie-auth-provider.md) encerrada como não necessária; #118–#127; [#128](https://github.com/labLima/creator-backend/issues/128) / [0045](issues/0045-cookie-auth-cutover.md) |
| [ADR-023](adr/0023-estrutura-modular-por-capacidade.md) | [docs/issues/0045](issues/0045-modular-structure-tracker.md) | [docs/issues/0045](issues/0045-modular-structure-tracker.md) |
| [ADR-024](adr/0024-estrutura-plana-por-capacidade.md) | [docs/issues/0048](issues/0048-plain-capability-layout.md) | [docs/issues/0048](issues/0048-plain-capability-layout.md) |

## Regras de atualização

1. Abra uma ADR antes de iniciar trabalho que altere uma decisão arquitetural material.
2. Vincule toda issue à ADR primária no corpo e à issue tracker da ADR pelo GitHub.
3. Não feche a issue tracker enquanto houver issues de implementação abertas; atualize o checklist de progresso.
4. Uma nova necessidade de implementação entra na ADR existente quando preserva a decisão. Crie uma nova ADR apenas quando a decisão ou seus trade-offs mudarem.
5. Na implementação, PRs devem usar `Refs #<issue>`; somente critérios de aceite satisfeitos permitem `Closes #<issue>`.
6. Trackers locais são aceitos (decisão D1) quando a ADR ainda não tem tracker remoto; o tracker remoto deve ser criado antes de fechar a fase correspondente.
