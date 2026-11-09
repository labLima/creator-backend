# Plano de implementação: alinhamento ao Creator_DB_final.sql

> Gerado com a skill `planning-and-task-breakdown` e apoio do agente `planner`.
> A saída bruta do planner foi revisada e corrigida contra o repositório: ela citava tabelas
> inexistentes no modelo final (`roles`, `media_files`, `generation_requests` etc.), ADR-022/023
> (já ocupadas) e a issue local 0050 (já usada). Este documento substitui aquela versão.
> Números e listas vêm de `docs/migration/schema-final-alignment.md`, regenerável por
> `python scripts/schema_parity_report.py`.

## Overview

Fazer o schema vivo (metadata SQLAlchemy + Alembic, SQLite) coincidir com a modelagem final
`docs/migration/Creator_DB_final.sql`: **54 tabelas, 52 enums, 173 índices, 101 FKs, 80 CHECKs,
69 funções/triggers e 1 view**. O delta verificado é 18 tabelas a criar, 31 a alinhar, 1 rename
com migração de valores e 4 redesenhos de modelo. A migração PostgreSQL→SQLite **já está
concluída** (ADR-021, `0001_sqlite_baseline.py`, `migrations/legacy_postgres/`, compose com
`sqlite+pysqlite:////data/creator.db`) e não é reescopada aqui.

O conjunto-alvo durante a execução é de **71 tabelas** (54 do dump + 4 extensões de ADR + 13
legadas/sem alvo), não 58: as 13 só saem com a ADR-029. `users.password_hash` e
`users.global_role` permanecem como extensão da ADR-020, mesmo ausentes no dump.

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
4. **Comparador único em `src/`, importável pelos dois lados.** O parsing e a comparação vivem
   em `src/creator/infrastructure/database/final_schema.py`; `scripts/schema_parity_report.py`
   passa a ser um invólucro fino. `scripts/` e `tests/` não se importam entre si, e duplicar o
   parser criaria duas verdades. O módulo não importa `Base` nem muta `sys.path`.
5. **Oito dimensões de paridade em `tests/test_schema_inventory.py`**, junto dos fixtures
   congelados: tabelas (aplicando o mapa de renames uma vez); colunas e PK; nullability, tamanho
   de `String` e largura `Integer`/`BigInteger`; enums; índices e UNIQUE (nome, colunas
   ordenadas, unicidade, predicado parcial); FKs (colunas locais, alvo, colunas do alvo,
   `ON DELETE`); CHECKs; e presença de defaults. CHECKs e FKs não são comparáveis por texto
   entre PostgreSQL e SQLite, então o módulo declara `CHECK_MAP` e `RENAME_MAP`, e o teste falha
   se um CHECK do dump ficar sem entrada.
6. **Orçamento de dívida que só diminui (ratchet).** `tests/contracts/schema_parity_budget.json`
   guarda `dump_sha256`, contagem por categoria e `gap_digest`. O teste exige igualdade: dívida
   maior falha (`schema debt GREW`), dívida menor também falha (`ratchet stale: reduza o
   orçamento nesta PR`). Assim o PR que corrige uma tabela reduz a contagem e o digest na mesma
   diff — a evidência de progresso é o diff. `xfail`, skip e allowlist por tabela são rejeitados
   porque não forçam a limpeza; no fim todas as contagens são zero.
7. **Snapshot passa a ser gate e a cobrir índices.** `scripts/snapshot_contract.py` ganha
   `--check` e `make check` passa a executá-lo. O fixture `tests/contracts/schema_ddl.sql` ganha
   os `CREATE INDEX` canônicos (hoje não tem nenhum, então mudança só de índice é invisível), e
   a comparação deixa de colapsar todo whitespace: normaliza apenas EOL e espaço final. Essa
   normalização frouxa foi o que escondeu o gerador emitindo espaço final.
8. **`alembic check` deixa de ser vacuous.** A baseline usa `create_all()` sobre o metadata
   corrente, então um banco novo já nasce alinhado e uma revisão esquecida não é detectada.
   Medidas: `compare_type=True` e `render_as_batch=True` em `migrations/env.py`, e um teste de
   upgrade a partir de `tests/contracts/schema_prev_ddl.sql` (schema da head anterior), estampado
   na revisão correspondente, que precisa convergir para `Base.metadata` após `alembic upgrade
   head`. O fixture é renovado a cada fase que muda schema.
9. **Índices: preservar nomes explícitos, nomear só os anônimos.** SQLite **exige** nome em
   `CREATE INDEX` (não existe `CREATE INDEX ON tabela`). Dos 173 índices do dump, 50 têm nome
   (`idx_m8_*`, `uq_*`) e são preservados; os 123 anônimos recebem nome na metadata pela
   convenção `ix_<tabela>_<colunas>`/`uq_<tabela>_<colunas>`, com mapeamento no teste.
10. **Portabilidade de constraints é trabalho explícito.** SQLite não aceita
    `ALTER TABLE ... ADD CONSTRAINT`, então as 101 FKs precisam estar nas models. São 10
    compostas: **6 com `workspace_id` e 4 com `brand_id`**, cada uma exigindo UNIQUE composta no
    alvo com a chave exata. `ON DELETE` preservado (40 CASCADE, 31 RESTRICT, 30 SET NULL). Dos
    80 CHECKs, 15 usam regex PostgreSQL — 12 de moeda, 1 de UF, 1 de CEP e 1 de cor hexadecimal —
    e 3 usam `num_nonnulls`. Helpers em `creator/infrastructure/database/constraints.py` traduzem
    para `GLOB`/`LIKE`/`length`/`upper` e soma de `CASE WHEN ... IS NOT NULL`, com teste de
    equivalência por helper. `gen_random_uuid()` vira default Python `uuid4`; `now()` vira
    `CURRENT_TIMESTAMP`/helper UTC.
11. **Enums: 52 tipos, vocabulário 1:1.** `Enum(native_enum=False, create_constraint=True)` ou
    `String` + `CHECK`, em `creator/infrastructure/database/enums.py`, importado pelas models.
    Vocabulário idêntico ao dump, inclusive valores sem uso previsto.
12. **Triggers, funções e view têm decisão própria.** As 69 funções/triggers e a view
    `charges_with_last_transaction` carregam regra no banco (imutabilidade do ledger, validação
    de lote, `updated_at`, snapshot de cupom, histórico append-only). T19 inventaria objeto a
    objeto e classifica em portar como trigger SQLite, mover para a aplicação com teste
    equivalente, ou declarar fora de escopo com justificativa. Ledger e histórico de assinatura
    são obrigatoriamente cobertos.
13. **Rename também migra dados.** `workspace_memberships` → `workspace_members` muda o
    vocabulário de `role` (`owner/admin/editor/viewer` → `OWNER/MANAGER/EDITOR/VIEWER`), adiciona
    `status` e remove `deleted_at` (hoje filtrado nas consultas). Segue expand → backfill →
    contract como as demais, com mapa de valores explícito.
14. **Aposentadoria do legado em ADR-029**, com mapeamento tabela→alvo, ordem de remoção e
   verificação de consumidores. Tabela retida precisa de justificativa e prazo escritos.
15. **Rastreabilidade**: ADR-028 e ADR-029 em `docs/adr/`, indexadas em
    `docs/ADR-ISSUE-TRACKER.md`; épico local
    [0057](../docs/issues/0057-sqlite-final-schema-alignment.md) e issue
    [#159](https://github.com/labLima/creator-backend/issues/159); issues filhas no board `SHC`
    do Shared Context, uma por tarefa (cada uma declara o workspace
    `/home/emanueljtrodrigues/Documents/LeFil/creator-backend`). `docs/openapi.yaml` é
    atualizado antes de qualquer mudança de payload HTTP (membership status, posts com
    aprovação/agendamento, créditos).

## Dependências descobertas na execução (2026-11-09)

- **T14 foi dividida em T24 e T25.** O lote A original cobria 13 tabelas de seis
  domínios e um backfill de `campaigns.brand_id`; uma rodada só não fecha isso com
  qualidade. T24 cobre identidade/notificações (incluindo o enum de `role` em
  `workspace_invites`) e T25 cobre brand/campanha/persona com o backfill de
  `campaigns.brand_id`.

- **T13 depende da migração de consumidores.** 17 arquivos de aplicação (routers,
  services, repositórios e UoW de Planning, PostStructure, Generation e Content)
  ainda usam as tabelas legadas. Dropar `planning`/`post_structure`/
  `design_structure`/`generated_image` sem migrar esses consumidores quebra as
  rotas e o e2e. T13 fica dividida em **T23** (migrar consumidores mantendo o
  contrato HTTP) e T13 (dropar as tabelas), nessa ordem.

- **T9, T10 e T11 dependem de T14.** `content_plans`, `posts`/`post_designs` e
  `brand_business_details` têm FKs compostas para `campaigns(id, brand_id)` e
  `personas(id, brand_id)`. `campaigns` ainda não tem `brand_id` e falta o UNIQUE
  `(id, brand_id)` nas duas tabelas, então essas fatias não podem ser criadas antes do
  alinhamento de campanhas/personas. T14 (ou uma fatia inicial dela) precede T9–T11.
- **T8 foi dividida.** A renomeação + `status`/`invited_by` + remoção de `deleted_at` é
  uma fatia própria; trocar o vocabulário de `role` e as regras de autorização é outra
  (T21), porque toca `ROLE_RANK`, `minimum_role="admin"`, workers e testes de auth em 21
  arquivos. Cada fatia precisa fechar verde.

## Fase 0 — Contrato, paridade e portabilidade

### T1 — ADR-028, épico e tracker

**Descrição:** Registrar a estratégia de alinhamento (incrementais + squash final, expand→backfill→contract, teste de paridade em `tests/test_schema_inventory.py`, convenção de nomes de índice, gate `make snapshot-contract`, política de enums e de constraints portáveis) e amarrar a rastreabilidade do épico 0057 / #159 às ADR-021 e ADR-015.

**Critérios de aceite:**
- [ ] `docs/adr/0028-sqlite-final-schema-alignment.md` aceita, cobrindo as decisões 1–15.
- [ ] `docs/ADR-ISSUE-TRACKER.md` lista ADR-028 com tracker e issues de implementação.
- [ ] Épico [0057](../docs/issues/0057-sqlite-final-schema-alignment.md) aponta para o plano e para as issues filhas.
- [ ] `tasks/plan.md` e `tasks/todo.md` (históricos) permanecem intocados.

**Verificação:**
- [ ] `python scripts/schema_parity_report.py` sem erro e relatório commitado.
- [ ] `git diff --exit-code tests/contracts/` (fase sem mudança de schema).

**Dependências:** Nenhuma
**Arquivos prováveis:** `docs/adr/0028-sqlite-final-schema-alignment.md`, `docs/ADR-ISSUE-TRACKER.md`, `docs/issues/0057-sqlite-final-schema-alignment.md`
**Tamanho:** S

### T2 — Comparador único e teste de paridade com orçamento

**Descrição:** Extrair o parsing e a comparação para `src/creator/infrastructure/database/final_schema.py` (`parse_final`, `parse_models`, `compare`, `gap_counts`, `gap_digest`, `render_schema_ddl`), fazer `scripts/schema_parity_report.py` usá-lo e adicionar ao inventário congelado os testes de paridade em oito dimensões, com as exceções declaradas (`ADR_EXTENSIONS`, `LEGACY_RETENTION`, `RENAME_MAP`, `CHECK_MAP`) e orçamento de dívida que só diminui.

**Critérios de aceite:**
- [ ] O módulo não importa `Base`, não muta `sys.path` e não importa `tests`; o script vira invólucro fino.
- [ ] `parse_models` passa a registrar colunas de índice, unicidade, predicado e **todas** as colunas de FK composta (hoje perde as demais).
- [ ] `tests/contracts/creator_db_final.sql` versionado com sha256 conferido; `tests/contracts/schema_parity_budget.json` com `dump_sha256`, contagem por categoria e `gap_digest`.
- [ ] Testes: `test_final_table_set` (54 + 4 extensões + 13 legadas declaradas), `test_final_columns_and_pk`, `test_final_nullability_and_widths`, `test_final_enum_vocabulary`, `test_final_indexes`, `test_final_foreign_keys`, `test_final_checks`, `test_final_defaults`.
- [ ] O teste exige **igualdade** com o orçamento: dívida maior falha (`schema debt GREW`) e dívida menor também (`ratchet stale`).
- [ ] `test_ratchet_mechanism` prova, sobre dados sintéticos, que crescimento e estagnação são detectados.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` verde com o orçamento atual.
- [ ] `python scripts/schema_parity_report.py` regenera o relatório idêntico ao commitado.
- [ ] `XDG_DATA_HOME=$PWD/.local/xdg make check PYTHON=.venv/bin/python`.

**Dependências:** T1
**Arquivos prováveis:** `src/creator/infrastructure/database/final_schema.py`, `scripts/schema_parity_report.py`, `tests/test_schema_inventory.py`, `tests/contracts/creator_db_final.sql`, `tests/contracts/schema_parity_budget.json`
**Tamanho:** L (justificado: fundação única; será fatiado em commits por dimensão)

### T3 — Helpers portáveis de enum e nome de índice

**Descrição:** Estender o que já existe em `creator/infrastructure/database/types.py` (não criar um `columns.py` paralelo) com o módulo de enums e o de nomes: `enums.py` com os 52 vocabulários e `enum_column(nome)`, e `naming.py` com `index_name`/`unique_index_name` para os 123 índices anônimos.

**Critérios de aceite:**
- [ ] `enums.py` com os 52 vocabulários extraídos do dump, validados pelo teste de paridade.
- [ ] `enum_column("workspace_role")` renderiza `VARCHAR` + `CHECK` (sem enum nativo) e rejeita valor fora do vocabulário.
- [ ] `naming.py` preserva nomes explícitos do dump e só gera nome para índice anônimo.
- [ ] `types.py` reexporta os helpers usados pelas models; nenhum import de `sqlalchemy` fora de `models.py`, `repository.py` e `creator/infrastructure/database/`.

**Verificação:**
- [ ] `pytest tests/test_module_boundaries.py tests/test_schema_inventory.py -q`.
- [ ] `grep -rn "JSONB\|PGUUID\|gen_random_uuid" src/creator` sem resultados.
- [ ] `make snapshot-contract` sem diff (fase sem mudança de schema).

**Dependências:** T1
**Arquivos prováveis:** `src/creator/infrastructure/database/enums.py`, `src/creator/infrastructure/database/naming.py`, `src/creator/infrastructure/database/types.py`
**Tamanho:** S

### T4 — Portabilidade das CHECK constraints e defaults

**Descrição:** Criar `constraints.py` com helpers portáveis e cobrir os 80 CHECKs do dump: 12 de moeda, 1 de UF, 1 de CEP, 1 de cor hexadecimal (todos com regex `~` no dump) e 3 `num_nonnulls`. Definir o mapa de defaults (`gen_random_uuid()`→`uuid4`, `now()`→`CURRENT_TIMESTAMP`).

**Critérios de aceite:**
- [ ] `currency_code_check`, `uf_check`, `zip_code_check`, `hex_color_check`, `exactly_one_of`, `at_most_one_of` com teste de equivalência semântica (aceitam e rejeitam os mesmos casos que o PostgreSQL).
- [ ] `CHECK_MAP` só aceita entrada válida (check existente no dump, tabela e constraint existentes no modelo e SQL portável
  declarado); a cobertura dos 80 CHECKs cresce junto com as tabelas e é medida por `check_missing` no orçamento.
- [ ] Nenhum `~`, `num_nonnulls` ou `gen_random_uuid` em model ou migration.
- [ ] Defaults documentados: UUID por `uuid4` em Python, timestamps por `CURRENT_TIMESTAMP`.

**Verificação:**
- [ ] `pytest tests/test_portable_schema.py tests/test_schema_inventory.py -q`.
- [ ] `grep -rn "num_nonnulls\| ~ '" src migrations` sem resultados.

**Dependências:** T3
**Arquivos prováveis:** `src/creator/infrastructure/database/constraints.py`, `tests/test_portable_schema.py`
**Tamanho:** M

### T19 — Snapshot como gate, índices no fixture e teste de upgrade anterior

**Descrição:** Fechar as duas brechas de verificação: `snapshot_contract.py` ganha `--check` e entra em `make check`; o fixture `schema_ddl.sql` passa a incluir os `CREATE INDEX` canônicos; e um teste de upgrade parte de `tests/contracts/schema_prev_ddl.sql` (schema da head anterior) para provar que uma revisão esquecida é detectada, já que `alembic check` sozinho é vacuous com a baseline `create_all`.

**Critérios de aceite:**
- [ ] `python scripts/snapshot_contract.py --check` falha quando o schema muda e não escreve arquivo.
- [ ] `make check` executa `snapshot-contract --check`.
- [ ] `schema_ddl.sql` contém tabelas **e** índices, ordenados e com nome; comparação canônica (EOL e espaço final apenas).
- [ ] `schema_prev_ddl.sql` carregado e estampado na revisão anterior; `alembic upgrade head` converge para `Base.metadata`.
- [ ] `migrations/env.py` com `compare_type=True` e `render_as_batch=True`.

**Verificação:**
- [ ] `make check` vermelho ao remover uma coluna de uma revisão (teste de mutação manual registrado na issue).
- [ ] `make snapshot-contract --check` verde após regenerar.
- [ ] `pytest tests/test_schema_inventory.py -q`.

**Dependências:** T2
**Arquivos prováveis:** `scripts/snapshot_contract.py`, `Makefile`, `migrations/env.py`, `tests/test_schema_inventory.py`, `tests/contracts/schema_prev_ddl.sql`, `tests/contracts/schema_ddl.sql`
**Tamanho:** M

### Checkpoint — Fase 0
- [ ] ADR-028 aceita e tracker consistente; épico 0057 alinhado.
- [ ] Comparador único em `final_schema.py`, usado pelo script e pelos testes.
- [ ] Orçamento de paridade com as oito dimensões, em igualdade com o estado atual.
- [ ] `snapshot-contract --check` no `make check`, com índices no fixture.
- [ ] Teste de upgrade anterior provando que revisão esquecida é detectada.
- [ ] Helpers de enum, nome e constraint com teste de equivalência.
- [ ] Revisão humana da ADR-028 e do orçamento antes da fase seguinte.

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

**Descrição:** Criar `brand_hashtags`, `brand_values`, `campaign_hashtags` e `campaign_voices`, com unicidade de hashtag/valor/voz por pai e FKs em cascata. `brand_business_details` fica em T22, que também adiciona `campaigns.brand_id` e os UNIQUE `(id, brand_id)` de campaigns/personas.

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

### T8 — `workspace_memberships` → `workspace_members` com migração de valores

**Descrição:** Renomear `workspace_memberships` → `workspace_members`, adicionar `status` (`member_status`) e `invited_by` (`ON DELETE SET NULL`), remover `deleted_at` e o CHECK associado, e trocar a unicidade parcial por `UNIQUE (workspace_id, user_id)` com os índices do dump. Migrar o repositório de soft delete para exclusão física. O vocabulário de `role` permanece como está nesta fatia.

**Critérios de aceite:**
- [ ] `RENAME_MAP` fica vazio (nomes alinhados) e o parâmetro `updated_at` continua íntegro.
- [ ] `deleted_at IS NOT NULL` vira `status = 'REMOVED'` antes de remover a coluna; consultas de autorização deixam de filtrar `deleted_at`.
- [ ] Tabela, índices e UNIQUE(workspace_id, user_id) conforme o dump.
- [ ] Revisão `0009_*` com rename e `0010_*` com backfill + drop de `deleted_at`; ambas com downgrade.
- [ ] Nenhuma referência ao nome ou aos valores antigos em `src`, `tests`, `migrations`.

**Verificação:**
- [ ] `grep -rn "workspace_memberships" src tests migrations scripts` sem resultados.
- [ ] `grep -rn '"admin"\|"owner"\|"viewer"' src/creator/domain src/creator/workspace` sem resultados.
- [ ] `pytest tests/ -q -k "workspace or member or auth"` verde.

**Dependências:** T4
**Arquivos prováveis:** `src/creator/workspace/models.py`, `src/creator/workspace/repository.py`, `src/creator/domain/auth.py`, `migrations/versions/0009_*.py`, `migrations/versions/0010_*.py`
**Tamanho:** M

### T21 — Vocabulário de `workspace_role` e autorização

**Descrição:** Trocar o vocabulário do papel de vínculo de `owner/admin/editor/viewer` para `OWNER/MANAGER/EDITOR/VIEWER` (com `admin→MANAGER`), ajustando `ROLE_RANK`, `minimum_role`, workers, serviços e testes de autorização. Inclui revisão de backfill dos valores existentes.

**Critérios de aceite:**
- [ ] `WorkspaceRole` com os quatro valores do dump e `ROLE_RANK` coerente.
- [ ] Nenhuma comparação com `"admin"`, `"owner"`, `"editor"` ou `"viewer"` minúsculos em código de autorização.
- [ ] Revisão com backfill `owner→OWNER`, `admin→MANAGER`, `editor→EDITOR`, `viewer→VIEWER` e downgrade inverso.
- [ ] Testes de autorização por papel cobrindo os quatro valores.

**Verificação:**
- [ ] `grep -rn '"admin"\|"owner"\|"viewer"' src/creator/domain src/creator/workspace src/creator/infrastructure/persistence` sem resultados de papel de workspace.
- [ ] `pytest tests/test_authorization_denials.py tests/test_activity_events.py -q`.
- [ ] `make check` verde.

**Dependências:** T8
**Arquivos prováveis:** `src/creator/domain/auth.py`, `src/creator/infrastructure/persistence/sql.py`, `src/creator/workspace/repository.py`, `src/creator/services/agents/runner.py`, `migrations/versions/0021_*.py`
**Tamanho:** M

### T22 — Chaves pai de campanhas/personas e `brand_business_details`

**Descrição:** Adicionar `campaigns.brand_id` (nullable enquanto não houver backfill), o UNIQUE `(id, brand_id)` e os índices de `brand_id` em campaigns e personas, e criar `brand_business_details` com as FKs compostas para `campaigns(id, brand_id)` e `personas(id, brand_id)`. É o pré-requisito de T9, T10 e T11.

**Critérios de aceite:**
- [ ] `campaigns.brand_id` presente, FK `CASCADE` e índice `ix_campaigns_brand_id`; UNIQUE `uq_campaigns_id_brand_id`.
- [ ] `personas` com UNIQUE `uq_personas_id_brand_id` e `ix_personas_brand_id`.
- [ ] `brand_business_details` com colunas, JSON `output`, FKs compostas e os cinco índices do dump.
- [ ] Revisão Alembic com `downgrade` funcional e guarda para banco novo.
- [ ] A dívida de `campaigns.brand_id` NULL (dump exige NOT NULL) fica declarada no orçamento até o backfill de T14.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` (upgrade anterior converge).
- [ ] Teste de introspecção das duas FKs compostas e do UNIQUE pai.
- [ ] `make snapshot-contract` e revisão do diff.

**Dependências:** T21
**Arquivos prováveis:** `src/creator/campaign/models.py`, `src/creator/persona/models.py`, `src/creator/brand/models.py`, `migrations/versions/0011_*.py`
**Tamanho:** M

### T9 — `planning` → `content_plans` + satélites

**Descrição:** Expand do redesenho de planejamento. Criar `content_plans` (11 colunas) e as satélites `content_plan_items` e `content_plan_special_dates`; a persona inline deixa de viver no plano e passa a apontar `personas`.

**Critérios de aceite:**
- [ ] `content_plans` com exatamente as 11 colunas e FKs do dump (brand, campaign, persona, created_by).
- [ ] `content_plan_items` (format, quantity) e `content_plan_special_dates` (special_date, label) com FK para o plano.
- [ ] `planning` permanece intacta (expand); repositório novo não reutiliza o legado.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py -q` → 3 ausentes (`captions`, `design_slides`, `image_resizes`).
- [ ] `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.

**Dependências:** T4, T22
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

**Dependências:** T4, T22
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

**Dependências:** T4, T22
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

### T23 — Migrar consumidores legados para os modelos finais

**Descrição:** Migrar Planning, PostStructure, DesignStructure e GeneratedImage (routers, services, repositórios e UoW) para `content_plans`, `posts`, `post_designs`, `design_slides` e `generated_images`, preservando o contrato HTTP ou versionando-o explicitamente. É pré-requisito do contract de T13.

**Critérios de aceite:**
- [ ] Nenhum router/service/repositório importa `Planning`, `PostStructure`, `DesignStructure` ou `GeneratedImage` legados.
- [ ] `docs/openapi.yaml` atualizado antes de mudança de payload; teste de paridade OpenAPI verde.
- [ ] Testes de API/e2e cobrindo planejamento, posts/estrutura e imagens passam com os novos modelos.
- [ ] Dados existentes continuam visíveis (backfill de T12) e nenhuma rota retorna 500.

**Verificação:**
- [ ] `grep -rn "post_structure_models\|planning_models\|design_structure_models" src/creator` sem resultados.
- [ ] `make check` e `make e2e` verdes.

**Dependências:** T12
**Arquivos prováveis:** `src/creator/planning/*`, `src/creator/post_structure/*`, `src/creator/design_structure/*`, `src/creator/generation/*`, `src/creator/uow.py`, `docs/openapi.yaml`
**Tamanho:** L (será fatiado por rota)

### T13 — Contract: remover as tabelas antigas

**Descrição:** Dropar `planning`, `post_structure`, `design_structure` e `generated_image`, remover o script de backfill e os consumidores remanescentes.

**Critérios de aceite:**
- [ ] Revisão `0013_*` remove as 4 tabelas; downgrade as recria vazias.
- [ ] Nenhum model, repositório, teste ou worker referencia as tabelas removidas.
- [ ] Relatório de paridade regenerado sem sobras de redesign.

**Verificação:**
- [ ] `grep -rn "post_structure\|design_structure\|generated_image\b" src tests workers` sem resultados.
- [ ] `make check` e `make e2e` verdes.

**Dependências:** T12, T23
**Arquivos prováveis:** `migrations/versions/0013_*.py`, `src/creator/**/models.py`, `docs/migration/schema-final-alignment.md`
**Tamanho:** S

### Checkpoint — Fase 3
- [ ] Backfill idempotente e contagens conferidas.
- [ ] Banco vazio e banco de dev convergem para o mesmo schema.
- [ ] `make e2e` verde após a remoção.

## Fase 4 — Alinhar as 31 tabelas comuns

### T24 — Lote A1: identidade, convites e notificações

**Descrição:** Alinhar `users`, `workspaces`, `workspace_invites` (com `role` como enum `workspace_role` e validação do payload), `workspace_invite_usages`, `notifications`, `notification_recipients`, `notification_preferences` e `user_devices` ao modelo final, incluindo OpenAPI e testes de contrato.

**Critérios de aceite:**
- [ ] As 8 tabelas sem divergência de coluna/nullability/tamanho no relatório (ou dívida justificada).
- [ ] `workspace_invites.role` vira enum com validação; `docs/openapi.yaml` atualizado.
- [ ] Enums dessas tabelas com vocabulário do dump.
- [ ] Fixtures de snapshot regenerados; testes de API atualizados.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py tests/test_api.py -q`.
- [ ] `make check` e `make e2e` verdes.

**Dependências:** T12
**Arquivos prováveis:** `src/creator/user/models.py`, `src/creator/workspace/models.py`, `src/creator/notification/models.py`, `src/creator/workspace/schemas.py`, `docs/openapi.yaml`, `migrations/versions/0015_*.py`
**Tamanho:** M

### T25 — Lote A2: brand, campanha e persona + backfill do brand_id

**Descrição:** Alinhar `brands`, `brand_colors`, `brand_assets`, `campaigns` e `personas` ao modelo final e tornar `campaigns.brand_id` obrigatório após o backfill (preenchido por `planning` em T12), com OpenAPI e testes.

**Critérios de aceite:**
- [ ] As 5 tabelas sem divergência de coluna/nullability/tamanho no relatório.
- [ ] `campaigns.brand_id` NOT NULL com backfill e downgrade seguros.
- [ ] Enums (`brand_asset_type`, `campaign_voice`, `persona_gender`, `age_range`) com vocabulário do dump.
- [ ] `docs/openapi.yaml` atualizado para payloads de brand/campaign/persona.

**Verificação:**
- [ ] `pytest tests/test_schema_inventory.py tests/test_api.py -q`.
- [ ] `make check` e `make e2e` verdes.

**Dependências:** T22, T24
**Arquivos prováveis:** `src/creator/brand/models.py`, `src/creator/campaign/models.py`, `src/creator/persona/models.py`, `docs/openapi.yaml`, `migrations/versions/0016_*.py`
**Tamanho:** M

### T14 — Lote A: identidade, notificações, brand, campanha, persona (13 tabelas)

**Descrição:** Alinhar `users`, `workspaces`, `workspace_invites` (incluindo `role` como enum `workspace_role` e validação do payload), `workspace_invite_usages`, `notifications`, `notification_recipients`, `notification_preferences`, `user_devices`, `brands`, `brand_colors`, `brand_assets`, `campaigns` e `personas` — colunas, nullability, tamanhos, enums e índices — usando `render_as_batch`.

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

### T20 — Triggers, funções e view do dump

**Descrição:** Inventariar as 69 funções/triggers e a view `charges_with_last_transaction` e classificar cada objeto em: portar como trigger SQLite, mover para a aplicação com teste equivalente, ou declarar fora de escopo com justificativa. Ledger de créditos e histórico append-only de assinatura são obrigatoriamente cobertos.

**Critérios de aceite:**
- [ ] Inventário versionado em `docs/migration/storage-objects-matrix.md` com uma linha por objeto e a classificação.
- [ ] Objetos de imutabilidade (`workspace_credit_transactions`, `subscription_history`), validação de lote e `updated_at` implementados como trigger SQLite ou como guarda de aplicação com teste que falha sem ela.
- [ ] View `charges_with_last_transaction` substituída por consulta equivalente com teste.
- [ ] Nenhum objeto sem classificação; os fora de escopo têm justificativa e risco escrito.

**Verificação:**
- [ ] `pytest tests/test_storage_objects.py -q` cobrindo cada guarda portada.
- [ ] `grep -c` do inventário igual ao número de objetos do dump (70).
- [ ] `make check`, `make security` e `make e2e` verdes.

**Dependências:** T15
**Arquivos prováveis:** `docs/migration/storage-objects-matrix.md`, `migrations/versions/0018_*.py`, `tests/test_storage_objects.py`
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
| `workspace_members` (hoje `workspace_memberships`) | renomear + alinhar | T8 |
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
| `brand_business_details` | criar | T22 |

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
| `content_plans` (hoje `planning`) | redesenhar (expand → contract) | T9 |
| `content_plan_items` | criar | T9 |
| `content_plan_special_dates` | criar | T9 |
| `posts` (hoje `post_structure`) | redesenhar (expand → contract) | T10 |
| `captions` | criar | T10 |
| `post_designs` (hoje `design_structure`) | redesenhar (expand → contract) | T10 |
| `design_slides` | criar | T10 |

#### Geração e Mídia

| Tabela final | Ação | Tarefa |
| --- | --- | --- |
| `generated_images` (hoje `generated_image`) | redesenhar (expand → contract) | T11 |
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
| Orçamento de paridade ficar stale ou crescer sem revisão | Alto | igualdade obrigatória: crescer falha, ficar stale falha; cada PR reduz na mesma diff |
| Snapshot sem índices esconder mudança de índice | Alto | `schema_ddl.sql` passa a incluir `CREATE INDEX`; `--check` no `make check` |
| `alembic check` vacuous pela baseline `create_all` | Alto | teste de upgrade a partir de `schema_prev_ddl.sql` + `compare_type`/`render_as_batch` |
| Triggers do ledger e do histórico de assinatura não serem portados | Alto | T20 obriga classificação e teste; imutabilidade não pode depender só de disciplina |
| `test_schema_migration_matrix` e `test_schema_models` quebrarem | Médio | atualizar matriz e o assert de `users.email` na mesma PR que muda schema |
| Extensão de auth (`password_hash`/`global_role`) ser removida por engano | Alto | exceção declarada na ADR-028 e no teste de paridade; T14 verifica consumidores |

## Questões abertas

1. **Existe banco com dados a preservar?** Se sim, a consolidação da baseline (T17) fica
   proibida e o backfill passa a ser obrigatório também para as 31 tabelas alinhadas.
2. **`settings` e `brand_settings`:** viram colunas em `workspaces`/`brands` ou permanecem como
   tabela chave-valor até existir UI de configuração? Muda o escopo de T16.
3. **`provider_customers`/`provider_subscriptions`:** remover (estado em
   `charge_transactions`/`fiscal_invoices`) ou manter como cache para idempotência e
   reconciliação?
4. **`generated_images.is_current`:** unicidade por `design_slide_id` (como o dump sugere) ou por
   `post`? O índice do dump é parcial e precisa de decisão explícita.
5. **Triggers do dump:** quais objetos aceitam virar guarda de aplicação em vez de trigger SQLite?
   A decisão é por objeto, em T20, e imutabilidade de ledger/histórico não pode ficar só na
   aplicação.

> Resolvidas na revisão da ADR-028: `users.password_hash`/`global_role` permanecem como extensão
> da ADR-020; o conjunto-alvo é de 71 tabelas até a ADR-029; `workspace_role` migra
> `admin→MANAGER`; nomes de índice explícitos do dump são preservados.

## Task list for tracker

```json
[
  {
    "id": "T1",
    "title": "ADR-028, épico e tracker",
    "description": "Registrar a estratégia de alinhamento (incrementais + squash final, expand→backfill→contract, teste de paridade, convenção de índices, gate de snapshot, enums e constraints portáveis) e amarrar épico 0057 e #159 às ADR-021/015.",
    "priority": "high",
    "depends_on": [],
    "phase": "Fase 0 — Contrato, paridade e portabilidade",
    "files": [
      "docs/adr/0028-sqlite-final-schema-alignment.md",
      "docs/ADR-ISSUE-TRACKER.md",
      "docs/issues/0057-sqlite-final-schema-alignment.md"
    ],
    "size": "S"
  },
  {
    "id": "T2",
    "title": "Comparador único e teste de paridade com orçamento",
    "description": "Extrair parse/compare para src/creator/infrastructure/database/final_schema.py, fazer o script usá-lo e adicionar ao inventário congelado os testes de oito dimensões com ADR_EXTENSIONS, LEGACY_RETENTION, RENAME_MAP, CHECK_MAP e orçamento de dívida que só diminui (schema_parity_budget.json).",
    "priority": "high",
    "depends_on": [
      "T1"
    ],
    "phase": "Fase 0 — Contrato, paridade e portabilidade",
    "files": [
      "src/creator/infrastructure/database/final_schema.py",
      "scripts/schema_parity_report.py",
      "tests/test_schema_inventory.py",
      "tests/contracts/creator_db_final.sql",
      "tests/contracts/schema_parity_budget.json"
    ],
    "size": "L"
  },
  {
    "id": "T3",
    "title": "Helpers portáveis de enum e nome de índice",
    "description": "Estender types.py (sem columns.py paralelo) com enums.py dos 52 vocabulários e naming.py para os 123 índices anônimos, preservando os 50 nomes explícitos do dump.",
    "priority": "high",
    "depends_on": [
      "T1"
    ],
    "phase": "Fase 0 — Contrato, paridade e portabilidade",
    "files": [
      "src/creator/infrastructure/database/enums.py",
      "src/creator/infrastructure/database/naming.py",
      "src/creator/infrastructure/database/types.py"
    ],
    "size": "S"
  },
  {
    "id": "T4",
    "title": "Portabilidade das CHECK constraints e defaults",
    "description": "Criar constraints.py com helpers para 12 CHECKs de moeda, UF, CEP, cor hexadecimal e 3 num_nonnulls, cobrindo os 80 CHECKs via CHECK_MAP, e documentar defaults uuid4/CURRENT_TIMESTAMP.",
    "priority": "high",
    "depends_on": [
      "T3"
    ],
    "phase": "Fase 0 — Contrato, paridade e portabilidade",
    "files": [
      "src/creator/infrastructure/database/constraints.py",
      "tests/test_portable_schema.py"
    ],
    "size": "M"
  },
  {
    "id": "T5",
    "title": "Conformidade, consentimento e interesses",
    "description": "Criar audit_logs, user_consents e persona_interests com FKs, UNIQUE e índices conforme o dump, mais revisão 0006 com downgrade.",
    "priority": "medium",
    "depends_on": [
      "T4"
    ],
    "phase": "Fase 1 — Criar tabelas",
    "files": [
      "src/creator/audit/models.py",
      "src/creator/user/models.py",
      "src/creator/persona/models.py",
      "migrations/versions/0006_*.py"
    ],
    "size": "S"
  },
  {
    "id": "T6",
    "title": "Satélites de Brand e Campanha",
    "description": "Criar brand_business_details, brand_hashtags, brand_values, campaign_hashtags e campaign_voices com UNIQUE por pai e FKs em cascata, mais revisão 0007.",
    "priority": "medium",
    "depends_on": [
      "T4"
    ],
    "phase": "Fase 1 — Criar tabelas",
    "files": [
      "src/creator/brand/models.py",
      "src/creator/campaign/models.py",
      "migrations/versions/0007_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T7",
    "title": "Satélites de Billing e Créditos",
    "description": "Criar plan_payment_methods, charge_transactions, fiscal_invoices, workspace_credit_lots e workspace_credit_lot_consumptions com CHECKs portáveis e ledger sem dupla contagem.",
    "priority": "medium",
    "depends_on": [
      "T4"
    ],
    "phase": "Fase 1 — Criar tabelas",
    "files": [
      "src/creator/billing/models.py",
      "src/creator/credit/models.py",
      "migrations/versions/0008_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T8",
    "title": "workspace_members: rename, status, invited_by e exclusão física",
    "description": "Renomear workspace_memberships para workspace_members, adicionar status e invited_by, remover deleted_at e o CHECK, trocar a unicidade parcial por UNIQUE (workspace_id, user_id) e migrar o repositório de soft delete para exclusão física. Vocabulário de role fica para T21.",
    "priority": "high",
    "depends_on": [
      "T4"
    ],
    "phase": "Fase 2 — Renomear e redesenhar (expand)",
    "files": [
      "src/creator/workspace/models.py",
      "src/creator/workspace/repository.py",
      "src/creator/notification/models.py",
      "migrations/versions/0009_workspace_members.py"
    ],
    "size": "M"
  },
  {
    "id": "T9",
    "title": "planning para content_plans e satélites",
    "description": "Expand do redesenho de planejamento: content_plans com 11 colunas, content_plan_items e content_plan_special_dates, mantendo planning intacta.",
    "priority": "high",
    "depends_on": [
      "T4",
      "T22"
    ],
    "phase": "Fase 2 — Renomear e redesenhar (expand)",
    "files": [
      "src/creator/planning/models.py",
      "src/creator/planning/repository.py",
      "migrations/versions/0010_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T10",
    "title": "post_structure e design_structure para posts, captions, post_designs e design_slides",
    "description": "Expand do redesenho editorial: posts com 17 colunas e CHECKs de aprovação/agendamento, captions versionadas, post_designs com format/ratio e design_slides ordenados.",
    "priority": "high",
    "depends_on": [
      "T4",
      "T22"
    ],
    "phase": "Fase 2 — Renomear e redesenhar (expand)",
    "files": [
      "src/creator/content/models.py",
      "src/creator/design_structure/models.py",
      "migrations/versions/0011_*.py",
      "docs/openapi.yaml"
    ],
    "size": "M"
  },
  {
    "id": "T11",
    "title": "generated_image para generated_images e image_resizes",
    "description": "Expand do redesenho de mídia: generated_images com 23 colunas e 9 CHECKs portadas, image_resizes com UNIQUE (source_image_id, ratio).",
    "priority": "high",
    "depends_on": [
      "T4",
      "T22"
    ],
    "phase": "Fase 2 — Renomear e redesenhar (expand)",
    "files": [
      "src/creator/generation/models.py",
      "migrations/versions/0012_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T12",
    "title": "Backfill dos 4 redesenhos",
    "description": "Script idempotente com relatório de contagens e invariantes copiando planning, post_structure, design_structure e generated_image para as tabelas novas, testado em SQLite temporário.",
    "priority": "high",
    "depends_on": [
      "T8",
      "T9",
      "T10",
      "T11"
    ],
    "phase": "Fase 3 — Backfill e contract",
    "files": [
      "scripts/backfill_redesigns.py",
      "tests/test_backfill_redesigns.py"
    ],
    "size": "M"
  },
  {
    "id": "T13",
    "title": "Contract: remover as tabelas antigas",
    "description": "Dropar planning, post_structure, design_structure e generated_image, remover o script de backfill e os consumidores remanescentes, com downgrade funcional.",
    "priority": "high",
    "depends_on": [
      "T12",
      "T23"
    ],
    "phase": "Fase 3 — Backfill e contract",
    "files": [
      "migrations/versions/0013_*.py",
      "docs/migration/schema-final-alignment.md"
    ],
    "size": "S"
  },
  {
    "id": "T14",
    "title": "Lote A (guarda-chuva): identidade, brand e campanha",
    "description": "Guarda-chuva da T14, dividida em T24 (identidade/convites/notificações) e T25 (brand/campanha/persona + backfill de campaigns.brand_id). Fecha quando ambas fecharem.",
    "priority": "medium",
    "depends_on": [
      "T13"
    ],
    "phase": "Fase 4 — Alinhar tabelas comuns",
    "files": [
      "src/creator/user/models.py",
      "src/creator/workspace/models.py",
      "src/creator/notification/models.py",
      "src/creator/brand/models.py",
      "src/creator/campaign/models.py",
      "src/creator/persona/models.py",
      "migrations/versions/0014_*.py",
      "docs/openapi.yaml"
    ],
    "size": "M"
  },
  {
    "id": "T15",
    "title": "Lote B: billing, créditos e cupons",
    "description": "Alinhar as 18 tabelas de billing, assinaturas, charges, invoices, refunds, providers, cupons e créditos, com bigint nos centavos e backfill dos campos novos.",
    "priority": "medium",
    "depends_on": [
      "T14"
    ],
    "phase": "Fase 4 — Alinhar tabelas comuns",
    "files": [
      "src/creator/billing/models.py",
      "src/creator/credit/models.py",
      "src/creator/coupon/models.py",
      "migrations/versions/0015_*.py",
      "docs/openapi.yaml"
    ],
    "size": "M"
  },
  {
    "id": "T16",
    "title": "ADR-029, 11 legadas e 2 tabelas sem alvo",
    "description": "Mapear cada tabela legada ao alvo final ou justificar retenção com prazo, remover as aprovadas, ajustar consumidores e decidir provider_customers e provider_subscriptions.",
    "priority": "medium",
    "depends_on": [
      "T15"
    ],
    "phase": "Fase 5 — Aposentadoria do legado",
    "files": [
      "docs/adr/0029-legacy-table-retirement.md",
      "migrations/versions/0017_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T17",
    "title": "Consolidar a baseline",
    "description": "Regenerar 0001_sqlite_baseline do metadata final, remover revisões intermediárias e provar convergência com make snapshot-contract sem diff.",
    "priority": "high",
    "depends_on": [
      "T13",
      "T15",
      "T16"
    ],
    "phase": "Fase 6 — Consolidação e fechamento",
    "files": [
      "migrations/versions/0001_sqlite_baseline.py",
      "docs/adr/0028-sqlite-final-schema-alignment.md"
    ],
    "size": "M"
  },
  {
    "id": "T18",
    "title": "Fechamento do épico",
    "description": "Regenerar relatório de paridade e OpenAPI, atualizar tracker, épico 0057 e #159 com evidência de CI e rodar os três gates finais.",
    "priority": "high",
    "depends_on": [
      "T17"
    ],
    "phase": "Fase 6 — Consolidação e fechamento",
    "files": [
      "docs/openapi.yaml",
      "docs/migration/schema-final-alignment.md",
      "docs/ADR-ISSUE-TRACKER.md"
    ],
    "size": "S"
  },
  {
    "id": "T19",
    "title": "Snapshot como gate, índices no fixture e teste de upgrade anterior",
    "description": "Adicionar --check ao snapshot_contract e ao make check, incluir CREATE INDEX no schema_ddl.sql, comparar bytes canônicos e provar com schema_prev_ddl.sql que uma revisão esquecida é detectada, com compare_type e render_as_batch no env.py.",
    "priority": "high",
    "depends_on": [
      "T2"
    ],
    "phase": "Fase 0 — Contrato, paridade e portabilidade",
    "files": [
      "scripts/snapshot_contract.py",
      "Makefile",
      "migrations/env.py",
      "tests/test_schema_inventory.py",
      "tests/contracts/schema_prev_ddl.sql"
    ],
    "size": "M"
  },
  {
    "id": "T20",
    "title": "Triggers, funções e view do dump",
    "description": "Inventariar as 69 funções/triggers e a view charges_with_last_transaction e classificar cada objeto em trigger SQLite, guarda de aplicação com teste ou fora de escopo justificado, cobrindo obrigatoriamente ledger e histórico append-only.",
    "priority": "high",
    "depends_on": [
      "T15"
    ],
    "phase": "Fase 5 — Aposentadoria do legado",
    "files": [
      "docs/migration/storage-objects-matrix.md",
      "migrations/versions/0018_*.py",
      "tests/test_storage_objects.py"
    ],
    "size": "M"
  },
  {
    "id": "T21",
    "title": "Vocabulário de workspace_role e autorização",
    "description": "Trocar owner/admin/editor/viewer por OWNER/MANAGER/EDITOR/VIEWER, ajustar ROLE_RANK, minimum_role, workers e testes, com backfill e downgrade do vocabulário.",
    "priority": "high",
    "depends_on": [
      "T8"
    ],
    "phase": "Fase 2 — Renomear e redesenhar (expand)",
    "files": [
      "src/creator/domain/auth.py",
      "src/creator/infrastructure/persistence/sql.py",
      "src/creator/workspace/repository.py",
      "src/creator/services/agents/runner.py",
      "migrations/versions/0021_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T22",
    "title": "Chaves pai de campanhas/personas e brand_business_details",
    "description": "Adiciona campaigns.brand_id, UNIQUE (id, brand_id) e índices de brand_id em campaigns/personas, e cria brand_business_details com FKs compostas para campaigns/personas.",
    "priority": "high",
    "depends_on": [
      "T21"
    ],
    "phase": "Fase 2 — Renomear e redesenhar (expand)",
    "files": [
      "src/creator/campaign/models.py",
      "src/creator/persona/models.py",
      "src/creator/brand/models.py",
      "migrations/versions/0011_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T23",
    "title": "Migrar consumidores legados para os modelos finais",
    "description": "Migrar routers, services, repositórios e UoW de Planning/PostStructure/DesignStructure/GeneratedImage para content_plans, posts, post_designs, design_slides e generated_images, preservando ou versionando o contrato HTTP.",
    "priority": "high",
    "depends_on": [
      "T12"
    ],
    "phase": "Fase 3 — Backfill e contract",
    "files": [
      "src/creator/planning/*",
      "src/creator/post_structure/*",
      "src/creator/design_structure/*",
      "src/creator/generation/*",
      "src/creator/uow.py",
      "docs/openapi.yaml"
    ],
    "size": "L"
  },
  {
    "id": "T24",
    "title": "Lote A1: identidade, convites e notificações",
    "description": "Alinhar users, workspaces, workspace_invites (role enum + validação), invite_usages, notifications, recipients, preferences e user_devices; OpenAPI e testes.",
    "priority": "high",
    "depends_on": [
      "T12"
    ],
    "phase": "Fase 4 — Alinhar tabelas comuns",
    "files": [
      "src/creator/user/models.py",
      "src/creator/workspace/models.py",
      "src/creator/notification/models.py",
      "src/creator/workspace/schemas.py",
      "docs/openapi.yaml",
      "migrations/versions/0015_*.py"
    ],
    "size": "M"
  },
  {
    "id": "T25",
    "title": "Lote A2: brand, campanha e persona + backfill do brand_id",
    "description": "Alinhar brands, brand_colors, brand_assets, campaigns e personas e tornar campaigns.brand_id NOT NULL após backfill, com OpenAPI e testes.",
    "priority": "high",
    "depends_on": [
      "T22",
      "T24"
    ],
    "phase": "Fase 4 — Alinhar tabelas comuns",
    "files": [
      "src/creator/brand/models.py",
      "src/creator/campaign/models.py",
      "src/creator/persona/models.py",
      "docs/openapi.yaml",
      "migrations/versions/0016_*.py"
    ],
    "size": "M"
  }
]
```