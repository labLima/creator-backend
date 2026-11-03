# Refactor TODO — Modular Monolith (creator-backend)

> Checklist de execução do plano em `tasks/plan.md`. Regras: um PR por tarefa a partir de `dev`
> (`refactor/fase-N-<slug>`), gates `make check` + `make security` + `make e2e` verdes em cada PR,
> `git diff --exit-code docs/openapi.yaml` e `git diff --exit-code CONTEXT.md` nas fases 1+.
> T1 espelha este checklist em `docs/issues/` + GitHub issues (uma por fase).

## Fase 0 — Governança e guarda-corpos
- [ ] T1  ADR-0023 + tracker + issues de implementação (docs/adr, ADR-ISSUE-TRACKER, docs/issues, GitHub)
- [ ] T2  import-linter com baseline (.importlinter, pyproject, Makefile)
- [ ] T3  Fixture dourada de 222 rotas (tests/test_route_inventory.py)
- [ ] T4  Guardas de estrutura com baseline por fase (tests/test_structure_guards.py)
- [ ] T5  Baseline de cobertura por pacote (docs/refactor/coverage-baseline.md)
- [ ] T6  Fingerprint do schema SQLAlchemy (tests/test_schema_fingerprint.py)
- [ ] T7  core/models_registry.py + repoint migrations (PR isolado, nenhum model se move)
- [ ] T8  Teste de resolução dos paths RQ (tests/test_job_paths.py)
- [ ] T9  Política de merge/rollback (docs/refactor/README.md)
- [ ] T10 core/config.py com shim
- [ ] T11 make refactor-guards + job de CI

### ✅ Checkpoint C0
- [ ] make check / security / e2e / refactor-guards verdes
- [ ] alembic upgrade head (DB vazio) + alembic check limpos
- [ ] docs/openapi.yaml sem diff · fixture com 222 operações
- [ ] Revisão humana aprovada para iniciar fase 1

## Fase 1 — Rotas e DTOs (222 handlers; um módulo por PR; billing por último)
- [ ] T12 Casca api/ (router agregador, errors, openapi; settings injetado)
- [ ] T13 Módulo auth (5 rotas)
- [ ] T14 Módulo users (6 rotas)
- [ ] T15 Módulo workspaces pt.1 (workspace + memberships)
- [ ] T16 Módulo workspaces pt.2 (invites + usage)
- [ ] T17 Módulo brands pt.1 (CRUD + settings)
- [ ] T18 Módulo brands pt.2 (cores, assets, knowledge)
- [ ] T19 Módulo contents pt.1 (CRUD + paginação)
- [ ] T20 Módulo contents pt.2 (geração texto/imagem, melhoria)
- [ ] T21 Módulo generations (9 rotas)
- [ ] T22 Módulo agent_workflows (4 rotas, URL preservada)
- [ ] T23 Módulo design (5 rotas)
- [ ] T24 Módulo marketing pt.1 (campaigns + plannings) — depende OQ-2
- [ ] T25 Módulo marketing pt.2 (personas + post structures)
- [ ] T26 Módulo notifications pt.1
- [ ] T27 Módulo notifications pt.2
- [ ] T28 billing router pt.1 (accounts/addresses/payment/subscriptions)
- [ ] T29 billing router pt.2 (invoices/charges/coupons)
- [ ] T30 billing router pt.3 (provider*/webhooks/idempotency) — depende OQ-5
- [ ] T31 billing router pt.4 (credits/orders/refunds) — esvazia api/dtos/billing
- [ ] T32 Limpeza fase 1 + guarda main.py < 300 linhas

### ✅ Checkpoint C1
- [ ] Gates verdes · openapi.yaml sem diff · 222 operationIds idênticos
- [ ] main.py < 300 linhas, sem rotas de negócio · CONTEXT.md sem diff

## Fase 2 — Application → service.py + ports.py
- [ ] T33 event_publisher → core/outbox/dispatcher (quebra ciclo)
- [ ] T34 core/uow.py (UnitOfWorkProtocol 4 métodos + Base)
- [ ] T35 core/pagination.py com shim
- [ ] T36 Ports pt.1 (auth, users, workspaces, brands)
- [ ] T37 Ports pt.2 (contents, generations, agent_workflows, design)
- [ ] T38 Ports pt.3 (marketing, notifications)
- [ ] T39 Ports pt.4 (billing, 32 Protocols)
- [ ] T40 core/outbox/ports.py
- [ ] T41 modules/auth/service.py
- [ ] T42 contents services pt.1 (texto + melhoria)
- [ ] T43 contents services pt.2 (imagem + storage)
- [ ] T44 agent_workflows/service.py (+ crewai atrás de port)
- [ ] T45 Services users + workspaces
- [ ] T46 Services brands + design
- [ ] T47 Services marketing
- [ ] T48 Services notifications
- [ ] T49 Services billing pt.1
- [ ] T50 Services billing pt.2
- [ ] T51 Trocar alvo de cobertura (creator.core + creator.modules)

### ✅ Checkpoint C2
- [ ] Gates verdes · lint-imports sem ciclos · sqlalchemy só no allowlist
- [ ] Cobertura ≥80% nos novos alvos · routers sem acesso a repositories

## Fase 3 — Persistência, models e UoW mixins (⚠️ mais arriscada)
- [ ] T52 🛑 REVISÃO HUMANA pré-fase 3 (checklist no PR; nenhum model move sem aprovação)
- [ ] T53 core/persistence/{types,legacy_schema}.py
- [ ] T54 Models users + workspaces (settings → workspaces, ver OQ-1)
- [ ] T55 Models auth (auth_session)
- [ ] T56 Models brands
- [ ] T57 Models contents (content, assets, project) — depende OQ-1
- [ ] T58 Models generations
- [ ] T59 Models agent_workflows
- [ ] T60 Models marketing — depende OQ-2
- [ ] T61 Models billing/notifications/design
- [ ] T62 Remover imports _schema_models (lote 1)
- [ ] T63 Remover _schema_models (lote 2) + guarda
- [ ] T64 UoW mixins pt.1 (auth, users, workspaces, brands)
- [ ] T65 UoW mixins pt.2 (contents, generations, agent_workflows, design)
- [ ] T66 UoW mixins pt.3 + src/creator/uow.py (12 mixins, snapshot 47 atributos)
- [ ] T67 Persistência core.py pt.1 (User, Settings, Workspace, Brand, Project)
- [ ] T68 Persistência core.py pt.2 (Content…ImageGeneration)
- [ ] T69 Persistência dos demais adapters + fim de infrastructure/persistence

### ✅ Checkpoint C3
- [ ] Gates verdes · alembic check limpo · fingerprint idêntico
- [ ] infrastructure/database/models inexistente · test_app_structure reescrito no mesmo PR

## Fase 4 — Providers, prompts, workers, shims e limpeza
- [ ] T70 Fundir adapters Gemini → core/providers/llm — depende OQ-3
- [ ] T71 core/providers/{storage,retrieval,agent_runtime} + core/queue + cookies — depende OQ-4
- [ ] T72 Prompts (base → core; específicos → modules/*/prompts)
- [ ] T73 agent_workflows/tasks.py (worker de 1.249 linhas)
- [ ] T74 contents/tasks.py + core/outbox/tasks.py
- [ ] T75 workers/cli.py estável + shims de paths RQ
- [ ] T76 Remover shims legados + reescrever guardas — depende OQ-7 (drenar fila antes)
- [ ] T77 Atualizar ADR/tracker/issues de encerramento
- [ ] T78 Verificação final ponta-a-ponta (Compose saudável, /health/live 200)

### ✅ Checkpoint C4 (final)
- [ ] Gates verdes · lint-imports com 0 ignores restantes
- [ ] Contrato HTTP idêntico · fingerprint idêntico · main.py < 300 linhas · CONTEXT.md sem diff

## Questões abertas (responder antes da tarefa indicada)
- [ ] OQ-1 Project/assets → contents? (T57/T60) — padrão: contents
- [ ] OQ-2 Campaign/Persona/Planning/PostStructure → marketing? (T24/T25/T60) — padrão: sim
- [ ] OQ-3 Fonte de verdade ao fundir Gemini (T70)
- [ ] OQ-4 Comportamento de cookies a preservar (T71)
- [ ] OQ-5 Alias /content/{id} e PUT duplicado: remover ou preservar? (T30/T32)
- [ ] OQ-6 app=create_app() no import: manter ou lazy? (T78) — padrão: manter
- [ ] OQ-7 Vida dos shims de job paths (T76) — padrão: 1 release + fila drenada
