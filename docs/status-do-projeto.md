# Status do projeto Creator

Atualizado em: 2026-11-03

Este documento é um **snapshot datado**. O estado canônico das issues está no
GitHub (`labLima/creator-backend`) e no `docs/ADR-ISSUE-TRACKER.md`.

## Visão geral

Creator é um backend Python/FastAPI multi-tenant, contract-first, com isolamento
por Workspace, autenticação própria, SQLite como banco padrão e providers
externos atrás de interfaces.

A branch `dev` é a linha de integração. A `main` é release e está atrás da `dev`.

## O que está concluído

- API versionada em `/api/v1`, envelope de sucesso/erro e `request_id`.
- Estrutura plana por capacidade (`src/creator/<entidade>/`), conforme ADR-024
  e PR #129; contrato HTTP e schema preservados.
- Autenticação própria: signup, login, refresh rotativo, logout e sessões
  revogáveis. A API autentica exclusivamente por cookies `HttpOnly`, com CSRF e
  validação de Origin; login, signup e refresh não retornam tokens no corpo.
  Supabase Auth foi removido.
- Persistência SQLAlchemy com baseline SQLite `0001_sqlite_baseline`, WAL,
  foreign keys e testes de integração em SQLite.
- CRUD dos recursos centrais, com escopo por Workspace e Soft Delete.
- Geração de texto e imagem com Gemini, prompts versionados, storage local ou
  Supabase opcional, RQ e idempotência.
- Workflow multiagente Business → Planner → Writer → Artist → Reviewer, com
  runs/steps persistidos, reviewer multimodal e pipeline tipado.
- Rate limiting distribuído, métricas Prometheus, Ruff, mypy e pytest.
- Contrato OpenAPI estático em paridade com `app.openapi()` (teste de CI).

## Fase -1 concluída

A milestone `00 · Fase -1 — Correções e Fundação Técnica` foi concluída em 2026-10-26 (22/22 issues). Ela entregou:

- security gate, lint/type e E2E no CI;
- Docker Compose com SQLite em volume, Redis, API, worker e migrations;
- `make dev/start`, `dev/stop`, `dev/clean`;
- autenticação própria (ADR-020);
- SQLite e tipos portáveis (ADR-021);
- correção do entrypoint `creator-worker`;
- documentação e governança.

O PR #115 foi mergeado em `dev`. O CI da `dev` passou em quality, security, contract, e2e e containers. A milestone está fechada; as fases seguintes estão desbloqueadas.

## Fase 1 encerrada

A milestone `02 · Fase 1 — Fundação e Plataforma` foi encerrada em 2026-11-03.
O registro de evidências, critérios e dispensas está em
[`docs/milestones/fase-1-encerramento.md`](milestones/fase-1-encerramento.md).
O PR de encerramento é o [#136](https://github.com/labLima/creator-backend/pull/136).

Os itens de operação de produção (#23, #24, #31, #32) foram explicitamente
dispensados para a Fase 4; a paridade de comportamento do legado foi transferida
para a [#134](https://github.com/labLima/creator-backend/issues/134).

## Pendências conhecidas

- Consolidação estrutural complementar: 23 `service.py` ainda importam
  `creator.api`, 4 routers acessam o UoW diretamente e os 47 repositórios por
  agregado (fase 5 da ADR-023) seguem pendentes — ver
  [0049](issues/0049-flat-layout-consolidation.md) / #133.
- Backlog de segurança pré-existente S1–S13 — ver
  [0046](issues/0046-security-backlog-after-modularization.md). S1 corrigido;
  S2–S13 abertos.
- Paridade de comportamento com o legado e ETL — ver
  [0050](issues/0050-legacy-behavior-parity.md) / #134.
- Paridade de `operationId` OpenAPI — ver
  [0051](issues/0051-openapi-operation-id-parity.md) / #135.
- Brand Knowledge ainda não tem repositórios/casos de uso completos (#49).
- Créditos têm schema e ledger, mas o lifecycle e os consumidores ainda precisam
  ser fechados (#54).
- CrewAI real ainda não é importado; o adapter atual usa o runner determinístico
  (#64).
- Jobs COPY/CAPTION ainda não têm executores/filas (#79).
- RAG, tool calling e ingestão por Workspace (#73–#77) não começaram.
- Operação de produção (#23, #24, #31, #32) permanece na Fase 4.
- Cache de geração e avaliação de agentes/RAG (#53, #78) pendentes.

## Estado do CI

O job de qualidade executa `make check`; o de segurança executa `pip-audit` e
Gitleaks; o de contrato valida a paridade OpenAPI e o build; o de E2E executa
`make e2e`; o de containers sobe o Compose e valida health/migrations/worker.
O PR #129 passou nesses jobs e foi mergeado em `dev` em 2026-11-03.

## Leituras principais

- `CONTEXT.md`: vocabulário e boundaries.
- `docs/ADR-ISSUE-TRACKER.md`: índice de ADRs, milestones e issues.
- `docs/adr/`: decisões arquiteturais.
- `docs/issues/`: backlog local e critérios de aceite.
- `docs/openapi.yaml`: contrato HTTP.
- `README.md`: execução local, Compose, worker e comandos.
