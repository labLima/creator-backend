# Encerramento da Fase 1 — Fundação e Plataforma

- Milestone: `02 · Fase 1 — Fundação e Plataforma` (#3)
- Épico: #109
- PR: [#136](https://github.com/labLima/creator-backend/pull/136)
- Branch: `feat/milestone-3-foundation`
- Base: `dev` @ `108fb09`
- Status: em validação até o merge do PR
- Data: 2026-11-03

## Veredito

A Fase 1 entrega a fundação técnica do Creator e encerra os trackers de ADR com
escopo explícito. O que pertence à operação de produção foi **dispensado para a
Fase 4**, não declarado concluído. O que pertence à paridade de comportamento do
legado foi transferido para a [0050](../issues/0050-legacy-behavior-parity.md)
([#134](https://github.com/labLima/creator-backend/issues/134)) com inventário e
matriz reais.

## Escopo entregue

- API com 227 operações e 103 paths no OpenAPI (inclui `/health`, `/health/live` e `/metrics`) e envelope `{success,data,meta.request_id}`.
- 27 capacidades em `src/creator/<entidade>/` (ADR-024).
- 51 tabelas no metadata SQLite, com DDL congelado em `tests/contracts/`.
- Autenticação própria por cookies `HttpOnly`, CSRF e Origin (ADR-020/022).
- SQLite como banco padrão, WAL e foreign keys (ADR-021).
- Docker Compose com API, worker, Redis, SQLite e migrations.
- Geração de texto/imagem, workflow de agentes, rate limiting, métricas, E2E.
- OpenAPI de superfície paritário (paths, métodos e segurança) e snapshots de
  rotas/serializers.
- Matriz de schema completa em [`docs/SCHEMA-MIGRATION-MATRIX.md`](../SCHEMA-MIGRATION-MATRIX.md).
- Inventário do legado em [`docs/migration/legacy-inventory.md`](../migration/legacy-inventory.md).
- Matriz de comportamento em [`docs/migration/legacy-compatibility-matrix.md`](../migration/legacy-compatibility-matrix.md).
- Correção do S1 (Brand Settings cross-tenant) com testes de regressão.

## Critérios de saída da milestone

| Critério | Evidência | Status |
| --- | --- | --- |
| Issues da fase fechadas com evidência | Corpos de #34/#40/#42/#43/#109 atualizados; fechamento remoto será feito no merge. #44 está fechada como `completed`, mas seus critérios não foram atendidos; o escopo remanescente está na #134. | ✅ (fechamento no merge) |
| OpenAPI paritário | paths/métodos/segurança verdes; `operationId` e error responses na [#135](https://github.com/labLima/creator-backend/issues/135) | ✅ (superfície; gap documentado) |
| Matriz de migração do legado | `docs/SCHEMA-MIGRATION-MATRIX.md` + `docs/migration/*` + `tests/test_schema_migration_matrix.py` | ✅ |
| Nenhuma issue da fase sem milestone/critério | auditoria da milestone 3; dispensas registradas no tracker central | ✅ |
| `make check` / `make security` / `make e2e` | ver seção Evidência | ✅ |
| Contrato e schema congelados | `docs/openapi.yaml` e `CONTEXT.md` sem diff | ✅ |

## Dispensas explícitas para a Fase 4

| Issue | Tracker | Motivo | Destino |
| --- | --- | --- | --- |
| #23 | #34 / ADR-001 | Custo/consumo de IA é observabilidade de produção | Fase 4 |
| #24 | #42 / ADR-009 | Imagem multi-stage/readiness/SIGTERM | Fase 4 |
| #31 | #40/#42/#43 | Runbooks, SLO, backup e incidentes | Fase 4 |
| #32 | #42 / ADR-009 | CD Cloud Run depende de credenciais/decisão de produção | Fase 4 |

Elas continuam abertas, com critérios originais preservados; não foram marcadas
como concluídas.

## Dívidas residuais (não bloqueiam a Fase 1)

- [#133](https://github.com/labLima/creator-backend/issues/133) — consolidação
  da estrutura plana (services/API, routers/UoW, 47 repositórios).
- [#134](https://github.com/labLima/creator-backend/issues/134) — paridade de
  comportamento do legado e ETL.
- [#135](https://github.com/labLima/creator-backend/issues/135) — `operationId`
  do OpenAPI.
- [0046](../issues/0046-security-backlog-after-modularization.md) — S2–S13
  (S1 corrigido).
- [0047](../issues/0047-cookie-auth-cutover.md) — sign-off de frontend e prazo
  de depreciação do cutover de cookies; gate de release, não de fundação.

## Evidência

Execução local em 2026-11-03:

- `make check`: **396 passed**, 16 e2e deselected, cobertura **73,76%**;
  Ruff check/format e mypy strict limpos; Alembic `upgrade head` + `check` sem
  operações pendentes.
- `make security`: pip-audit sem vulnerabilidades; Gitleaks sem vazamentos.
- `make e2e`: **16 passed**.
- `git diff --exit-code docs/openapi.yaml`: sem diff.
- `git diff --exit-code CONTEXT.md`: sem diff.
- `tests/test_schema_migration_matrix.py`: cobre todas as 51 tabelas.
- CI remoto: executar no head final do PR #136 antes do merge.

## Rollback

Reverter apenas os commits documentais deste PR. O commit `4a23433` (fix S1)
**não** deve ser revertido com o encerramento. Se o encerramento for revertido,
reabrir os trackers #34/#40/#42/#43/#109; as issues #23/#24/#31/#32 permanecem na
Fase 4. Nenhuma migração de dados ou deploy é executada por este encerramento.
