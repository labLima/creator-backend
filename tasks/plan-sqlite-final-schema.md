# Plano de implementação: alinhamento ao Creator_DB_final.sql

> Gerado com a skill `planning-and-task-breakdown` e apoio do agente `planner`.
> A saída bruta do planner foi revisada e corrigida contra o repositório: ela citava tabelas
> inexistentes no modelo final (`roles`, `media_files`, `generation_requests` etc.), ADR-022/023
> (já ocupadas) e a issue local 0050 (já usada). Este documento substitui aquela versão.
> Números e listas vêm de `docs/migration/schema-final-alignment.md`, regenerável por
> `python scripts/schema_parity_report.py`.

## Overview

Fazer o schema vivo (metadata SQLAlchemy + Alembic, SQLite) coincidir com a modelagem final
`docs/migration/Creator_DB_final.sql`: **54 tabelas, 52 enums, 173 índices, 101 foreign keys,
80 CHECK constraints**. O delta verificado é 18 tabelas a criar, 31 a alinhar, 1 rename simples
e 4 redesenhos de modelo. A migração PostgreSQL→SQLite **já está concluída** (ADR-021,
`0001_sqlite_baseline.py`, `migrations/legacy_postgres/`, compose com
`sqlite+pysqlite:////data/creator.db`) e não é reescopada aqui.

A execução é incremental: revisões Alembic encadeadas a partir da head atual
(`0005_content_text_versions`), cada PR verde, cada mudança de schema acompanhada da
regeneração de `tests/contracts/schema_tables.json` e `tests/contracts/schema_ddl.sql`. No fim,
as revisões são consolidadas numa baseline única regenerada, já que o banco é pré-produção.

## Decisões de arquitetura

1. **Revisões incrementais agora, baseline única no fim.** Durante o trabalho, cada fase é uma
   revisão Alembic a partir de `0005_content_text_versions`. A fase 6 regenera
   `0001_sqlite_baseline` do metadata final e remove as revisões intermediárias — proibido
   enquanto existir banco com dados a preservar. A decisão e a condição que a inverte vão para
   a **ADR-028**, porque é irreversível para quem já tem volume.
2. **`create_all` define o schema; Alembic cobre bancos existentes.** A baseline é
   `Base.metadata.create_all()`, então uma mudança só nas models cria a tabela em banco novo mas
   deixa banco antigo defasado, e `alembic check` acusa. Regra: **model + revisão no mesmo PR**.
3. **Expand → backfill → contract para os 4 redesenhos**, nunca no mesmo PR. Expand cria as
   tabelas novas ao lado das antigas; backfill copia dados; contract remove as antigas. O
   rollback de cada etapa é o `downgrade` da própria revisão.
4. **Teste de paridade mora em `tests/test_schema_inventory.py`**, junto dos fixtures congelados,
   para não existir um segundo parser de DDL. Ele ganha `tests/contracts/creator_db_final.sql`
   (cópia de `docs/migration/Creator_DB_final.sql`, com sha256 verificado no teste) e asserta
   seis dimensões contra `Base.metadata`: conjunto de tabelas (54 finais + 4 extensões
   declaradas), colunas por tabela, nullability e tamanho de coluna, vocabulário de enum,
   índices (nome, colunas ordenadas, unicidade) e foreign keys (colunas, alvo, `ON DELETE`).
   As falhas agregam todas as divergências com contagem por categoria.
5. **Nomes de índice são contrato.** O snapshot DDL precisa ser determinístico e 123 dos 173
   índices do dump são anônimos. Convenção obrigatória: `ix_<tabela>_<colunas>` e
   `uq_<tabela>_<colunas>`, registrada em ADR-028; índice anônimo no dump recebe nome na
   metadata e o mapeamento fica documentado no próprio teste.
6. **`make snapshot-contract` é gate de toda PR que muda schema**, na mesma PR, com o diff dos
   dois fixtures revisado. O diff é a evidência auditável da mudança; separar em outra PR quebra
   a rastreabilidade e desaparece com a revisão.
7. **Portabilidade de constraints é trabalho explícito, não detalhe.** SQLite não aceita:
   `ALTER TABLE ... ADD CONSTRAINT` (as 101 FKs precisam estar nas models, e 10 são **compostas
   com `workspace_id`**, exigindo UNIQUE composta no alvo); regex PostgreSQL `~` (15 CHECKs de
   moeda) nem `num_nonnulls` (3 CHECKs). Helpers em `creator/infrastructure/database/`
   traduzem para `GLOB`/`LIKE`/`length`+`upper` e para soma de `CASE WHEN ... IS NOT NULL`, com
   teste de equivalência por constraint. `gen_random_uuid()` vira default Python `uuid4` e
   `now()` vira `CURRENT_TIMESTAMP`/helper UTC.
8. **Enums: 52 tipos, vocabulário 1:1.** `Enum(native_enum=False, create_constraint=True)` ou
   `String` + `CHECK`, num módulo único de constantes importado pelas models
   (`<entity>/models.py` e `creator/infrastructure/database/` podem importar; router, schemas,
   service e ports não).
9. **Aposentadoria do legado em ADR-029**, com mapeamento tabela→alvo, ordem de remoção e
   verificação de consumidores. Tabela retida precisa de justificativa e prazo escritos.
10. **Rastreabilidade**: ADR-028 e ADR-029 em `docs/adr/`, indexadas em
    `docs/ADR-ISSUE-TRACKER.md`; épico local
    [0057](../docs/issues/0057-sqlite-final-schema-alignment.md) e issue
    [#159](https://github.com/labLima/creator-backend/issues/159); issues filhas no board `SHC`
    do Shared Context, uma por tarefa (cada uma declara o workspace
    `/home/emanueljtrodrigues/Documents/LeFil/creator-backend`). `docs/openapi.yaml` é
    atualizado antes de qualquer mudança de payload HTTP (membership status, posts com
    aprovação/agendamento, créditos).

## Fase 0 — Contrato, paridade e portabilidade

### T1 — ADR-028, épico e tracker

**Descrição:** Registrar a estratégia de alinhamento (incrementais + squash final, expand→backfill→contract, teste de paridade em `tests/test_schema_inventory.py`, convenção de nomes de índice, gate `make snapshot-contract`, política de enums e de constraints portáveis) e amarrar a rastreabilidade do épico 0057 / #159 às ADR-021 e ADR-015.

**Critérios de aceite:**
- [ ] `docs/adr/0028-sqlite-final-schema-alignment.md` aceita, cobrindo as decisões 1–8.
- [ ] `docs/ADR-ISSUE-TRACKER.md` lista ADR-028 com tracker e issues de implementação.
- [ ] Épico [0057](../docs/issues/0057-sqlite-final-schema-alignment.md) aponta para o plano e para as issues filhas.
- [ ] `tasks/plan.md` e `tasks/todo.md` (históricos) permanecem intocados.

**Verificação:**
- [ ] `python scripts/schema_parity_report.py` sem erro e relatório commitado.
- [ ] `git diff --exit-code tests/contracts/` (fase sem mudança de schema).

**Dependências:** Nenhuma
**Arquivos prováveis:** `docs/adr/0028-sqlite-final-schema-alignment.md`, `docs/ADR-ISSUE-TRACKER.md`, `docs/issues/0057-sqlite-final-schema-alignment.md`
**Tamanho:** S

### T2 — Teste de paridade contra o DDL final

**Descrição:** Copiar o dump final para `tests/contracts/creator_db_final.sql` e adicionar ao módulo de inventário as asserções de paridade (tabelas, colunas, nullability/tamanho, vocabulário de enum, índices e FKs), com as 4 extensões de ADR declaradas como exceção e falha agregada por categoria. O teste nasce vermelho com o delta atual — é o contrato do plano.

**Critérios de aceite:**
- [ ] Fixture versionada com sha256 conferido no teste.
- [ ] `test_final_table_set`, `test_final_columns`, `test_final_nullability_and_lengths`, `test_final_enum_vocabulary`, `test_final_indexes`, `test_final_foreign_keys` no mesmo módulo.
- [ ] Exceções declaradas em constante única (`ADR_EXTENSIONS`, `LEGACY_RETENTION`), não em `if`s espalhados.
- [ ] Testes antigos (`test_metadata_table_set_is_exact`, `test_ddl_is_byte_identical`) continuam verdes.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` vermelho apenas nas asserções novas, com relatório de 18 ausentes e 31 divergentes.
- [ ] `XDG_DATA_HOME=$PWD/.local/xdg make check PYTHON=.venv/bin/python` falha só nesse arquivo.

**Dependências:** T1
**Arquivos prováveis:** `tests/test_schema_inventory.py`, `tests/contracts/creator_db_final.sql`
**Tamanho:** M

### T3 — Helpers portáveis de coluna, enum e índice

**Descrição:** Centralizar em `creator/infrastructure/database/` os tipos e fábricas que as models passarão a usar: PK UUID (CHAR(32)), timestamps UTC, JSON, enum portátil, índices nomeados na convenção `ix_/uq_`, além das 52 constantes de enum extraídas do dump.

**Critérios de aceite:**
- [ ] `uuid_pk()`, `utc_timestamp()`, `json_column()`, `enum_column(enum_cls)`, `index_name()`, `unique_index_name()` disponíveis.
- [ ] Inventário dos 52 enums com nome e valores.
- [ ] Nenhum import de `sqlalchemy` fora de `models.py`, `repository.py` e `creator/infrastructure/database/`.

**Verificação:**
- [ ] `pytest tests/test_module_boundaries.py -q`.
- [ ] `grep -rn "JSONB\|PGUUID\|gen_random_uuid" src/creator` sem resultados.
- [ ] `git diff --exit-code tests/contracts/`.

**Dependências:** T1
**Arquivos prováveis:** `src/creator/infrastructure/database/columns.py`, `src/creator/infrastructure/database/enums.py`
**Tamanho:** S

### T4 — Portabilidade das CHECK constraints e defaults

**Descrição:** Traduzir as 80 CHECKs do dump final para expressões válidas em SQLite, com helpers testados: 15 regex de moeda (`currency ~ '^[A-Z]{3}$'`), 3 `num_nonnulls(...)` e os predicados com `NOT is_current`. Definir o mapa de defaults (`gen_random_uuid()`→`uuid4`, `now()`→`CURRENT_TIMESTAMP`).

**Critérios de aceite:**
- [ ] Helpers `currency_code_check(coluna)`, `exactly_one_of(*colunas)`, `at_most_one_of(*colunas)` geram SQL portável.
- [ ] Teste de equivalência semântica por helper (aceita e rejeita os mesmos casos que a expressão PostgreSQL).
- [ ] Nenhum `~`, `num_nonnulls` ou `gen_random_uuid` em model ou migration.

**Verificação:**
- [ ] `pytest tests/test_portable_schema.py tests/test_schema_inventory.py -q`.
- [ ] `grep -rn "num_nonnulls\| ~ '" src migrations` sem resultados.

**Dependências:** T3
**Arquivos prováveis:** `src/creator/infrastructure/database/constraints.py`, `tests/test_portable_schema.py`
**Tamanho:** M

### Checkpoint — Fase 0
- [ ] ADR-028 aceita e tracker consistente.
- [ ] Teste de paridade roda e reporta o delta esperado (18 ausentes, 31 divergentes).
- [ ] Helpers de constraint com teste de equivalência.
- [ ] Revisão humana da ADR-028 antes da fase seguinte.

## Fase 1 — Criar tabelas sem dependência de redesenho

### T5 — Conformidade, consentimento e interesses

**Descrição:** Criar `audit_logs`, `user_consents` e `persona_interests` com models, repositórios mínimos e revisão `0006_*`.

**Critérios de aceite:**
- [ ] Colunas, nullability, FKs (`ON DELETE` iguais ao dump) e índices conforme o modelo final.
- [ ] `user_consents` com UNIQUE por (user, type, document_version); `audit_logs` só append.
- [ ] Revisão com `downgrade` funcional; fixtures de snapshot regenerados.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` → 15 tabelas ausentes.
- [ ] `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
- [ ] `python scripts/check_migrations.py`.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/audit/models.py`, `src/creator/user/models.py`, `src/creator/persona/models.py`, `migrations/versions/0006_*.py`
**Tamanho:** S

### T6 — Satélites de Brand e Campanha

**Descrição:** Criar `brand_business_details`, `brand_hashtags`, `brand_values`, `campaign_hashtags` e `campaign_voices`, com unicidade de hashtag/valor por pai e FKs em cascata.

**Critérios de aceite:**
- [ ] Cinco tabelas com colunas e UNIQUE do dump.
- [ ] FKs com `ON DELETE` idêntico ao dump; índices nomeados.
- [ ] Revisão `0007_*` com downgrade; fixtures regenerados.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` → 10 ausentes.
- [ ] `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/brand/models.py`, `src/creator/campaign/models.py`, `migrations/versions/0007_*.py`
**Tamanho:** M

### T7 — Satélites de Billing e Créditos

**Descrição:** Criar `plan_payment_methods`, `charge_transactions`, `fiscal_invoices`, `workspace_credit_lots` e `workspace_credit_lot_consumptions`, com ledger de consumo ligado a lote e sem dupla contagem.

**Critérios de aceite:**
- [ ] CHECKs de status e de sinais (`original_amount > 0`, `remaining_amount` entre 0 e original) portáveis.
- [ ] `workspace_credit_lot_consumptions` referencia lote e transação; UNIQUE composta conforme dump.
- [ ] `fiscal_invoices` guarda metadados e referências; nenhum SDK de provider importado.
- [ ] Revisão `0008_*` com downgrade; fixtures regenerados.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` → 5 ausentes.
- [ ] `grep -rn "import stripe\|import mercadopago" src/creator` sem resultados.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/billing/models.py`, `src/creator/credit/models.py`, `migrations/versions/0008_*.py`
**Tamanho:** M

### Checkpoint — Fase 1
- [ ] 13 das 18 tabelas novas criadas; paridade acusa 5 ausentes.
- [ ] `make check` verde com fixtures atualizados.
- [ ] `alembic upgrade head` em banco vazio e `downgrade base` sem erro.

## Fase 2 — Renomear e redesenhar (expand)

### T8 — Renomear `workspace_memberships` → `workspace_members`

**Descrição:** Único rename viável: adicionar `status` e `invited_by`, remover `deleted_at`, preservar UNIQUE(workspace_id, user_id), renomear índices na convenção e atualizar repositório, autorização e testes.

**Critérios de aceite:**
- [ ] Tabela e índices renomeados; colunas e enum `member_status` conforme dump.
- [ ] Nenhuma referência ao nome antigo em `src`, `tests`, `migrations`.
- [ ] Remoção do soft delete documentada (remoção de vínculo é exclusão).
- [ ] Revisão `0009_*` com downgrade; fixtures regenerados.

**Verificação:**
- [ ] `grep -rn "workspace_memberships" src tests migrations scripts` sem resultados.
- [ ] `pytest tests/ -q -k "workspace or member"` verde.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/workspace/models.py`, `src/creator/workspace/repository.py`, `migrations/versions/0009_*.py`
**Tamanho:** S

### T9 — `planning` → `content_plans` + satélites

**Descrição:** Expand do redesenho de planejamento. Criar `content_plans` (11 colunas) e as satélites `content_plan_items` e `content_plan_special_dates`; a persona inline deixa de viver no plano e passa a apontar `personas`.

**Critérios de aceite:**
- [ ] `content_plans` com exatamente as 11 colunas e FKs do dump (brand, campaign, persona, created_by).
- [ ] `content_plan_items` (format, quantity) e `content_plan_special_dates` (special_date, label) com FK para o plano.
- [ ] `planning` permanece intacta (expand); repositório novo não reutiliza o legado.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` → 3 ausentes (`captions`, `design_slides`, `image_resizes`).
- [ ] `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/planning/models.py`, `src/creator/planning/repository.py`, `migrations/versions/0010_*.py`
**Tamanho:** M

### T10 — `post_structure` + `design_structure` → `posts`, `captions`, `post_designs`, `design_slides`

**Descrição:** Expand do redesenho editorial: `posts` com publicação e aprovação, textos versionados em `captions`, arte em `post_designs` (format/ratio) e slides ordenados em `design_slides`.

**Critérios de aceite:**
- [ ] `posts` com as 17 colunas, as 6 CHECKs de aprovação/agendamento e FKs do dump.
- [ ] `captions` com índice de versão corrente por post; `post_designs` com CHECK de STORIES↔RATIO_9_16; `design_slides` com posição ≥ 0.
- [ ] Tabelas antigas preservadas; `docs/openapi.yaml` atualizado antes de expor os campos novos.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` → 1 ausente (`image_resizes`).
- [ ] `pytest tests/ -q -k "post or design or caption"` verde.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/content/models.py`, `src/creator/design_structure/models.py`, `migrations/versions/0011_*.py`, `docs/openapi.yaml`
**Tamanho:** M

### T11 — `generated_image` → `generated_images` + `image_resizes`

**Descrição:** Expand do redesenho de mídia: 23 colunas com storage bucket/key, dimensões, proveniência, estado de geração, `is_current`, aprovação e feedback; redimensionamentos em `image_resizes`.

**Critérios de aceite:**
- [ ] `generated_images` com as 9 CHECKs do dump portadas (arquivo por status, aprovação, dimensões).
- [ ] `image_resizes` com UNIQUE (source_image_id, ratio) e CHECKs de arquivo, erro e dimensão.
- [ ] `is_current` com regra de unicidade por pai documentada.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` → 0 ausentes.
- [ ] `python scripts/check_migrations.py` e `make check`.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/generation/models.py`, `migrations/versions/0012_*.py`
**Tamanho:** M

### Checkpoint — Fase 2
- [ ] 18/18 tabelas novas criadas; paridade acusa 0 ausentes.
- [ ] As 4 tabelas antigas seguem vivas e verdes (expand puro).
- [ ] Revisão humana do diff de `tests/contracts/` de cada PR.

## Fase 3 — Backfill e contract

### T12 — Backfill dos 4 redesenhos

**Descrição:** Script idempotente que copia `planning`, `post_structure`, `design_structure` e `generated_image` para as tabelas novas, com relatório de contagens e invariantes; roda contra cópia do banco de dev.

**Critérios de aceite:**
- [ ] Duas execuções não duplicam linhas; relatório origem→destino por tabela.
- [ ] Invariantes: persona inline migrada ou já existente, data especial convertida, imagem sem `storage_key` marcada como pendente.
- [ ] Teste de integração em SQLite temporário cobre os 4 caminhos e o caso vazio.
- [ ] Script fora de `src/creator` e não importado pela aplicação.

**Verificação:**
- [ ] `pytest tests/test_backfill_redesigns.py -q`.
- [ ] Execução sobre `.local` com contagens conferidas.
- [ ] `git diff --exit-code tests/contracts/`.

**Dependências:** T8, T9, T10, T11
**Arquivos prováveis:** `scripts/backfill_redesigns.py`, `tests/test_backfill_redesigns.py`
**Tamanho:** M

### T13 — Contract: remover as tabelas antigas

**Descrição:** Dropar `planning`, `post_structure`, `design_structure` e `generated_image`, remover o script de backfill e os consumidores remanescentes.

**Critérios de aceite:**
- [ ] Revisão `0013_*` remove as 4 tabelas; downgrade as recria vazias.
- [ ] Nenhum model, repositório, teste ou worker referencia as tabelas removidas.
- [ ] Relatório de paridade regenerado sem sobras de redesign.

**Verificação:**
- [ ] `grep -rn "post_structure\|design_structure\|generated_image\b" src tests workers` sem resultados.
- [ ] `make check` e `make e2e` verdes.

**Dependências:** T12
**Arquivos prováveis:** `migrations/versions/0013_*.py`, `src/creator/**/models.py`, `docs/migration/schema-final-alignment.md`
**Tamanho:** S

### Checkpoint — Fase 3
- [ ] Backfill idempotente e contagens conferidas.
- [ ] Banco vazio e banco de dev convergem para o mesmo schema.
- [ ] `make e2e` verde após a remoção.

## Fase 4 — Alinhar as 31 tabelas comuns

### T14 — Lote A: identidade, notificações, brand, campanha, persona (13 tabelas)

**Descrição:** Alinhar `users`, `workspaces`, `workspace_invites`, `workspace_invite_usages`, `notifications`, `notification_recipients`, `notification_preferences`, `user_devices`, `brands`, `brand_colors`, `brand_assets`, `campaigns` e `personas` — colunas, nullability, tamanhos, enums e índices — usando `render_as_batch`.

**Critérios de aceite:**
- [ ] As 13 tabelas sem divergência de coluna, nullability ou tamanho no relatório.
- [ ] Enums dessas tabelas com vocabulário do dump (`workspace_role`, `invite_*`, `notification_*`, `device_platform`, `persona_gender`, `age_range`, `brand_asset_type`, `campaign_voice`).
- [ ] `docs/openapi.yaml` atualizado antes de mudar payload (membership status, brand, campaign).
- [ ] Fixtures de snapshot regenerados na mesma PR.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` verde para esse conjunto.
- [ ] `make check` e `alembic upgrade head && alembic downgrade -1`.

**Dependências:** T13
**Arquivos prováveis:** `src/creator/user/models.py`, `src/creator/workspace/models.py`, `src/creator/notification/models.py`, `src/creator/brand/models.py`, `src/creator/campaign/models.py`, `src/creator/persona/models.py`, `migrations/versions/0014_*.py`, `docs/openapi.yaml`
**Tamanho:** M

### T15 — Lote B: billing, créditos e cupons (18 tabelas)

**Descrição:** Alinhar as 18 restantes: `billing_accounts`, `billing_addresses`, `billing_payment_methods`, `plans`, `plan_items`, `subscriptions`, `subscription_history`, `orders`, `invoices`, `charges`, `refunds`, `provider_disputes`, `provider_webhook_events`, `provider_idempotency_keys`, `coupons`, `coupon_redemptions`, `credit_packages`, `workspace_credit_transactions`.

**Critérios de aceite:**
- [ ] As 18 tabelas sem divergência; `bigint` nos campos de centavos conforme dump.
- [ ] Backfill de contagem de cupom, `credits`/`credits_validity_days` e `workspace_credit_transactions` (`amount`, `balance_after`).
- [ ] Revisões batch (`0015_*`, `0016_*`) com downgrade funcional.
- [ ] `docs/openapi.yaml` atualizado antes da mudança de contrato.

**Verificação:**
- [ ] `python scripts/schema_parity_report.py` sem divergência nas 54 tabelas.
- [ ] `pytest tests/test_schema_inventory.py -q` verde por completo.
- [ ] `make check`, `make security` e `make e2e` verdes.

**Dependências:** T14
**Arquivos prováveis:** `src/creator/billing/models.py`, `src/creator/credit/models.py`, `src/creator/plan/models.py`, `src/creator/coupon/models.py`, `src/creator/charge/models.py`, `src/creator/invoice/models.py`, `src/creator/order/models.py`, `src/creator/refund/models.py`, `migrations/versions/0015_*.py`, `docs/openapi.yaml`
**Tamanho:** M

### Checkpoint — Fase 4
- [ ] `python scripts/schema_parity_report.py` → 54/54 sem divergência.
- [ ] `tests/test_schema_inventory.py` inteiro verde.
- [ ] `make check`, `make security` e `make e2e` verdes.
- [ ] Revisão humana do relatório e do diff de `tests/contracts/` antes da fase destrutiva.

## Fase 5 — Aposentadoria do legado

### T16 — ADR-029, 11 legadas e 2 tabelas sem alvo

**Descrição:** Mapear cada tabela legada ao alvo final ou justificar retenção com prazo; remover as aprovadas, ajustar consumidores (settings, workers, repositórios) e decidir `provider_customers` e `provider_subscriptions`.

**Critérios de aceite:**
- [ ] ADR-029 com tabela→alvo, ordem de remoção e verificação de consumidores por tabela.
- [ ] Remoções em revisão única com downgrade; retenções registradas com prazo.
- [ ] `provider_customers`/`provider_subscriptions`: decisão explícita e, se retidas, exceção declarada no teste de paridade.
- [ ] Entrypoints `creator.workers.*` não renomeados.

**Verificação:**
- [ ] `grep -rn "<tabela removida>" src tests workers scripts` sem resultado por tabela removida.
- [ ] `make e2e` verde e `python scripts/check_migrations.py`.

**Dependências:** T15
**Arquivos prováveis:** `docs/adr/0029-legacy-table-retirement.md`, `migrations/versions/0017_*.py`, `src/creator/settings/**`, `workers/**`
**Tamanho:** M

### Checkpoint — Fase 5
- [ ] Toda tabela viva é final, extensão de ADR ou retenção aprovada com prazo.
- [ ] Relatório de paridade reconhece apenas as exceções declaradas.
- [ ] `make check`, `make security` e `make e2e` verdes.

## Fase 6 — Consolidação e fechamento

### T17 — Consolidar a baseline

**Descrição:** Regenerar `0001_sqlite_baseline` do metadata final (54 tabelas + 4 extensões), remover as revisões intermediárias e provar que banco vazio e banco de dev convergem.

**Critérios de aceite:**
- [ ] Baseline regenerada e revisada à mão (enums com CHECK, índices nomeados, FKs inline, `downgrade base` funcional).
- [ ] `scripts/check_migrations.py` vê uma única head, sem operação inesperada.
- [ ] Procedimento de reset do banco de dev documentado na ADR-028.
- [ ] `migrations/legacy_postgres/` e ADR-021 intocados.

**Verificação:**
- [ ] `rm -f .local/db/creator.db && alembic upgrade head && alembic downgrade base`.
- [ ] `make snapshot-contract` sem diff (prova de que o squash preservou o schema).
- [ ] `pytest tests/test_schema_inventory.py tests/test_module_boundaries.py -q`.

**Dependências:** T13, T15, T16
**Arquivos prováveis:** `migrations/versions/0001_sqlite_baseline.py`, `docs/adr/0028-sqlite-final-schema-alignment.md`
**Tamanho:** M

### T18 — Fechamento do épico

**Descrição:** Regenerar relatório de paridade e `docs/openapi.yaml`, atualizar tracker, épico 0057 e issue #159 com evidência de CI, e rodar os três gates finais.

**Critérios de aceite:**
- [ ] `docs/openapi.yaml` em paridade com `app.openapi()`.
- [ ] Relatório de paridade mostrando 54/54 + 4 extensões e zero divergência não declarada.
- [ ] Tracker, épico e #159 com critérios marcados e evidência.
- [ ] Critérios de aceite de `docs/issues/0057` revisados um a um.

**Verificação:**
- [ ] `XDG_DATA_HOME=$PWD/.local/xdg make check PYTHON=.venv/bin/python`.
- [ ] `XDG_DATA_HOME=$PWD/.local/xdg make security PYTHON=.venv/bin/python`.
- [ ] `XDG_DATA_HOME=$PWD/.local/xdg make e2e PYTHON=.venv/bin/python`.

**Dependências:** T17
**Arquivos prováveis:** `docs/openapi.yaml`, `docs/migration/schema-final-alignment.md`, `docs/ADR-ISSUE-TRACKER.md`, `docs/issues/0057-sqlite-final-schema-alignment.md`
**Tamanho:** S

### Checkpoint — Fase 6 (final)
- [ ] Três gates verdes com `XDG_DATA_HOME` explícito.
- [ ] Teste de paridade verde nas seis dimensões.
- [ ] Banco recriável do zero e reset de dev documentado.
- [ ] PR revisado por humano antes do merge em `dev`.

## Rastreamento das 54 tabelas do modelo final

Cada linha indica a ação e a tarefa que a executa. A ação repete o delta do relatório
(`+` coluna exigida, `−` coluna sobrante, `!` nullability, tamanho, enum, índices).

#### Identidade e Workspace

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `users` | alinhar: +1 col, −5 col, !1 null, 1 tamanho | T14 |
| `workspaces` | alinhar: índices | T14 |
| `workspace_members`
(hoje `workspace_memberships`) | renomear + alinhar | T8 |
| `workspace_invites` | alinhar: +1 col, −4 col, 1 tamanho, 3 enum | T14 |
| `workspace_invite_usages` | alinhar: −4 col, !1 null | T14 |

#### Notificações

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `notifications` | alinhar: −1 col, 2 enum | T14 |
| `notification_recipients` | alinhar: +1 col, −3 col, 2 enum | T14 |
| `user_devices` | alinhar: −1 col, 1 enum | T14 |
| `notification_preferences` | alinhar: −1 col, 2 enum | T14 |

#### Billing

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `billing_accounts` | alinhar: +3 col, −4 col, !1 null, 1 tamanho, 2 enum | T15 |
| `billing_addresses` | alinhar: +8 col, −4 col, !4 null, 3 tamanho | T15 |
| `billing_payment_methods` | alinhar: +8 col, −5 col | T15 |
| `plans` | alinhar: +13 col, −3 col, 1 enum | T15 |
| `plan_items` | alinhar: +3 col, −3 col, !1 null, 1 tamanho, 2 enum | T15 |
| `plan_payment_methods` | criar | T7 |
| `subscriptions` | alinhar: +9 col, −7 col, !1 null, 1 tamanho, 4 enum | T15 |
| `subscription_history` | alinhar: +9 col, −7 col, 1 enum | T15 |
| `orders` | alinhar: +3 col, −3 col, 3 tamanho, 1 enum | T15 |
| `invoices` | alinhar: +2 col, −3 col, !1 null, 3 tamanho, 2 enum | T15 |
| `charges` | alinhar: +15 col, −3 col, 1 tamanho | T15 |
| `charge_transactions` | criar | T7 |
| `refunds` | alinhar: +7 col, −6 col, 1 tamanho, 1 enum | T15 |
| `provider_disputes` | alinhar: +6 col, −3 col, 1 enum | T15 |
| `provider_webhook_events` | alinhar: +1 col, −3 col, 2 enum | T15 |
| `provider_idempotency_keys` | alinhar: +1 col, −1 col, 2 enum | T15 |
| `fiscal_invoices` | criar | T7 |

#### Créditos e Cupons

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `credit_packages` | alinhar: +2 col, −3 col, 1 tamanho | T15 |
| `coupons` | alinhar: +3 col, −2 col, 1 tamanho, 2 enum | T15 |
| `coupon_redemptions` | alinhar: +10 col, −3 col, 1 tamanho, 1 enum | T15 |
| `workspace_credit_transactions` | alinhar: +7 col, −5 col | T15 |
| `workspace_credit_lots` | criar | T7 |
| `workspace_credit_lot_consumptions` | criar | T7 |

#### Brand

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `brands` | alinhar: +7 col, −4 col, 1 tamanho | T14 |
| `brand_values` | criar | T6 |
| `brand_hashtags` | criar | T6 |
| `brand_colors` | alinhar: +3 col, −15 col | T14 |
| `brand_assets` | alinhar: +3 col, −2 col, 1 enum | T14 |
| `brand_business_details` | criar | T6 |

#### Campanha

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `campaigns` | alinhar: +2 col, −4 col, 1 tamanho | T14 |
| `campaign_hashtags` | criar | T6 |
| `campaign_voices` | criar | T6 |

#### Persona

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `personas` | alinhar: +2 col, −3 col, 1 tamanho, 1 enum | T14 |
| `persona_interests` | criar | T5 |

#### Planejamento e Conteúdo

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `content_plans`
(hoje `planning`) | redesenhar (expand → contract) | T9 |
| `content_plan_items` | criar | T9 |
| `content_plan_special_dates` | criar | T9 |
| `posts`
(hoje `post_structure`) | redesenhar (expand → contract) | T10 |
| `captions` | criar | T10 |
| `post_designs`
(hoje `design_structure`) | redesenhar (expand → contract) | T10 |
| `design_slides` | criar | T10 |

#### Geração e Mídia

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `generated_images`
(hoje `generated_image`) | redesenhar (expand → contract) | T11 |
| `image_resizes` | criar | T11 |

#### Conformidade e Auditoria

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `audit_logs` | criar | T5 |
| `user_consents` | criar | T5 |

### Extensões de ADR preservadas (fora do modelo final)

| Tabela | Decisão | Tarefa |
| --- | --- | --- |
| `auth_sessions` | preservar; exceção declarada no teste de paridade | T2, T17 |
| `outbox_events` | preservar; exceção declarada no teste de paridade | T2, T17 |
| `activity_events` | preservar; exceção declarada no teste de paridade | T2, T17 |
| `content_text_versions` | preservar; exceção declarada no teste de paridade | T2, T17 |

### Legado com consumidores (11) e sem alvo (2)

| Tabela | Decisão | Tarefa |
| --- | --- | --- |
| `settings` | mapear para configuração de workspace e remover, ou reter com prazo | T16 |
| `brand_settings` | absorver em `brands` e remover | T16 |
| `projects` | mapear para `content_plans`/`campaigns` e remover | T16 |
| `contents` | mapear para `posts` e remover | T16 |
| `generations` | mapear para `generated_images`/`content_text_versions` e remover | T16 |
| `assets` | mapear para `brand_assets`/`generated_images` e remover | T16 |
| `generation_jobs` | mapear para `generated_images` e remover | T16 |
| `generation_job_status_events` | absorver em `activity_events` e remover | T16 |
| `images` | mapear para `generated_images` e remover | T16 |
| `agent_workflow_runs` | absorver em `activity_events` ou reter com prazo | T16 |
| `agent_workflow_steps` | absorver em `activity_events` ou reter com prazo | T16 |
| `provider_customers` | remover ou reter como cache de provider (decisão humana) | T16 |
| `provider_subscriptions` | remover ou reter como cache de provider (decisão humana) | T16 |

## Riscos e mitigações

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| PR muda schema sem regenerar `schema_tables.json`/`schema_ddl.sql` | Alto | `make snapshot-contract` é critério de aceite de toda tarefa de schema, na mesma PR |
| Teste de paridade divergente do snapshot congelado | Médio | paridade dentro de `tests/test_schema_inventory.py`, dono único das fixtures |
| Índices anônimos quebram asserção por nome | Alto | convenção `ix_/uq_` na ADR-028; mapeamento explícito dos 123 anônimos |
| Squash da baseline destrói banco de dev | Alto | só depois de T13–T16; reset documentado; `make snapshot-contract` sem diff como prova |
| `ALTER TABLE` limitado no SQLite | Médio | `render_as_batch` obrigatório em T14/T15; `downgrade` testado por revisão |
| Perda de dados nos 4 redesenhos | Alto | expand antes de contract; backfill idempotente testado (T12); contract isolado (T13) |
| CHECKs PostgreSQL incompatíveis | Alto | T4 traduz e testa equivalência antes de qualquer tabela nova usando o helper |
| FK composta sem UNIQUE no alvo falha em runtime | Médio | T2 asserta FKs; UNIQUE composta exige teste explícito |
| Drift dos 52 enums | Médio | inventário único (T3) + `test_final_enum_vocabulary` |
| `test_module_boundaries` quebrado por models novos | Médio | tabela nova nasce em `<entity>/models.py` + `repository.py` |
| `docs/openapi.yaml` dessincronizado | Médio | contrato antes do código em T10, T14 e T15 |
| Remoção de legado quebra worker/settings | Alto | ADR-029 com mapeamento e `grep` de consumidores; `make e2e` antes do merge |
| Volume de PRs e conflito de revisões | Médio | uma revisão por tarefa, cadeia linear, rebase diário, PR por fase |

## Questões abertas

1. **Existe banco com dados a preservar?** Se sim, a consolidação da baseline (T17) fica proibida e o backfill passa a ser obrigatório também para as 31 tabelas alinhadas.
2. **`settings` e `brand_settings`:** viram colunas em `workspaces`/`brands` ou permanecem como tabela chave-valor até existir UI de configuração? Muda o escopo de T16.
3. **`provider_customers`/`provider_subscriptions`:** remover (estado em `charge_transactions`/`fiscal_invoices`) ou manter como cache para idempotência e reconciliação?
4. **Enums:** paridade 1:1 com os 52, incluindo valores sem uso previsto, ou apenas o subconjunto ativo?
5. **`workspace_members.deleted_at` removido:** confirma que não há soft delete nesse agregado (remoção de vínculo é exclusão física)?
6. **`generated_images.is_current`:** unicidade por `design_slide_id` (como o dump sugere) ou por `post`? O índice do dump é parcial e precisa de decisão explícita.

## Task list for tracker

```json
[
  {"id":"T1","title":"ADR-028, épico e tracker","description":"Registrar a estratégia de alinhamento (incrementais + squash final, expand→backfill→contract, teste de paridade, convenção de índices, gate de snapshot, enums e constraints portáveis) e amarrar épico 0057 e #159 às ADR-021/015.","priority":"high","depends_on":[],"phase":"Fase 0 — Contrato, paridade e portabilidade","files":["docs/adr/0028-sqlite-final-schema-alignment.md","docs/ADR-ISSUE-TRACKER.md","docs/issues/0057-sqlite-final-schema-alignment.md"],"size":"S"},
  {"id":"T2","title":"Teste de paridade contra o DDL final","description":"Versionar tests/contracts/creator_db_final.sql e adicionar ao inventário as asserções de tabelas, colunas, nullability/tamanho, enums, índices e FKs, com as extensões de ADR como exceção declarada e falha agregada.","priority":"high","depends_on":["T1"],"phase":"Fase 0 — Contrato, paridade e portabilidade","files":["tests/test_schema_inventory.py","tests/contracts/creator_db_final.sql"],"size":"M"},
  {"id":"T3","title":"Helpers portáveis de coluna, enum e índice","description":"Centralizar PK UUID, timestamps UTC, JSON, enum portátil, fábricas de índice ix_/uq_ e as 52 constantes de enum em creator/infrastructure/database/.","priority":"high","depends_on":["T1"],"phase":"Fase 0 — Contrato, paridade e portabilidade","files":["src/creator/infrastructure/database/columns.py","src/creator/infrastructure/database/enums.py"],"size":"S"},
  {"id":"T4","title":"Portabilidade das CHECK constraints e defaults","description":"Traduzir as 80 CHECKs do dump (15 regex de moeda, 3 num_nonnulls) para expressões SQLite com helpers testados e definir o mapa gen_random_uuid→uuid4 e now→CURRENT_TIMESTAMP.","priority":"high","depends_on":["T3"],"phase":"Fase 0 — Contrato, paridade e portabilidade","files":["src/creator/infrastructure/database/constraints.py","tests/test_portable_schema.py"],"size":"M"},
  {"id":"T5","title":"Conformidade, consentimento e interesses","description":"Criar audit_logs, user_consents e persona_interests com FKs, UNIQUE e índices conforme o dump, mais revisão 0006 com downgrade.","priority":"medium","depends_on":["T4"],"phase":"Fase 1 — Criar tabelas","files":["src/creator/audit/models.py","src/creator/user/models.py","src/creator/persona/models.py","migrations/versions/0006_*.py"],"size":"S"},
  {"id":"T6","title":"Satélites de Brand e Campanha","description":"Criar brand_business_details, brand_hashtags, brand_values, campaign_hashtags e campaign_voices com UNIQUE por pai e FKs em cascata, mais revisão 0007.","priority":"medium","depends_on":["T4"],"phase":"Fase 1 — Criar tabelas","files":["src/creator/brand/models.py","src/creator/campaign/models.py","migrations/versions/0007_*.py"],"size":"M"},
  {"id":"T7","title":"Satélites de Billing e Créditos","description":"Criar plan_payment_methods, charge_transactions, fiscal_invoices, workspace_credit_lots e workspace_credit_lot_consumptions com CHECKs portáveis e ledger sem dupla contagem.","priority":"medium","depends_on":["T4"],"phase":"Fase 1 — Criar tabelas","files":["src/creator/billing/models.py","src/creator/credit/models.py","migrations/versions/0008_*.py"],"size":"M"},
  {"id":"T8","title":"Renomear workspace_memberships para workspace_members","description":"Renomear a tabela, adicionar status e invited_by, remover deleted_at, preservar UNIQUE(workspace_id, user_id) e atualizar repositório, autorização e testes.","priority":"high","depends_on":["T4"],"phase":"Fase 2 — Renomear e redesenhar (expand)","files":["src/creator/workspace/models.py","src/creator/workspace/repository.py","migrations/versions/0009_*.py"],"size":"S"},
  {"id":"T9","title":"planning para content_plans e satélites","description":"Expand do redesenho de planejamento: content_plans com 11 colunas, content_plan_items e content_plan_special_dates, mantendo planning intacta.","priority":"high","depends_on":["T4"],"phase":"Fase 2 — Renomear e redesenhar (expand)","files":["src/creator/planning/models.py","src/creator/planning/repository.py","migrations/versions/0010_*.py"],"size":"M"},
  {"id":"T10","title":"post_structure e design_structure para posts, captions, post_designs e design_slides","description":"Expand do redesenho editorial: posts com 17 colunas e CHECKs de aprovação/agendamento, captions versionadas, post_designs com format/ratio e design_slides ordenados.","priority":"high","depends_on":["T4"],"phase":"Fase 2 — Renomear e redesenhar (expand)","files":["src/creator/content/models.py","src/creator/design_structure/models.py","migrations/versions/0011_*.py","docs/openapi.yaml"],"size":"M"},
  {"id":"T11","title":"generated_image para generated_images e image_resizes","description":"Expand do redesenho de mídia: generated_images com 23 colunas e 9 CHECKs portadas, image_resizes com UNIQUE (source_image_id, ratio).","priority":"high","depends_on":["T4"],"phase":"Fase 2 — Renomear e redesenhar (expand)","files":["src/creator/generation/models.py","migrations/versions/0012_*.py"],"size":"M"},
  {"id":"T12","title":"Backfill dos 4 redesenhos","description":"Script idempotente com relatório de contagens e invariantes copiando planning, post_structure, design_structure e generated_image para as tabelas novas, testado em SQLite temporário.","priority":"high","depends_on":["T8","T9","T10","T11"],"phase":"Fase 3 — Backfill e contract","files":["scripts/backfill_redesigns.py","tests/test_backfill_redesigns.py"],"size":"M"},
  {"id":"T13","title":"Contract: remover as tabelas antigas","description":"Dropar planning, post_structure, design_structure e generated_image, remover o script de backfill e os consumidores remanescentes, com downgrade funcional.","priority":"high","depends_on":["T12"],"phase":"Fase 3 — Backfill e contract","files":["migrations/versions/0013_*.py","docs/migration/schema-final-alignment.md"],"size":"S"},
  {"id":"T14","title":"Lote A: identidade, notificações, brand, campanha e persona","description":"Alinhar 13 tabelas (users, workspaces, invites, usages, notifications, recipients, preferences, devices, brands, brand_colors, brand_assets, campaigns, personas) com batch, enums do dump e OpenAPI atualizado.","priority":"medium","depends_on":["T13"],"phase":"Fase 4 — Alinhar tabelas comuns","files":["src/creator/user/models.py","src/creator/workspace/models.py","src/creator/notification/models.py","src/creator/brand/models.py","src/creator/campaign/models.py","src/creator/persona/models.py","migrations/versions/0014_*.py","docs/openapi.yaml"],"size":"M"},
  {"id":"T15","title":"Lote B: billing, créditos e cupons","description":"Alinhar as 18 tabelas de billing, assinaturas, charges, invoices, refunds, providers, cupons e créditos, com bigint nos centavos e backfill dos campos novos.","priority":"medium","depends_on":["T14"],"phase":"Fase 4 — Alinhar tabelas comuns","files":["src/creator/billing/models.py","src/creator/credit/models.py","src/creator/coupon/models.py","migrations/versions/0015_*.py","docs/openapi.yaml"],"size":"M"},
  {"id":"T16","title":"ADR-029, 11 legadas e 2 tabelas sem alvo","description":"Mapear cada tabela legada ao alvo final ou justificar retenção com prazo, remover as aprovadas, ajustar consumidores e decidir provider_customers e provider_subscriptions.","priority":"medium","depends_on":["T15"],"phase":"Fase 5 — Aposentadoria do legado","files":["docs/adr/0029-legacy-table-retirement.md","migrations/versions/0017_*.py"],"size":"M"},
  {"id":"T17","title":"Consolidar a baseline","description":"Regenerar 0001_sqlite_baseline do metadata final, remover revisões intermediárias e provar convergência com make snapshot-contract sem diff.","priority":"high","depends_on":["T13","T15","T16"],"phase":"Fase 6 — Consolidação e fechamento","files":["migrations/versions/0001_sqlite_baseline.py","docs/adr/0028-sqlite-final-schema-alignment.md"],"size":"M"},
  {"id":"T18","title":"Fechamento do épico","description":"Regenerar relatório de paridade e OpenAPI, atualizar tracker, épico 0057 e #159 com evidência de CI e rodar os três gates finais.","priority":"high","depends_on":["T17"],"phase":"Fase 6 — Consolidação e fechamento","files":["docs/openapi.yaml","docs/migration/schema-final-alignment.md","docs/ADR-ISSUE-TRACKER.md"],"size":"S"}
]
```
