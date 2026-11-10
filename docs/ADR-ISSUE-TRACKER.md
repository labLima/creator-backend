# Tracker de ADRs e Issues

Este arquivo é o índice versionado da relação entre decisões arquiteturais e trabalho de implementação. Uma ADR registra uma decisão; ela pode ter várias issues. Uma issue tem uma ADR primária e pode referenciar ADRs relacionadas.

As issues #34 a #43 são trackers de ADR-001..010. As issues #108 a #113 são épicos de fase. As tarefas executáveis incluem #2–#33, #49–#54 e #56–#82. A issue #44 registrou o inventário do legado; a migração de comportamento foi encerrada como não planejada em 2026-11-04 (#134 / [0050](issues/0050-legacy-behavior-parity.md)).

A implementação de observabilidade e correlação desta entrega estende ADR-006 e
ADR-008, mantendo o tracker ADR-006 (#39) como decisão primária e exigindo issue
de implementação vinculada antes do fechamento do tracker.

> **Auditoria de 2026-11-04.** As issues #29, #63, #64, #66 e #134 foram
> encerradas após revisão do código e do estado remoto. As issues #15, #20, #49,
> #50, #51, #52, #53, #54, #79, #106, #110, #111 e #133 tiveram o
> escopo/critérios corrigidos para o vocabulário atual. Ver a seção
> “Auditoria de 2026-11-04” abaixo.

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
| [ADR-001](adr/0001-llm-provider.md) | [#34](https://github.com/labLima/creator-backend/issues/34) | #3, #9, #11, #13 (Gemini image adapter substituído), #17, #19, #23, #27, [#143](https://github.com/labLima/creator-backend/issues/143) / [0053](issues/0053-openai-provider-migration.md) |
| [ADR-002](adr/0002-image-storage.md) | [#35](https://github.com/labLima/creator-backend/issues/35) | #3, #5, #10, #16, #33 |
| [ADR-003](adr/0003-async-image-generation.md) | [#36](https://github.com/labLima/creator-backend/issues/36) | #3, #5, #7, #8, #12, #16, #25, #33, #79 |
| [ADR-004](adr/0004-supabase-auth.md) | [#37](https://github.com/labLima/creator-backend/issues/37) | #3, #14, #15, #20, #25; substituída por ADR-020 |
| [ADR-005](adr/0005-postgresql-sqlalchemy-alembic.md) | [#38](https://github.com/labLima/creator-backend/issues/38) | #2, #3, #5, #6, #29 (fechada como não planejada), #50 (reescrita para Planning), #51, #52, #53, #54 |
| [ADR-006](adr/0006-versioned-api-envelope.md) | [#39](https://github.com/labLima/creator-backend/issues/39) | #4, #13, #16, #17, #18, #19, #25, #28, #52, [0043](issues/0043-observability-correlation.md) |
| [ADR-007](adr/0007-openapi-first.md) | [#40](https://github.com/labLima/creator-backend/issues/40) | #4, #13, #16, #17, #18, #19, #25, #30, #31, #49, #50, #51, #52, #53, #54, #88, [#135](https://github.com/labLima/creator-backend/issues/135) |
| [ADR-008](adr/0008-api-limits-and-soft-delete.md) | [#41](https://github.com/labLima/creator-backend/issues/41) | #5, #13, #15, #18, #22, #25, #49, #50, #51, #52, #53, #54, [0024](issues/0024-api-rate-limiting.md), [0029](issues/0029-activity-events.md), [0043](issues/0043-observability-correlation.md) |
| [ADR-009](adr/0009-cloud-run-deployment.md) | [#42](https://github.com/labLima/creator-backend/issues/42) | #3, #7, #24, #30, #31, #32, #87, #90, #91 |
| [ADR-010](adr/0010-architecture-governance.md) | [#43](https://github.com/labLima/creator-backend/issues/43) | #1, #21, #26, #30, #31, #44, #52, #104, [#134](https://github.com/labLima/creator-backend/issues/134) (fechada como não planejada), [0025](issues/0025-quality-controls.md), [0042](issues/0042-security-gate-hardening.md) |
| [ADR-011 Core Resource CRUD](adr/0011-core-resource-crud.md) | [docs/issues/0041](issues/0041-ownership-enforcement.md) | [docs/issues/0041](issues/0041-ownership-enforcement.md), #20 |
| [ADR-011 CrewAI (alias 011A)](adr/0011-crewai-multi-agent-orchestration.md) | [docs/issues/0012](issues/0012-crewai-multi-agent-orchestration.md) | #64 (fechada), [docs/issues/0013](issues/0013-crewai-adapter.md) |
| [ADR-012](adr/0012-langchain-rag-tool-calling.md) | [docs/issues/0021](issues/0021-langchain-rag-tool-calling.md) | [docs/issues/0022](issues/0022-langchain-retrieval-adapters.md), #49, #73–#77 |
| [ADR-013](adr/0013-content-improvement-preview.md) | [docs/issues/0023](issues/0023-content-improvement-preview.md) | #17, [docs/issues/0023](issues/0023-content-improvement-preview.md) |
| [ADR-014](adr/0014-agent-image-generation-workflow.md) | [#56](https://github.com/labLima/creator-backend/issues/56), [docs/issues/0032](issues/0032-agent-image-generation-workflow.md) | #57, #58, #59, #60, #62, #63 (fechada), #65, #66 (fechada), #67–#72; [docs/issues/0033](issues/0033-agent-workflow-persistence.md)–[0036](issues/0036-agent-workflow-api-worker.md), [#153](https://github.com/labLima/creator-backend/issues/153) / [0055](issues/0055-agent-workflow-from-planning.md) |
| [ADR-015](adr/0015-database-diagram-alignment.md) | [docs/issues/0037](issues/0037-database-diagram-alignment.md) | [#106](https://github.com/labLima/creator-backend/issues/106), [docs/issues/0037](issues/0037-database-diagram-alignment.md), [#159](https://github.com/labLima/creator-backend/issues/159) / [0058](issues/0058-sqlite-final-schema-alignment.md) |
| [ADR-016](adr/0016-polymorphic-generation-job-artifacts.md) | [docs/issues/0038](issues/0038-polymorphic-generation-job-artifacts.md) | #79, #80, [docs/issues/0038](issues/0038-polymorphic-generation-job-artifacts.md) |
| [ADR-017](adr/0017-versioned-agent-pipeline-contracts.md) | [docs/issues/0039](issues/0039-versioned-agent-pipeline-contracts.md) | #81, [docs/issues/0039](issues/0039-versioned-agent-pipeline-contracts.md) |
| [ADR-018](adr/0018-event-driven-agent-pipeline.md) | [docs/issues/0040](issues/0040-event-driven-agent-pipeline.md) | [#107](https://github.com/labLima/creator-backend/issues/107), [docs/issues/0040](issues/0040-event-driven-agent-pipeline.md) |
| [ADR-019](adr/0019-credit-ledger.md) | [#54](https://github.com/labLima/creator-backend/issues/54) | #54, [docs/issues/0031](issues/0031-credits.md) |
| [ADR-020](adr/0020-self-hosted-authentication.md) | [#92](https://github.com/labLima/creator-backend/issues/92) | [#93](https://github.com/labLima/creator-backend/issues/93), [#94](https://github.com/labLima/creator-backend/issues/94), [#95](https://github.com/labLima/creator-backend/issues/95), [#96](https://github.com/labLima/creator-backend/issues/96) |
| [ADR-021](adr/0021-sqlite-default-database.md) | [#97](https://github.com/labLima/creator-backend/issues/97) | [#98](https://github.com/labLima/creator-backend/issues/98), [#99](https://github.com/labLima/creator-backend/issues/99), [#100](https://github.com/labLima/creator-backend/issues/100), [#101](https://github.com/labLima/creator-backend/issues/101), [#102](https://github.com/labLima/creator-backend/issues/102), [#159](https://github.com/labLima/creator-backend/issues/159) |
| [ADR-022](adr/0022-cookie-auth-provider.md) | [#116](https://github.com/labLima/creator-backend/issues/116) | [0044](issues/0044-cookie-auth-provider.md) encerrada como não necessária; #118–#127; [#128](https://github.com/labLima/creator-backend/issues/128) / [0047](issues/0047-cookie-auth-cutover.md) |
| [ADR-023](adr/0023-estrutura-modular-por-capacidade.md) | [docs/issues/0045](issues/0045-modular-structure-tracker.md) | [docs/issues/0045](issues/0045-modular-structure-tracker.md) (histórico; fase 5 em [0049](issues/0049-flat-layout-consolidation.md)) |
| [ADR-024](adr/0024-estrutura-plana-por-capacidade.md) | [docs/issues/0048](issues/0048-plain-capability-layout.md) | [docs/issues/0048](issues/0048-plain-capability-layout.md), [0049](issues/0049-flat-layout-consolidation.md), [#133](https://github.com/labLima/creator-backend/issues/133), [0046](issues/0046-security-backlog-after-modularization.md) (backlog relacionado) |
| [ADR-025](adr/0025-generation-independente-com-especialistas.md) | [#140](https://github.com/labLima/creator-backend/issues/140) | [#141](https://github.com/labLima/creator-backend/issues/141), [0052](issues/0052-generation-jobs-independentes.md) |
| [ADR-026](adr/0026-deterministic-image-composition.md) | [#152](https://github.com/labLima/creator-backend/issues/152) | [#147](https://github.com/labLima/creator-backend/issues/147), [0054](issues/0054-deterministic-image-composition.md); relacionada a #78 |
| [ADR-027](adr/0027-generative-image-adaptation.md) | [#154](https://github.com/labLima/creator-backend/issues/154) | [#155](https://github.com/labLima/creator-backend/issues/155), [#156](https://github.com/labLima/creator-backend/issues/156), [#160](https://github.com/labLima/creator-backend/issues/160), [0056](issues/0056-generative-image-adaptation.md), [0057](issues/0057-image-import.md) |
| [ADR-028](adr/0028-sqlite-final-schema-alignment.md) | [0058](issues/0058-sqlite-final-schema-alignment.md) / [#159](https://github.com/labLima/creator-backend/issues/159) | [0058](issues/0058-sqlite-final-schema-alignment.md); board `SHC` (`SHC-2`–`SHC-26`); relacionada a [ADR-015](adr/0015-database-diagram-alignment.md) e [ADR-021](adr/0021-sqlite-default-database.md) |

A [0049](issues/0049-flat-layout-consolidation.md) é o tracker local da
consolidação da estrutura plana; a issue remota é
[#133](https://github.com/labLima/creator-backend/issues/133). A paridade de
comportamento com o legado foi encerrada como não planejada
([0050](issues/0050-legacy-behavior-parity.md) / [#134](https://github.com/labLima/creator-backend/issues/134)).
A paridade de `operationId`/error responses é a
[0051](issues/0051-openapi-operation-id-parity.md)
([#135](https://github.com/labLima/creator-backend/issues/135)).

## Fase 1 encerrada

A milestone `02 · Fase 1 — Fundação e Plataforma` foi encerrada em 2026-11-03
no merge `1530067` do PR [#136](https://github.com/labLima/creator-backend/pull/136),
com 0 issues abertas. Evidências: [fase-1-encerramento](milestones/fase-1-encerramento.md).

## Dispensas explícitas da Fase 1

| Issue | Tipo | Tracker / ADR | Destino | Milestone destino | Justificativa | Evidência | Aprovado por/data |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #23 | dispensa | #34 / ADR-001 | Fase 4 | 05 · Fase 4 — Produção e Operação | Custo/consumo de IA é observabilidade de produção, não boundary de provider. | #23 permanece aberta na Fase 4. | backend/platform — 2026-11-03 |
| #24 | dispensa | #42 / ADR-009 | Fase 4 | 05 · Fase 4 — Produção e Operação | Imagem multi-stage/readiness/SIGTERM pertence ao endurecimento de produção. | #24 permanece aberta na Fase 4. | backend/platform — 2026-11-03 |
| #31 | dispensa | #40, #42, #43 | Fase 4 | 05 · Fase 4 — Produção e Operação | Runbooks/SLO/backup/incidentes são operação; a paridade de operationId/error responses está na 0051. | #31 permanece aberta na Fase 4. | backend/platform — 2026-11-03 |
| #32 | dispensa | #42 / ADR-009 | Fase 4 | 05 · Fase 4 — Produção e Operação | CD Cloud Run depende de decisão/credenciais de produção; ADR-009 emendada. | #32 permanece aberta na Fase 4. | backend/platform — 2026-11-03 |
| #44 | substituição | #43 / ADR-010 | Fase 2 / #134 | 03 · Fase 2 — Produto Core | Issue fechada como completed sem evidência de comportamento/ETL; inventário produzido e escopo remanescente transferido. A migração foi encerrada como não planejada em 2026-11-04. | `docs/migration/legacy-inventory.md`, #134, [0050](issues/0050-legacy-behavior-parity.md). | backend/platform — 2026-11-04 |

## Auditoria de 2026-11-04

### Encerramentos

| Issue | Tipo | Evidência |
| --- | --- | --- |
| #29 | não planejada | PostgreSQL/Testcontainers contrariam a ADR-021; testes de repositório/integridade já rodam em SQLite. |
| #63 | completed | `AGENT_DESIGNS` v3.0 com goal/backstory/task/expected output para os cinco papéis; testes golden em `tests/test_specialist_specs.py`. |
| #64 | completed | `CrewAIMultiAgentOrchestrator` atrás da factory; worker usa `create_multi_agent_orchestrator`; flag desligada falha fechada; `tests/test_agent_kickoff.py`. |
| #66 | completed | Boundary Artist/Reviewer registrado na ADR-014 e em `docs/agent-specification-compatibility.md`; teste dedicado em `tests/test_specialist_specs.py`. |
| #134 | não planejada | Arquitetura nova, sem paridade/ETL com Create Bloom; ver [0050](issues/0050-legacy-behavior-parity.md). |

### Dispensas de trackers fechados

A regra 3 exige dispensa explícita quando um tracker de ADR é fechado com
implementação aberta. A auditoria manteve os trackers fechados e registra a
dispensa abaixo; nenhuma decisão arquitetural nova é aberta por estas linhas.

| Issue | Tracker / ADR | Destino | Justificativa |
| --- | --- | --- | --- |
| #53 | #34 / ADR-001 | Fase 5 | Cache é performance/avaliação, não boundary de Provider. |
| #79, #80 | #36 / ADR-003 + ADR-016 | Fase 3 | A generalização do Generation Job é decisão da ADR-016; executores seguem na Fase 3. |
| #50, #51, #54 | #38 / ADR-005 | Fase 2 | A decisão SQLAlchemy/Alembic permanece; o trabalho restante é de produto/schema. |
| #135 | #40 / ADR-007 | Fase 2 | Paridade de operationId/error responses é implementação do contrato, não nova decisão. |
| #52 | #43 / ADR-010 | Fase 2 | Activity timeline é implementação de governança, não nova decisão. |
| #15, #20 | #37 / ADR-004 | Fase 2 | ADR-004 foi substituída pela ADR-020; auth/segurança seguem na Fase 2. |

### Reescritas e correções de escopo

| Issue | Ajuste |
| --- | --- |
| #15 | CORS/erros já entregues; restam headers, limite de body e docs em produção; vínculo corrigido para ADR-020/008. |
| #20 | Reescopada para autorização por Workspace + dívidas S2–S13, em vez de ownership por usuário. |
| #49 | Brand Knowledge volta a ser pendente; o schema anterior foi removido na migration `0004_drop_dead_tables`. |
| #50 | Passa de calendário (`calendars`/`calendar_items`) para lifecycle de Planning e vínculo com Content. |
| #51 | Alinhada a Content Feedback append-oriented, distinto de Human Review Decision e Performance Signal. |
| #52 | Alinhada a Activity Event, sem replicar o `activity_log` legado. |
| #53 | Modelo de cache atualizado para JSON portável (ADR-021). |
| #54 | Créditos voltam a ser pendentes; wallet/ledger/preços não existem no código atual. |
| #79 | Modelo/contrato de `artifact_type` entregue; executores COPY/CAPTION pendentes. |
| #106 | Deixa de depender de ETL/legado; foco em constraints, índices, models legados e cobertura OpenAPI. |
| #110 | Critérios da Fase 2 atualizados para Planning/Content feedback/Activity/Credits. |
| #111 | Critérios da Fase 3 atualizados; event-driven pipeline e CrewAI já entregues. |
| #133 | Concluída no PR [#137](https://github.com/labLima/creator-backend/pull/137): nenhum `service.py` importa `creator.api` e os routers não acessam UoW diretamente. |

## Regras de atualização

1. Abra uma ADR antes de iniciar trabalho que altere uma decisão arquitetural material.
2. Vincule toda issue à ADR primária no corpo e à issue tracker da ADR pelo GitHub.
3. Não feche a issue tracker enquanto houver issue de implementação aberta **não dispensada explicitamente** para outra ADR, fase ou issue substituta. A dispensa exige justificativa, destino e evidência na tabela acima e no corpo da issue.
4. Uma nova necessidade de implementação entra na ADR existente quando preserva a decisão. Crie uma nova ADR apenas quando a decisão ou seus trade-offs mudarem.
5. Na implementação, PRs devem usar `Refs #<issue>`; somente critérios de aceite satisfeitos permitem `Closes #<issue>`.
6. Trackers locais são aceitos (decisão D1) quando a ADR ainda não tem tracker remoto; o tracker remoto deve ser criado antes de fechar a fase correspondente.
