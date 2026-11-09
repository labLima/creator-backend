# ADR-028: Alinhamento do schema SQLite ao Creator_DB_final.sql

- Status: accepted
- Fonte: decisão da Fase 2 (schema), 2026-11-09
- Tracker: [docs/issues/0057](../issues/0057-sqlite-final-schema-alignment.md) / [#159](https://github.com/labLima/creator-backend/issues/159)
- ADRs relacionadas: [ADR-021](0021-sqlite-default-database.md) (SQLite como banco padrão), [ADR-015](0015-database-diagram-alignment.md) (alinhamento ao diagrama)
- Issues de implementação: `SHC-2` a `SHC-19` no board `SHC` do Shared Context; plano em [`tasks/plan-sqlite-final-schema.md`](../../tasks/plan-sqlite-final-schema.md)

## Contexto

A troca de PostgreSQL por SQLite foi concluída na ADR-021: `DATABASE_URL` padrão
`sqlite+pysqlite:///./.local/db/creator.db`, `PRAGMA foreign_keys=ON`/WAL/busy_timeout,
baseline `0001_sqlite_baseline` criada por `Base.metadata.create_all()` e migrations
PostgreSQL arquivadas em `migrations/legacy_postgres/`.

O que não foi concluído é a paridade entre o schema vivo e a modelagem final. O dump
`docs/migration/Creator_DB_final.sql` (sha256 `619512b7…b583`) declara **54 tabelas, 52
tipos ENUM, 173 índices, 101 foreign keys e 80 CHECK constraints**; o metadata tem **53
tabelas** e diverge em **31 tabelas comuns**, além de **18 tabelas ausentes**, **1 rename
viável** e **4 redesenhos de modelo**. O relatório
[`docs/migration/schema-final-alignment.md`](../migration/schema-final-alignment.md) mede o
delta e é regenerável por `scripts/schema_parity_report.py`.

O banco é pré-produção. Ainda assim, a decisão de reconstruir ou migrar é irreversível para
quem já tem volume, então precisa de condição explícita de inversão.

## Decisão

### 1. Incremental agora, baseline única no fim, com condição de inversão

O trabalho é executado em revisões Alembic encadeadas a partir da head atual
(`0005_content_text_versions`), uma por tarefa, para que cada PR fique verde. A fase final
regenera `0001_sqlite_baseline` do metadata final e remove as revisões intermediárias,
produzindo uma baseline única. O `make snapshot-contract` sem diff é a prova de que o
squash preservou o schema.

**Condição de inversão:** se existir banco com dados a preservar, a consolidação da baseline
fica proibida e a estratégia vira migração incremental permanente, com backfill obrigatório
também para as 31 tabelas alinhadas.

### 2. Expand → backfill → contract para as mudanças de modelo

As quatro mudanças não são renames: `planning` (24 colunas) → `content_plans` (11) +
`content_plan_items` + `content_plan_special_dates`; `post_structure` (18) → `posts` (17) +
`captions` + `post_designs` + `design_slides`; `design_structure` (5) → `post_designs` (6);
`generated_image` (11) → `generated_images` (23) + `image_resizes`. Cada uma segue três
etapas em PRs separados:

1. **expand** — criar as tabelas novas ao lado das antigas, sem remover nada;
2. **backfill** — script idempotente que copia os dados e reporta contagens e invariantes;
3. **contract** — remover as tabelas antigas e o script.

Nenhum PR mistura expand e contract. O rollback de cada etapa é o `downgrade` da própria
revisão. O único rename simples é `workspace_memberships` → `workspace_members` (7 → 8
colunas), que não precisa de expand.

### 3. Fonte de verdade versionada

`docs/migration/Creator_DB_final.sql` é a fonte da modelagem final, versionada no
repositório. `scripts/schema_parity_report.py` é a única implementação de comparação contra
`Base.metadata` e gera o relatório de paridade. Nenhuma issue pode declarar paridade sem
rodar esse script.

### 4. Teste de paridade no inventário congelado

As asserções de paridade vivem em `tests/test_schema_inventory.py`, o mesmo módulo que já
congela o schema, para não existirem dois parsers de DDL. O módulo ganha a fixture
`tests/contracts/creator_db_final.sql` (cópia com sha256 verificado no teste) e asserta seis
dimensões contra `Base.metadata`:

1. conjunto exato de tabelas (54 finais + 4 extensões declaradas);
2. conjunto de colunas por tabela;
3. nullability e tamanho de `String` por coluna;
4. vocabulário de enum por coluna;
5. índices por nome, colunas ordenadas, unicidade e predicado parcial;
6. foreign keys por colunas, alvo e `ON DELETE`.

As exceções (extensões de ADR e retenções de legado) ficam em constantes declaradas no
módulo, nunca em condições espalhadas. As falhas agregam todas as divergências com contagem
por categoria, para um único diagnóstico por execução.

### 5. Nomes de índice são contrato

O snapshot DDL precisa ser determinístico e 123 dos 173 índices do dump são anônimos.
Todo índice passa a seguir `ix_<tabela>_<colunas>` e `uq_<tabela>_<colunas>`. Índice
anônimo no dump recebe nome na metadata e o mapeamento correspondente é registrado no
teste de paridade, resolvendo a divergência no sentido metadata → dump.

### 6. `make snapshot-contract` é gate de toda PR que muda schema

Qualquer mudança de schema regenera `tests/contracts/schema_tables.json` e
`tests/contracts/schema_ddl.sql` **na mesma PR**, com o diff revisado. O diff é a evidência
auditável da mudança; separar em outra PR quebra a rastreabilidade e elimina a revisão.

### 7. Portabilidade de constraints é trabalho explícito

SQLite não aceita `ALTER TABLE ... ADD CONSTRAINT`, então as 101 FKs do dump precisam estar
nas models para valerem no baseline criado por `create_all()`. Dez delas são **compostas e
incluem `workspace_id`**, o que exige UNIQUE composta com a mesma chave no alvo. O `ON
DELETE` do dump (40 CASCADE, 31 RESTRICT, 30 SET NULL) é preservado.

Das 80 CHECK constraints, 15 usam regex PostgreSQL (`currency ~ '^[A-Z]{3}$'`) e 3 usam
`num_nonnulls(...)`. Ambas são traduzidas por helpers em
`creator/infrastructure/database/` para expressões SQLite (`GLOB`/`LIKE`/`length`/`upper` e
soma de `CASE WHEN ... IS NOT NULL`), com teste de equivalência semântica por helper.
`gen_random_uuid()` vira default Python `uuid4` e `now()` vira `CURRENT_TIMESTAMP`/helper UTC.

### 8. Enums com vocabulário 1:1

Os 52 tipos ENUM viram `Enum(native_enum=False, create_constraint=True)` ou `String` +
`CHECK`, definidos num módulo único de constantes importado pelas models. O vocabulário
precisa ser idêntico ao do dump, inclusive valores ainda sem uso previsto; divergência de
valor falha o teste de paridade.

### 9. Preservação e aposentadoria

Quatro tabelas são extensões de ADR e não existem no modelo final, permanecendo como
exceção declarada: `auth_sessions`, `outbox_events`, `activity_events`,
`content_text_versions`. As 11 tabelas legadas e as 2 sem alvo no modelo final
(`provider_customers`, `provider_subscriptions`) são decididas na **ADR-029**, com
mapeamento tabela → alvo, ordem de remoção e verificação de consumidores.

## Consequências

O schema passa a ter uma definição única e verificável, com paridade automatizada e diff de
contrato revisável em cada PR. O custo é volume de PRs: 18 tarefas, com pelo menos uma
revisão Alembic por tarefa que muda schema, e a necessidade de regenerar os fixtures em cada
uma.

A consolidação da baseline reduz dívida, mas é destrutiva para bancos existentes; por isso
depende da condição de inversão do item 1 e de procedimento documentado de reset do banco de
dev.

Cuidados obrigatórios:

- `ALTER TABLE` limitado do SQLite exige `render_as_batch`/`batch_alter_table` nas alterações
  de coluna (lotes A e B).
- A ordem de criação respeita dependências: satélites só entram depois do pai; FK composta só
  depois da UNIQUE composta no alvo.
- `docs/openapi.yaml` é atualizado antes de qualquer mudança de payload HTTP (membership
  status, posts com aprovação/agendamento, créditos).
- `tests/test_module_boundaries.py` continua valendo: tabela nova nasce em
  `<entity>/models.py` + `repository.py`.

## Fora de escopo

- Reintroduzir PostgreSQL/MySQL como banco principal.
- ETL de dados PostgreSQL para SQLite (decisão C1, #99).
- Redesenhar a modelagem final ou criar entidades de produto novas.
- Interface do Lovable.
