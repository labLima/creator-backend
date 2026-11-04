# Status do projeto Creator

Atualizado em: 2026-11-04

Este documento é um **snapshot datado**. O estado canônico das issues está no
GitHub (`labLima/creator-backend`) e no `docs/ADR-ISSUE-TRACKER.md`.

## Visão geral

Creator é um backend Python/FastAPI multi-tenant, contract-first, com isolamento
por Workspace, autenticação própria, SQLite como banco padrão e providers
externos atrás de interfaces.

A branch `dev` é a linha de integração. A `main` é release, está mais de 100
commits atrás da `dev` e o CI remoto atual dela está vermelho; o HEAD da `dev`
está verde.

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
- Configurações v3 dos agentes (goal, backstory, task, expected output) e
  adapter CrewAI atrás da factory; flag desligada falha fechada.
- Rate limiting distribuído, métricas Prometheus, Ruff, mypy e pytest.
- Contrato OpenAPI estático em paridade de paths/methods/security/operationIds
  com `app.openapi()`; 403/404/409 são comparados por operação e
  401/422/429/500 são convenções globais (#135, branch de implementação).

## Fases encerradas

- `00 · Fase -1 — Correções e Fundação Técnica`: 22/22 issues.
- `01 · Fase 0 — Arquitetura e Governança`: 2/2 issues.
- `02 · Fase 1 — Fundação e Plataforma`: 18/18 issues; evidências em
  [`docs/milestones/fase-1-encerramento.md`](milestones/fase-1-encerramento.md).
- `07 · Auth JWT em cookies`: 13/13 issues.

## Auditoria de issues de 2026-11-04

Encerramentos por implementação ou obsolescência:

- #29 — testes PostgreSQL/Testcontainers: obsoleta pela ADR-021 (SQLite);
  testes de repositório/integridade já existem em SQLite.
- #63 — configurações reais dos agentes: entregue em `AGENT_DESIGNS` v3.0 e
  testes golden.
- #64 — integração CrewAI: entregue no adapter, factory e worker, com testes.
- #66 — boundary Artist/Reviewer: registrado em ADR-014 e na documentação de
  compatibilidade.
- #134 — paridade com Create Bloom/ETL: encerrada como não planejada; o produto
  está sendo construído com arquitetura nova (ver
  [0050](issues/0050-legacy-behavior-parity.md)).

Issues reescritas ou corrigidas:

- #50 — passou de “calendário editorial” para lifecycle de Planning.
- #49 — Brand Knowledge volta a ser pendente; o schema anterior foi removido.
- #54 — créditos voltam a ser pendentes; o schema antigo foi removido e o ledger
  real (wallet/saldo/preços/idempotência) não existe.
- #133 — consolidação de repositórios concluída (27 arquivos); restam 23
  `service.py` que importam `creator.api` e 4 routers que usam o UoW.

## Pendências conhecidas

- Consolidação estrutural complementar: 23 `service.py` ainda importam
  `creator.api`; 4 routers acessam o UoW diretamente — ver
  [0049](issues/0049-flat-layout-consolidation.md) / #133.
- Backlog de segurança pré-existente S1–S13 — ver
  [0046](issues/0046-security-backlog-after-modularization.md). S1 corrigido;
  S2–S13 abertos.
- Paridade de `operationId`/error responses do OpenAPI implementada na branch
  `feat/135-openapi-operation-ids`; aguarda revisão/merge — ver
  [0051](issues/0051-openapi-operation-id-parity.md) / #135.
- Brand Knowledge e RAG ainda não têm schema ativo, ingestão nem retriever
  configurado (#49, #74–#77).
- Créditos têm apenas a tabela genérica `workspace_credit_transactions`; wallet,
  ledger, preços e débito atômico continuam pendentes (#54).
- O adapter CrewAI existe atrás de `CREWAI_ENABLED`; com a flag desligada ou
  CrewAI não instalado, o fallback é o runner determinístico/unconfigured.
- Jobs COPY/CAPTION ainda não têm executores/filas (#79/#80).
- Operação de produção (#23, #24, #31, #32) permanece na Fase 4.
- Cache de geração e avaliação de agentes/RAG (#53, #78) pendentes.
- Publicação, performance signal e feedback de conteúdo ainda não existem;
  ver CONTEXT.md.

## Estado do CI

O job de qualidade executa `make check`; o de segurança executa `pip-audit` e
Gitleaks; o de contrato valida a paridade OpenAPI e o build; o de E2E executa
`make e2e`; o de containers sobe o Compose e valida health/migrations/worker.
Os commits da auditoria (`21456f6`, `0ebce96`, `81cf842`) passaram nesses jobs.
A `main` está atrás e com CI vermelho; a release precisa de um PR `dev → main`
quando for decidida.

## Leituras principais

- `CONTEXT.md`: vocabulário, fluxo e boundaries.
- `docs/ADR-ISSUE-TRACKER.md`: índice de ADRs, milestones e issues.
- `docs/adr/`: decisões arquiteturais.
- `docs/issues/`: backlog local e critérios de aceite.
- `docs/openapi.yaml`: contrato HTTP.
- `README.md`: execução local, Compose, worker e comandos.
