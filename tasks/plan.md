# Implementation Plan: Refatoração estrutural — Modular Monolith (creator-backend)

> Gerado em 2026-10-29 a partir de: análise do @reviewer (estrutura atual, evidência arquivo-a-arquivo),
> pesquisa do @architect (bi-fin-lefil-backend + referências da comunidade FastAPI) e plano do @planner
> (skill planning-and-task-breakdown). Decisões de estrutura confirmadas pelo time.

## Overview

Migrar `src/creator/` da estrutura atual (main.py de 5.722 linhas com 222 rotas, `application/`,
`repositories/`, `infrastructure/`, `services/`, `integrations/`, `prompts/`, `workers/`) para o
layout-alvo **`api/` + `core/` + `modules/`**, em 5 fases incrementais (0–4), sem alterar contrato
HTTP, schema do banco, paths de jobs RQ, política de cookies ou o vocabulário de `CONTEXT.md`.
Cada fase termina com gates verdes (`make check`, `make security`, `make e2e` + gate específico)
e cada tarefa cabe em ≤5 arquivos.

**Motivação medida (evidência do estado atual):**
- `main.py`: 5.722 linhas, 222 de 227 rotas dentro de `create_app()` (97,8%), 52 serializers
  `_*_data()`, 128 `unit_of_work.commit()`, patch OpenAPI de ~378 linhas.
- `api/dtos/`: 88 arquivos (1 DTO por arquivo) + fachada de 167 linhas.
- UoW gordo: Protocol com 47 atributos (`application/unit_of_work.py`) espelhado em
  `infrastructure/persistence/unit_of_work.py` (310 linhas, 47 instanciações).
- Dois adapters Gemini quase idênticos (`services/ai/gemini.py` × `integrations/gemini/`).
- Ciclos: `application ⇄ services` e `services ⇄ integrations`.
- Domínio puro = 1,2% do código; persistência + main.py = 60,8%.

## Architecture Decisions

1. **Modular monolith com módulo PLANO ENRIQUECIDO** (escolha do time; precedente: Netflix Dispatch):
   ```
   src/creator/
   ├── main.py                  # composition root: create_app() + middleware + include_router (alvo <300 linhas)
   ├── uow.py                   # composition root do UoW: mixins por módulo
   ├── api/                     # router.py (agregador), openapi.py, errors.py, responses.py, dependencies.py, system.py
   ├── core/                    # shared kernel TÉCNICO — proibido importar modules
   │   ├── config.py, db.py, uow.py, models_registry.py, tenancy.py, errors.py,
   │   │   pagination.py, clock.py
   │   ├── security/            # passwords, tokens, cookies, rate_limit
   │   ├── observability/       # logging, metrics, middleware
   │   ├── queue/               # ports.py (JobQueue) + rq.py
   │   ├── outbox/              # models, ports, persistence, dispatcher, tasks
   │   ├── persistence/         # legacy_schema (34 tabelas "PDF"), legacy_manifest, types
   │   └── providers/           # llm/, storage/, retrieval/, agent_runtime/ (2+ consumidores)
   └── modules/                 # 11 módulos de negócio (reporting reservado no ADR, não criar)
       auth, users, workspaces, brands, contents, generations,
       agent_workflows, design, marketing, billing, notifications
   ```
   Template de cada módulo:
   ```
   modules/<ctx>/
   ├── __init__.py          # vazio — proibido re-exportar
   ├── router.py            # APIRouter + tags; zero lógica de negócio
   ├── schemas.py           # DTOs Pydantic (CreatorDTO, extra=forbid) + to_*_response()
   ├── service.py           # casos de uso; recebe ports, NUNCA models/persistence/UoW
   ├── ports.py             # Protocols + Records + enums/VOs — sem SQLAlchemy, sem Pydantic
   ├── persistence.py       # SqlAlchemy*Repository + mixin de UoW; único importador de models
   ├── models.py            # tabelas SQLAlchemy do contexto
   ├── dependencies.py / errors.py / events.py / tasks.py / prompts/ / public.py  # quando aplicável
   ```
2. **Invariante verificável** (substitui "SQLAlchemy só em infraestrutura", que deixa de existir
   como pasta): `import sqlalchemy` permitido SOMENTE em `core/db.py`, `core/persistence/*`,
   `core/outbox/{models,persistence}.py`, `modules/*/models.py`, `modules/*/persistence.py`.
   Enforçado por AST em `tests/test_structure_guards.py` + contratos import-linter.
3. **Fronteira cross-módulo**: apenas `public.py` (Protocol + Record + Exception; nunca ORM).
   Migrações permanecem centrais (`migrations/versions`, cadeia única; `alembic heads` == 1).
4. **UoW via mixins**: `core/uow.py` (UnitOfWorkProtocol com 4 métodos + UnitOfWorkBase) +
   mixin `*Repositories` por módulo (em `persistence.py`) + composição em `src/creator/uow.py`.
   Custo de módulo novo: 2 linhas no composition root.
5. **`core/` nunca importa `modules/`**. Tipos compartilhados (Principal, WorkspaceId) sobem para
   `core/tenancy.py`. Providers em `core/providers/` só quando têm 2+ consumidores.
6. **Decisões de fronteira** (do @architect, seção B.6): Project → `contents`; biblioteca de
   imagens/Assets → `contents` (output transacional de imagem fica em `generations`);
   BrandKnowledge → `brands`; Settings (workspace) → `workspaces`; credit transactions → `billing`;
   workspace invites → `workspaces`; `marketing` é módulo próprio (Campaign, Persona, Planning,
   PostStructure); `design` fica só com DesignStructure; `reporting` reservado (0 rotas hoje).
7. **Governança (AGENTS.md)**: ADR-0023 obrigatório + tracker issue + issues de implementação por
   fase em `docs/issues/` e GitHub (`labLima/creator-backend`); PRs contra `dev`; branch
   `refactor/fase-N-<slug>`.

**Task list target:** este repositório designa GitHub issues + `docs/ADR-ISSUE-TRACKER.md` como
estado de trabalho. A tarefa **T1** espelha este plano em `docs/issues/` + issues GitHub (uma por
fase). `tasks/todo.md` é o checklist local de execução até o espelhamento acontecer.

---

## Task List

### Fase 0 — Governança e guarda-corpos (nenhum código de negócio se move)

- [ ] **T1 · ADR-0023, tracker e issues de implementação** — escrever
  `docs/adr/0023-modular-monolith-structure.md` (estrutura-alvo, template de módulo, invariante
  sqlalchemy, regra de public.py, reserva de `reporting`, 5 fases + gates), atualizar
  `docs/ADR-ISSUE-TRACKER.md`, criar `docs/issues/0045-refatoracao-modular.md` com checklist das
  fases e espelhar issues no GitHub por fase. *Verif.: grep no tracker; ADR existe; vocabulário ==
  CONTEXT.md.* Deps: —. Arquivos: 3 docs. **M**
- [ ] **T2 · Contratos import-linter em modo baseline** — dependência `import-linter` em `[dev]`,
  `.importlinter` com contratos-alvo (core não importa modules/api; modules independentes exceto
  `public`; api não importa `modules/*/persistence`) + `ignore_imports` com as violações atuais
  medidas (cada linha com `# TODO(fase N)`); target `lint-imports` no Makefile. *Verif.:
  `lint-imports` → 0 violações com baseline.* Deps: T1. Arquivos: pyproject, .importlinter, Makefile. **M**
- [ ] **T3 · Inventário de rotas como fixture dourada** — `tests/fixtures/route_inventory.json`
  com 222 tuplas `(method, path, operationId, tags, response codes)` de `creator.main.app.openapi()`
  + `tests/test_route_inventory.py` (também valida paridade com `docs/openapi.yaml`). *Verif.:
  `pytest -q tests/test_route_inventory.py`; fixture tem 222 entradas, determinística.* Deps: T1. **S**
- [ ] **T4 · Guardas de estrutura com baseline por fase** — `tests/test_structure_guards.py` +
  `tests/structure/baseline.json` + `tests/structure/phase.json`; cada violação tolerada
  (`import sqlalchemy` fora do allowlist etc.) com `remove_at_phase`; falha se surgir violação nova
  ou entrada vencida. *Verif.: `pytest -q tests/test_structure_guards.py`.* Deps: T1. **M**
- [ ] **T5 · Baseline de cobertura por pacote** — `docs/refactor/coverage-baseline.md` com % por
  pacote hoje e projeção para `creator.core + creator.modules + creator.api` (prova de que o swap
  de `--cov` em T51 não derruba o gate de 80%). *Verif.: comando reproduzível documentado.* Deps: T1. **XS**
- [ ] **T6 · Fingerprint do schema SQLAlchemy** — `tests/test_schema_fingerprint.py` compara dump
  canônico de `Base.metadata` (tabelas, colunas, índices, uniques, FKs) com
  `tests/fixtures/schema_fingerprint.json`. *Verif.: `pytest -q tests/test_schema_fingerprint.py`.*
  Deps: T1. **S**
- [ ] **T7 · `core/models_registry.py` + repoint das migrações (PR isolado)** — criar
  `src/creator/core/models_registry.py` (importa `legacy_schema` primeiro, depois models por
  módulo); apontar `migrations/env.py` e `migrations/versions/0001_sqlite_baseline.py` para o
  registry. **Nenhum model se move neste PR** (mitiga R1). *Verif.: `alembic upgrade head` em DB
  vazio + `alembic check` + fingerprint idêntico.* Deps: T6. Arquivos: 4. **M**
- [ ] **T8 · Teste de resolução dos paths RQ** — `tests/test_job_paths.py` resolve via `importlib`
  cada string de `infrastructure/runtime/queue.py` + `_PIPELINE_HANDLERS`. *Verif.:
  `pytest -q tests/test_job_paths.py`.* Deps: T1. **S**
- [ ] **T9 · Política de janela de merge e rollback** — `docs/refactor/README.md`: ordem de PRs,
  congelamento de `main.py` na fase 1, formato de branch, rollback por fase. Deps: T1. **XS**
- [ ] **T10 · Extrair `creator/core/config.py` com shim** — mover `config.py` → `core/config.py`,
  shim reexportando `Settings`/`get_settings`; atualizar imports de migrations. *Verif.: `make
  check`; identidade `creator.config.get_settings is creator.core.config.get_settings`.* Deps: T7. **M**
- [ ] **T11 · `make refactor-guards` e job de CI** — target agregador (lint-imports + T3 + T4 + T6
  + T8) e job `refactor-guards` no `ci.yml`. *Verif.: `make refactor-guards` verde; job no CI.*
  Deps: T2, T3, T4, T6, T8. **S**

**Checkpoint C0:** `make check` + `make security` + `make e2e` + `make refactor-guards` +
`alembic upgrade head && alembic check` (DB vazio) + `git diff --exit-code docs/openapi.yaml`.
222 operações na fixture; baseline import-linter documentado; **nenhuma** movimentação de
model/rota. ✅ Revisão humana antes da fase 1.

### Fase 1 — Rotas e DTOs por módulo (222 handlers)

Regras da fase: **um módulo por PR**; rota + serializer + DTO movem juntos (R8); `docs/openapi.yaml`
sem diff em todo PR; fixture T3 inalterada; billing por último; `main.py` congelado para não-PRs
da fase (R13).

- [ ] **T12 · Casca `api/`** — criar `api/router.py` (agregador, prefixo `/api/v1`), `api/errors.py`
  (3 exception handlers), `api/openapi.py` (`OPENAPI_TAGS` + `install_openapi_patches`, aplicado
  após todos os include_router); `create_app()` passa `settings` como argumento para preservar o
  monkeypatch de `test_openapi_contract.py`. *Verif.: testes de contrato + fixture verdes sem
  edição.* Deps: T11. Arquivos: 4. **M**
- [ ] **T13 · Módulo `auth`** (5 rotas) — `api/routes/auth.py` → `modules/auth/router.py`; 4 DTOs →
  `schemas.py` (CreatorDTO); remover `api/routes/`. *Verif.: fixture idêntica; e2e auth verde.*
  Deps: T12. **M**
- [ ] **T14 · Módulo `users`** (6 rotas, incl. `/users/me`) — com `_user_data` e serializers; teste
  de serializers migra junto. Deps: T13. **M**
- [ ] **T15 · Módulo `workspaces` pt. 1** (workspace + memberships, ~9 rotas) — authz de workspace
  em `dependencies.py`. Deps: T14. **M**
- [ ] **T16 · Módulo `workspaces` pt. 2** (invites + usage, ~8 rotas) — remove DTOs soltos
  `workspace_invite_*` de `api/dtos/`. Deps: T15. **M**
- [ ] **T17 · Módulo `brands` pt. 1** (Brand CRUD + settings, ~10 rotas). Deps: T16. **M**
- [ ] **T18 · Módulo `brands` pt. 2** (cores, assets, knowledge, ~9 rotas) — remove DTOs soltos
  `brand_color_*`. Deps: T17. **M**
- [ ] **T19 · Módulo `contents` pt. 1** (CRUD + paginação, ~10 rotas) — `_page_data` sai de
  `main.py`. Deps: T18. **M**
- [ ] **T20 · Módulo `contents` pt. 2** (geração de texto/imagem, melhoria, ~10 rotas) — deps
  `get_llm_provider`/`get_generation_queue` continuam em `api/dependencies.py`. *Verif.: `make e2e`.*
  Deps: T19. **M**
- [ ] **T21 · Módulo `generations`** (9 rotas). Deps: T20. **S**
- [ ] **T22 · Módulo `agent_workflows`** (4 rotas, URL `/generations/image-workflows*` preservada
  literalmente). Deps: T21. **M**
- [ ] **T23 · Módulo `design`** (5 rotas) — remove DTO solto `design_structure_create`. Deps: T22. **S**
- [ ] **T24 · Módulo `marketing` pt. 1** (campaigns + plannings, ~10 rotas). Deps: T23 + OQ-2. **M**
- [ ] **T25 · Módulo `marketing` pt. 2** (personas + post structures, ~10 rotas). Deps: T24. **M**
- [ ] **T26 · Módulo `notifications` pt. 1** (notifications + preferences + recipients, ~10 rotas).
  Deps: T25. **M**
- [ ] **T27 · Módulo `notifications` pt. 2** (user-devices + usage, ~10 rotas). Deps: T26. **M**
- [ ] **T28 · `billing` router pt. 1** (accounts, addresses, payment methods, subscriptions, ~25
  rotas) — início do `schemas.py` a partir dos 31 DTOs de `api/dtos/billing/`. Deps: T27. **M**
- [ ] **T29 · `billing` router pt. 2** (invoices, charges, coupons, redemptions, ~25 rotas). Deps: T28. **M**
- [ ] **T30 · `billing` router pt. 3** (provider*, webhooks, idempotency, ~25 rotas) — resolve o PUT
  duplicado de provider-subscriptions conforme OQ-5. Deps: T29. **M**
- [ ] **T31 · `billing` router pt. 4** (credits, orders, refunds, workspace-credit-transactions,
  ~24 rotas) — esvazia `api/dtos/billing/`. *Total billing: 99 rotas.* Deps: T30. **M**
- [ ] **T32 · Limpeza da fase 1 + guarda do main.py** — remover `api/dtos/` e `api/routes/`;
  decidir alias `/content/{id}` (OQ-5); `/health*`+`/metrics` → `api/system.py`; guarda: `main.py`
  < 300 linhas, 0 rotas de negócio, 222 operações no agregador. Deps: T31. **M**

**Checkpoint C1:** gates padrão + `git diff --exit-code docs/openapi.yaml` + `wc -l main.py` < 300
+ fixture com 222 operações e operationIds idênticos + `git diff --exit-code CONTEXT.md`.

### Fase 2 — Application → `service.py` + `ports.py`, quebra de ciclo, cobertura

- [ ] **T33 · `event_publisher` → `core/outbox/dispatcher.py`** — quebra o ciclo
  `application ⇄ services` ANTES de tocar services; shim em `services/agents/`. Deps: T32. **S**
- [ ] **T34 · `core/uow.py`** — `UnitOfWorkProtocol` (4 métodos) + `UnitOfWorkBase`;
  `application/unit_of_work.py` vira shim do protocol de 47 atributos até a fase 3. Deps: T33. **S**
- [ ] **T35 · `core/pagination.py`** — `Page`/`PageRequest` de `repositories/common.py`, com shim.
  Deps: T34. **S**
- [ ] **T36 · Ports pt. 1** (auth, users, workspaces, brands) — Protocols + Records de
  `repositories/*` → `modules/*/ports.py`; fachada `repositories/__init__.py` reexporta (shim).
  *ports.py sem sqlalchemy/pydantic.* Deps: T35. **M**
- [ ] **T37 · Ports pt. 2** (contents, generations, agent_workflows, design) — inclui
  `GenerationQueue` Protocol (hoje inline em `application/image_generation.py`). Deps: T36. **M**
- [ ] **T38 · Ports pt. 3** (marketing, notifications). Deps: T37. **M**
- [ ] **T39 · Ports pt. 4** (billing, 32 Protocols) — fatiar em 2 PRs se > ~1.200 linhas.
  *Verif.: contagem de Protocols igual à atual.* Deps: T38. **M**
- [ ] **T40 · `core/outbox/ports.py`** — de `repositories/outbox.py`, com shim. Deps: T39. **S**
- [ ] **T41 · `modules/auth/service.py`** — `application/auth.py` + `auth_ports.py` +
  `auth_types.py` → service/ports; códigos de erro preservados. *Verif.: e2e de cookie verde.*
  Deps: T40. **M**
- [ ] **T42 · `contents` services pt. 1** (geração de texto + melhoria) — services recebem ports,
  não UoW. Deps: T41. **M**
- [ ] **T43 · `contents` services pt. 2** (imagem + storage de artefato) — enqueue usa o mesmo path
  RQ (T8 verde). Deps: T42. **M**
- [ ] **T44 · `agent_workflows/service.py`** — `application/agent_image_workflow.py` +
  `services/agents/{pipeline,runner,factory,errors}`; `crewai_adapter` atrás de port; `contracts`
  → `core/providers/agent_runtime/ports.py`. Deps: T43. **M**
- [ ] **T45 · Services de `users` + `workspaces`** — extrair lógica dos handlers; router só
  valida/ delega/ responde. Deps: T44. **M**
- [ ] **T46 · Services de `brands` + `design`**. Deps: T45. **M**
- [ ] **T47 · Services de `marketing`**. Deps: T46. **M**
- [ ] **T48 · Services de `notifications`**. Deps: T47. **M**
- [ ] **T49 · Services de `billing` pt. 1** (contas, assinaturas, faturas) — idempotência e ledger
  com testes de unidade. Deps: T48. **M**
- [ ] **T50 · Services de `billing` pt. 2** (provider sync/audit, webhooks, créditos). Deps: T49. **M**
- [ ] **T51 · Trocar alvo de cobertura** — `pyproject.toml` → `--cov=creator.core
  --cov=creator.modules` (alvos antigos só enquanto houver shims); atualizar baseline T5.
  *Verif.: gate 80% verde.* Deps: T50. **S**

**Checkpoint C2:** gates padrão + `lint-imports` sem ciclos + `import sqlalchemy` restrito ao
allowlist + cobertura ≥80% nos novos alvos + routers sem acesso direto a repositories.

### Fase 3 — Persistência, models e UoW mixins (fase mais arriscada)

- [ ] **T52 · 🛑 REVISÃO HUMANA pré-fase 3 (gate)** — checklist no PR: fingerprint idêntico,
  `alembic heads` único, registry em uso, plano de remoção de `_schema_models`, snapshot do UoW de
  47 atributos, semântica da migration 0001 preservada. **Nenhum model se move sem aprovação.**
  Deps: T51. **XS**
- [ ] **T53 · `core/persistence/{types,legacy_schema}.py`** — mover `schema_models.py` (638) e
  `models/types.py`; atualizar registry + migrations. *Nunca renomear tabela/coluna (R1).*
  Deps: T52. **M**
- [ ] **T54 · Models de `users` + `workspaces`** — `user.py` → `modules/users/models.py`;
  `workspace.py`, `workspace_membership.py`, `settings.py` → `modules/workspaces/models.py`
  (Settings → workspaces é a decisão padrão; ver OQ-1). Deps: T53. **M**
- [ ] **T55 · Models de `auth`** — `auth_session.py` → `modules/auth/models.py`. Deps: T54. **S**
- [ ] **T56 · Models de `brands`** — `brand/`, `brand_knowledge.py`. Deps: T55. **S**
- [ ] **T57 · Models de `contents`** — `content/`, `assets/`, `project/` (Project → contents,
  OQ-1). Deps: T56 + OQ-1. **M**
- [ ] **T58 · Models de `generations`** — `generation/` (3 arquivos). Deps: T57. **S**
- [ ] **T59 · Models de `agent_workflows`** — `workflow/` (runs, steps). Deps: T58. **S**
- [ ] **T60 · Models de `marketing`** — tabelas legadas de campaign/planning/persona/post_structure
  (hoje só em `legacy_schema`); models.py pode nascer vazio com documentação. Deps: T59 + OQ-2. **M**
- [ ] **T61 · Models de `billing`, `notifications`, `design`** — `models/credits.py` → billing;
  concluir remoção de `infrastructure/database/models/`. Deps: T60. **M**
- [ ] **T62 · Remover imports `_schema_models` (lote 1)** — 15 models fazem
  `import schema_models as _schema_models # noqa` só para FK; trocar por ordem garantida do
  registry. Deps: T61. **M**
- [ ] **T63 · Remover `_schema_models` (lote 2) + guarda** — `grep -r "_schema_models" src` → 0;
  guarda no structure_guards. Deps: T62. **M**
- [ ] **T64 · UoW mixins pt. 1** (auth, users, workspaces, brands) — `*Repositories` com
  `bind(uow, session)` em `persistence.py`. Deps: T63. **M**
- [ ] **T65 · UoW mixins pt. 2** (contents, generations, agent_workflows, design). Deps: T64. **M**
- [ ] **T66 · UoW mixins pt. 3 + `src/creator/uow.py`** — marketing, notifications, billing +
  composition root (12 mixins sobre UnitOfWorkBase; snapshot de 47 atributos idêntico). Deps: T65. **M**
- [ ] **T67 · Persistência: `core.py` pt. 1** — fatiar `persistence/repositories/core.py` (2.574
  linhas, 11 classes): User, Settings, Workspace, Brand, Project → `modules/*/persistence.py` com
  shims. Deps: T66. **M**
- [ ] **T68 · Persistência: `core.py` pt. 2** — Content, Generation, Asset, BrandSettings,
  AgentWorkflow, ImageGeneration → módulos; `core.py` removido. Deps: T67. **M**
- [ ] **T69 · Persistência dos demais adapters** — 18 arquivos restantes → `modules/*/persistence.py`
  + `core/outbox/persistence.py`; `infrastructure/persistence/` deixa de existir; UoW antigo
  substituído por `creator.uow`. Deps: T68. **M**

**Checkpoint C3:** gates padrão + `alembic upgrade head` (DB vazio) + `alembic check` limpo +
fingerprint idêntico + `infrastructure/database/models` inexistente + sqlalchemy só no allowlist +
`test_app_structure.py` reescrito no mesmo PR do move final.

### Fase 4 — Providers, prompts, workers, shims e limpeza

- [ ] **T70 · Fundir os dois adapters Gemini** — `services/ai/gemini.py` + `integrations/gemini/*`
  → `core/providers/llm/{client,image_generator,image_reviewer,errors}.py` (fonte da verdade:
  OQ-3). Deps: T69 + OQ-3. **M**
- [ ] **T71 · `core/providers/{storage,retrieval,agent_runtime}` + `core/queue` + cookies** —
  mover `services/storage`, `services/retrieval`, `crewai_adapter`, `runtime/{queue,storage,
  rate_limit}`; consolidar `auth_cookie_policy.py` + `api/auth/cookies.py` →
  `core/security/cookies.py` (OQ-4). *Verif.: e2e de cookie verde; `services/` inexistente.*
  Deps: T70 + OQ-4. **M**
- [ ] **T72 · Prompts** — `prompts/base.py` → `core/providers/llm/prompts.py`;
  `improvement/image/agents/content` → `modules/*/prompts/`. Deps: T71. **M**
- [ ] **T73 · `agent_workflows/tasks.py`** — `workers/agent_workflow.py` (1.249 linhas) → tasks +
  service, sem alterar path de job. Deps: T72. **M**
- [ ] **T74 · `contents/tasks.py` + `core/outbox/tasks.py`** — `workers/image_generation.py` e
  `workers/pipeline_events.py` (8 paths preservados). Deps: T73. **M**
- [ ] **T75 · `workers/cli.py` estável + shims de jobs** — entrypoint `creator-worker` intacto;
  shims `creator/workers/*.py` reexportando os callables novos (R2), com data de remoção.
  *Verif.: `creator-worker --help`; T8 verde para paths antigos e novos.* Deps: T74. **S**
- [ ] **T76 · Remover shims legados + reescrever guardas** — apagar `application/`, `repositories/`,
  `infrastructure/`, `services/`, `integrations/`, `domain/`, `prompts/`; reescrever
  `test_app_structure.py`; atualizar `tests/e2e/conftest.py`. *Drenar fila RQ antes (R2).*
  Deps: T75 + OQ-7. **M**
- [ ] **T77 · Atualizar ADR, tracker e issues de encerramento** — ADR-0023 com resultado real,
  issues fechadas com evidência de CI, `docs/status-do-projeto.md` atualizado. *Verif.:
  `git diff --exit-code CONTEXT.md`.* Deps: T76. **S**
- [ ] **T78 · Verificação final ponta-a-ponta** — suíte completa + Compose saudável (api, worker,
  redis, sqlite volumes) + `/health/live` 200 + fingerprint idêntico ao baseline. Deps: T77. **XS**

**Checkpoint C4 (final):** gates padrão + `lint-imports` com **0 ignores restantes** + alembic
limpo + fingerprint idêntico + 222 operações com operationIds idênticos + `docs/openapi.yaml` sem
diff + `main.py` < 300 linhas + `CONTEXT.md` sem diff.

---

## Risks and Mitigations

| ID | Risco | Impacto | Mitigação |
|---|---|---|---|
| R1 | `0001_sqlite_baseline.py` usa `Base.metadata.create_all()` (metadata vivo) | Schema da revisão base muda ao mover model | T6 fingerprint antes; T7 registry em PR isolado; `alembic check` em cada PR da fase 3; nunca renomear tabela/coluna |
| R2 | Paths RQ em string (`creator.workers.*`) persistidos no Redis | Jobs em fila/retry quebram silenciosamente | T8 teste desde a fase 0; shims em T75 por 1 release; drenar fila antes de remover (T76) |
| R3 | `--cov` fixo em pacotes que serão movidos (`pyproject.toml`) | Gate de 80% mede nada / quebra | T5 baseline; T51 troca alvo com folga; alvos antigos só saem com o shim |
| R4–R6 | `test_app_structure.py`, `test_main_serializers.py`, `test_openapi_contract.py` fixam caminhos atuais | CI quebra na fase errada / teste fica vácuo-verde | T4 baseline por fase; reescrever cada teste **no PR do move**; T12 preserva monkeypatch de `get_settings` |
| R7 | UoW com 47 atributos em 3 arquivos centrais | Ponto único de colisão de todas as features | T34 protocolo de 4 métodos; T64–T66 mixins; snapshot de atributos como teste |
| R8 | Serializers `_*_data` e 128 commits em `main.py` | Movimento separado da rota quebra contrato | Cada PR de módulo move rota + serializer + DTO juntos |
| R9 | `get_settings()` fora do DI (`main.py:1506`) | Testes não conseguem sobrescrever | `create_app` continua dono da resolução; injeta `settings` em `install_openapi_patches` |
| R10 | `app = create_app()` no import + engine singleton | Reordenar imports muda startup/alembic | Comportamento congelado até T78; decisão explícita (OQ-6) |
| R11 | 15 models importam `schema_models` só para FK | Ordem de carregamento frágil; `NoReferencedTableError` em runtime | Registry importa `legacy_schema` primeiro (T7/T53); remoção em T62/T63 com fingerprint |
| R12 | `docs/openapi.yaml` (10.182 linhas) mantido à mão | Contrato diverge sem ninguém notar | T3 fixture + `git diff --exit-code` em todo PR da fase 1 |
| R13 | PRs grandes em `main.py` na fase 1 | Conflitos constantes | Um módulo por PR; billing por último; janela de merge (T9) |
| R14 | Testes/e2e importam caminhos internos (`api.dependencies`) | PR que move símbolo quebra e2e | Regra "mesmo PR atualiza testes e imports"; shims em T10/T34/T35 |
| R15 | DTOs que violam `CreatorDTO` (22 módulos com BaseModel puro) | Inconsistência se multiplica na consolidação | Schemas novos sempre `CreatorDTO`; verificação em T28+ |
| R16 | Duplicação Gemini e cookies | Comportamento divergente após consolidação | T70/T71 fundem com decisão registrada (OQ-3/OQ-4) |
| R17 | `CONTEXT.md` alterado acidentalmente | Perda de vocabulário de domínio | `git diff --exit-code CONTEXT.md` em C1–C4 |

## Open Questions

| # | Questão | Bloqueia | Padrão adotado no plano |
|---|---|---|---|
| OQ-1 | `Project` e assets: `contents` ou módulo próprio? | T57, T60 | Project → `contents` (CONTEXT.md: Workspace owns "Projects, Content") |
| OQ-2 | Campaign/Persona/Planning/PostStructure: todos em `marketing`? | T24, T25, T60 | Sim, módulo `marketing` próprio (nunca fundir em `design`) |
| OQ-3 | Ao fundir Gemini, qual adapter é a fonte de verdade? | T70 | Fundir mantendo comportamento mais completo; revisão em PR |
| OQ-4 | `auth_cookie_policy.py` vs `api/auth/cookies.py`: qual comportamento prevalece? | T71 | Consolidar preservando o comportamento testado pelo e2e de cookie |
| OQ-5 | Alias `GET /content/{id}` e PUT duplicado de provider-subscriptions: remover (breaking) ou preservar? | T30, T32 | Preservar na fase 1 (contrato intocado); decidir remoção em ADR próprio |
| OQ-6 | `app = create_app()` no import + engine singleton: manter ou lazy? | T78 | Manter comportamento; lazy é decisão separada pós-refactor |
| OQ-7 | Vida dos shims: remover na mesma release ou após tag publicada? | T76 | Após 1 release com fila drenada |

## Validation Strategy

- **Fase 0:** `make check && make security && make e2e && make refactor-guards`; `alembic upgrade head` (DB vazio) + `alembic check`.
- **Fase 1:** + `git diff --exit-code docs/openapi.yaml` + `pytest -q tests/test_route_inventory.py` (222 operações) + `wc -l src/creator/main.py` < 300.
- **Fase 2:** + `pytest --cov=creator.core --cov=creator.modules --cov-fail-under=80` + `lint-imports` + allowlist de sqlalchemy.
- **Fase 3:** + fingerprint de schema idêntico + snapshot de 47 atributos do UoW.
- **Fase 4:** + `pytest -q tests/test_job_paths.py` + `creator-worker --help` + `docker compose up -d --build --wait` + `curl /health/live` + `grep -rn "creator.(application|infrastructure|repositories|services|integrations)" src tests` → 0.

**Critérios globais de fim:** contrato HTTP idêntico (paths, métodos, operationIds, tags, códigos);
schema idêntico; `main.py` < 300 linhas sem rotas de negócio; `core` não importa `modules`;
cross-módulo só via `public.py`; sqlalchemy só no allowlist; cobertura ≥80% em `core+modules`;
`CONTEXT.md` inalterado.

## Handoff sugerido

- **`coder`**: executar T1–T11 (fase 0) em branch `refactor/fase-0-fundacao` a partir de `dev`,
  um PR por tarefa, evidência de CI anexada ao issue.
- **`tester`**: no PR de T11 (gates) e em C3/T69 (snapshot UoW + fingerprint).
- **`reviewer`** (`code-review-and-quality`): revisar PR de T52 (gate humano) e T76 (remoção de shims).
