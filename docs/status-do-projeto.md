# Status do projeto Creator

Atualizado em: 2026-10-26

Este documento é um **snapshot datado**. O estado canônico das issues está no
GitHub (`labLima/creator-backend`) e no `docs/ADR-ISSUE-TRACKER.md`.

## Visão geral

Creator é um backend Python/FastAPI multi-tenant, contract-first, com isolamento
por Workspace, autenticação própria, SQLite como banco padrão e providers
externos atrás de interfaces.

A branch `dev` é a linha de integração. A `main` é release e está atrás da `dev`.

## O que está concluído

- API versionada em `/api/v1`, envelope de sucesso/erro e `request_id`.
- Autenticação própria: signup, login, refresh rotativo, logout e sessões
  revogáveis. Supabase Auth foi removido.
- Persistência SQLAlchemy com baseline SQLite `0001_sqlite_baseline`, WAL,
  foreign keys e testes de integração em SQLite.
- CRUD dos recursos centrais, com escopo por Workspace e Soft Delete.
- Geração de texto e imagem com Gemini, prompts versionados, storage local ou
  Supabase opcional, RQ e idempotência.
- Workflow multiagente Business → Planner → Writer → Artist → Reviewer, com
  runs/steps persistidos, reviewer multimodal e pipeline tipado.
- Rate limiting distribuído, métricas Prometheus, Ruff, mypy e pytest.
- Contrato OpenAPI estático em paridade com `app.openapi()` (teste de CI).

## Fase -1 em andamento

A milestone `00 · Fase -1 — Correções e Fundação Técnica` concentra:

- security gate, lint/type e E2E no CI;
- Docker Compose com SQLite em volume, Redis, API, worker e migrations;
- `make dev/start`, `dev/stop`, `dev/clean`;
- autenticação própria (ADR-020);
- SQLite e tipos portáveis (ADR-021);
- correção do entrypoint `creator-worker`;
- documentação e governança.

## Pendências conhecidas

- Brand Knowledge e créditos têm schema, mas ainda faltam repositórios,
  casos de uso e testes de lifecycle (#49, #54).
- CrewAI real ainda não é importado; o adapter atual usa o runner determinístico
  (#64).
- Jobs COPY/CAPTION ainda não têm executores/filas (#79).
- RAG, tool calling e ingestão por Workspace (#73–#77) não começaram.
- CI/CD de produção, observabilidade e deploy Cloud Run (#21–#32) pendentes.
- Cache de geração e avaliação de agentes/RAG (#53, #78) pendentes.

## Estado do CI

O job de qualidade executa `make check`; o de segurança executa `pip-audit` e
Gitleaks; o de contrato valida a paridade OpenAPI e o build; o de E2E executa
`make e2e`; o de containers sobe o Compose e valida health/migrations/worker.

## Leituras principais

- `CONTEXT.md`: vocabulário e boundaries.
- `docs/ADR-ISSUE-TRACKER.md`: índice de ADRs, milestones e issues.
- `docs/adr/`: decisões arquiteturais.
- `docs/issues/`: backlog local e critérios de aceite.
- `docs/openapi.yaml`: contrato HTTP.
- `README.md`: execução local, Compose, worker e comandos.
