# ADR-028: Alinhamento do schema SQLite ao Creator_DB_final.sql

- Status: accepted
- Fonte: decisão da Fase 2 (schema), 2026-11-09
- Tracker: [docs/issues/0057](../issues/0057-sqlite-final-schema-alignment.md) / [#159](https://github.com/labLima/creator-backend/issues/159)
- ADRs relacionadas: [ADR-020](0020-self-hosted-authentication.md) (autenticação própria), [ADR-021](0021-sqlite-default-database.md) (SQLite como banco padrão), [ADR-015](0015-database-diagram-alignment.md) (alinhamento ao diagrama)
- Issues de implementação: `SHC-2` a `SHC-20` no board `SHC` do Shared Context; plano em [`tasks/plan-sqlite-final-schema.md`](../../tasks/plan-sqlite-final-schema.md)

## Contexto

A troca de PostgreSQL por SQLite foi concluída na ADR-021. O que falta é a paridade entre o
schema vivo e a modelagem final. O dump `docs/migration/Creator_DB_final.sql` (sha256
`619512b778e1f03a315efe5d7d8710a5a540442b5df66ddc144b78e915bbb583`) declara **54 tabelas,
52 tipos ENUM, 173 índices, 101 foreign keys, 80 CHECK
constraints, 69 funções/triggers e 1 view**; o metadata tem **53 tabelas** e diverge em **31
tabelas comuns**, além de **18 tabelas ausentes**, **1 rename com migração de valores** e **4
redesenhos de modelo**.

O banco é pré-produção, mas a decisão de reconstruir ou migrar é irreversível para quem já tem
volume, então precisa de condição explícita de inversão.

### Fatos que restringem a decisão

1. **A modelagem final não é a única fonte de verdade.** Ela não contém `users.password_hash`
   nem `users.global_role`, que a ADR-020 exige para autenticação própria. Também não contém as
   quatro extensões de ADR já aceitas (`auth_sessions`, `outbox_events`, `activity_events`,
   `content_text_versions`) nem as 13 tabelas ainda sem alvo (`11 legadas + 2 de provider`).
2. **`alembic check` é hoje vacuous.** `0001_sqlite_baseline.upgrade()` chama
   `Base.metadata.create_all()` com o metadata corrente; um banco novo já nasce com as colunas
   novas antes das revisões seguintes rodarem, então `scripts/check_migrations.py` não detecta
   uma revisão esquecida. `tests/test_schema_inventory.py` documenta esse mesmo modo de falha.
3. **O snapshot de schema não vê índices.** `scripts/snapshot_contract.py` emite apenas
   `CreateTable` e `tests/contracts/schema_ddl.sql` não tem `CREATE INDEX`; mudanças só de
   índice são invisíveis. O snapshot também não é executado por `make check`.
4. **Índices anônimos não existem em SQLite.** `CREATE INDEX ON tabela (...)` é sintaxe
   inválida; todo índice precisa de nome. Dos 173 índices do dump, 50 têm nome explícito
   (`idx_m8_*`, `uq_*`) e 123 são anônimos.
5. **As FKs compostas não são todas de `workspace_id`.** São 10: 6 incluem `workspace_id` e 4
   incluem `brand_id` (`coupon_redemptions`/`workspace_credit_transactions` → `orders`,
   `workspace_credit_lot_consumptions` → `workspace_credit_lots`, e duas de
   `brand_business_details` → `campaigns`/`personas`). Cada uma exige UNIQUE composta no alvo
   com a mesma chave.
6. **Os CHECKs usam operadores que SQLite não tem.** São 80 CHECKs; 15 usam regex PostgreSQL
   (`~`): 12 de moeda, 1 de UF, 1 de CEP e 1 de cor hexadecimal. Outros 3 usam
   `num_nonnulls(...)`.
7. **O dump tem lógica de armazenamento, não só tabelas.** 69 funções/triggers (imutabilidade do
   ledger de créditos, validação de lote, `updated_at`, snapshot de cupom, histórico
   append-only de assinatura) e a view `charges_with_last_transaction` não são expressos por
   models.
8. **Tabelas do modelo final remapeiam dados, não só nomes.** `workspace_role` no dump é
   `OWNER/MANAGER/EDITOR/VIEWER`; o código usa `owner/admin/editor/viewer`. `workspace_members`
   troca `deleted_at` por `status`, e várias consultas filtram `deleted_at IS NULL`.

## Decisão

### 1. Incremental agora, baseline consolidada no fim, com condição de inversão

O trabalho usa revisões Alembic encadeadas a partir da head atual (`0005_content_text_versions`),
uma por tarefa, e a fase final regenera `0001_sqlite_baseline` e remove as revisões
intermediárias. A prova de equivalência é `make snapshot-contract --check` sem diff.

**Condição de inversão:** se existir banco com dados a preservar, a consolidação fica proibida e
a estratégia vira migração incremental permanente, com backfill obrigatório também nas 31
tabelas alinhadas.

### 2. A modelagem final é a referência, com exceções declaradas

O conjunto-alvo **não é 54 tabelas**: é `54 do dump` + `4 extensões de ADR` + `13 tabelas ainda
sem alvo` = **71 tabelas** durante a execução, caindo para 58 quando a ADR-029 decidir as 13. As
exceções são constantes declaradas no teste de paridade, nunca condições espalhadas:

- **Extensões de ADR preservadas:** `auth_sessions`, `outbox_events`, `activity_events`,
  `content_text_versions`.
- **Extensão de autenticação (emenda à ADR-020):** `users.password_hash` e `users.global_role`
  permanecem; são a única fonte de credencial local. `users.external_id` é absorvido por
  `users.auth_provider_id` na migração, e `users.cnpj`/`users.cpf` são removidos se não tiverem
  consumidor (verificado em T14).
- **Tabelas sem alvo:** `provider_customers` e `provider_subscriptions`, decididas na ADR-029.

Colunas exigidas pelo dump e ausentes por decisão de produto (por exemplo `users.email`
`varchar(254)`) são migradas; o `String(320)` atual deixa de valer e o teste
`tests/test_schema_models.py` é atualizado na mesma PR.

### 3. Expand → backfill → contract, incluindo o rename

Migrations are frozen history: they must not import live enums or model
constants whose meaning changes later. Migration `0009` stores `role` as a plain
varchar precisely so `0010` can map the vocabulary and rebuild the table with the
final enum; importing the live enum there would have rewritten the past.

Nem `workspace_memberships` é rename sem migração: além do nome, muda o vocabulário de `role`,
entra `status`, sai `deleted_at`. As cinco mudanças seguem três etapas em PRs separados:

1. **expand** — criar tabelas/colunas novas ao lado das antigas, sem remover nada;
2. **backfill** — script idempotente que copia e normaliza dados (`owner→OWNER`,
   `admin→MANAGER`, `deleted_at IS NOT NULL→status=…`), com relatório de contagens;
3. **contract** — remover tabelas/colunas antigas e o script.

Nenhum PR mistura expand e contract. **O `downgrade` do contract recria tabelas vazias, não
devolve dados**; a reversão de dados depende do backup, e isso é explicitado na issue de
execução. Remoção de tabela só ocorre depois de models, DTOs, OpenAPI, testes e consumidores
migrados, como exige a ADR-015.

### 4. Fonte de verdade e comparador únicos

`docs/migration/Creator_DB_final.sql` é a fonte versionada. O parser e a comparação vivem em
`src/creator/infrastructure/database/final_schema.py`, importáveis por script e testes (o
projeto já instala `src` em modo editável; `scripts/` e `tests/` não se importam entre si).
`scripts/schema_parity_report.py` passa a ser um fino invólucro desse módulo. Duas
implementações de parsing seriam duas verdades — proibido.

### 5. Oito dimensões de paridade, com ratchet explícito

As asserções ficam em `tests/test_schema_inventory.py`, junto dos fixtures congelados, e cobrem:
tabelas; colunas e PK; nullability, tamanho de `String` e largura `Integer`/`BigInteger`; enums;
índices e UNIQUE; FKs (colunas locais, alvo, colunas do alvo, `ON DELETE`); CHECKs; e presença
de defaults.

Como o alinhamento é incremental e o gate precisa ficar verde, o estado conhecido vive em
`tests/contracts/schema_parity_budget.json`, com `dump_sha256`, contagem por categoria e
`gap_digest`. O teste exige **igualdade** com o orçamento:

- divergência maior que o orçamento → falha (`schema debt GREW`);
- divergência menor que o orçamento → falha (`ratchet stale: reduza o orçamento nesta PR`).

Assim cada PR que corrige uma tabela reduz uma contagem e o digest na mesma diff — a evidência
de progresso é o próprio diff. `xfail`, skip e allowlist por tabela são rejeitados porque não
forçam a limpeza. Ao final, todas as contagens são zero e o arquivo de orçamento fica só com os
hashes.

CHECKs não são comparáveis por texto entre PostgreSQL e SQLite. O módulo declara
`CHECK_MAP`, mapeando cada CHECK do dump ao CHECK portável equivalente, e o teste falha se
algum CHECK do dump ficar sem entrada ou se a entrada apontar para uma coluna inexistente.

### 6. Snapshot passa a ser gate e a incluir índices

`scripts/snapshot_contract.py` ganha `--check` (não escreve, falha se divergir) e
`make check` passa a rodar `snapshot-contract --check`. O fixture `tests/contracts/schema_ddl.sql`
passa a conter, além dos `CREATE TABLE`, os `CREATE INDEX` canônicos — ordenados e com nome —,
porque sem isso mudanças só de índice são invisíveis. A comparação deixa de colapsar todo
whitespace: normaliza apenas fim de linha e espaço final, comparando bytes canônicos. Foi
exatamente essa normalização frouxa que escondeu o gerador emitindo espaço final.

### 7. Verificação de migração deixa de ser vacuous

Duas medidas, ambas na fase 0:

- `migrations/env.py` passa a usar `compare_type=True` e `render_as_batch=True`;
- um teste de upgrade a partir de schema anterior: `tests/contracts/schema_prev_ddl.sql` (cópia
  canônica do schema na head anterior) é carregado num banco, estampado na revisão
  correspondente, e `alembic upgrade head` roda; o resultado precisa bater com `Base.metadata` e
  com o orçamento. O fixture é renovado a cada fase que muda schema.

A baseline congelada (`create_all` a partir de um snapshot de metadata) é a alternativa
descartada por ora: ela conflita com `0001_sqlite_baseline` já aplicada em bancos existentes e
seria mais invasiva que o teste de upgrade.

### 8. Índices: preservar nomes explícitos, nomear só os anônimos

Os 50 índices com nome no dump mantêm o nome (`idx_m8_*`, `uq_*`), porque renomear quebraria a
paridade com a fonte. A convenção `ix_<tabela>_<colunas>` e `uq_<tabela>_<colunas>` vale apenas
para os 123 anônimos, e o mapeamento fica no teste. A afirmação anterior de que SQLite aceita
nomes automáticos está errada e não se aplica.

### 9. Portabilidade de constraints

FKs precisam estar nas models (SQLite não aceita `ALTER TABLE ... ADD CONSTRAINT`); as 10
compostas exigem UNIQUE composta no alvo com a chave exata. O `ON DELETE` é preservado (40
CASCADE, 31 RESTRICT, 30 SET NULL).

Os 15 CHECKs com regex viram helpers com teste de equivalência: moeda (`GLOB '[A-Z][A-Z][A-Z]'`),
UF, CEP e cor hexadecimal. Os 3 `num_nonnulls` viram soma de `CASE WHEN ... IS NOT NULL`, com
helper `exactly_one_of`/`at_most_one_of`. `gen_random_uuid()` vira default Python `uuid4` e
`now()` vira `CURRENT_TIMESTAMP`/helper UTC.

### 10. Enums com vocabulário 1:1

Os 52 tipos viram `Enum(native_enum=False, create_constraint=True)` ou `String` + `CHECK`, num
módulo único de constantes (`creator/infrastructure/database/enums.py`) importado pelas models.
O vocabulário é idêntico ao do dump, inclusive valores sem uso previsto.

### 11. Triggers, funções e view precisam de decisão própria

As 69 funções/triggers e a view não entram na paridade tabela-coluna, mas também não
podem desaparecer silenciosamente: eles hoje sustentam imutabilidade do ledger, validação de
lote, `updated_at`, snapshot de cupom e histórico append-only. A tarefa T19 inventaria objeto a
objeto e classifica em (a) portar como trigger SQLite, (b) mover para a aplicação com teste
equivalente, ou (c) declarar fora de escopo com justificativa. Nenhum objeto fica sem
classificação; os invariantes do ledger e do histórico de assinatura são obrigatoriamente
cobertos por (a) ou (b).

### 12. Rastreabilidade

ADR-028 é a decisão primária desta frente; ADR-015 e ADR-021 são relacionadas. `docs/issues/0057`
e o tracker passam a apontar ADR-028 como primária. A ADR-029 (aposentadoria do legado) é criada
em T16, não antes, e o conjunto de 71 tabelas só reduz depois dela.

## Consequências

O schema ganha uma definição única e verificável, com paridade automatizada, orçamento de dívida
que só diminui e diff de contrato revisável em cada PR. O custo é volume de PRs e a disciplina de
regenerar snapshot, orçamento e o fixture de upgrade em cada mudança de schema.

Efeitos colaterais já conhecidos, que precisam ser tratados nas mesmas PRs:

- `tests/test_schema_migration_matrix.py` exige que toda tabela do metadata apareça em
  `docs/SCHEMA-MIGRATION-MATRIX.md`; as 18 tabelas novas obrigam atualizar a matriz.
- `tests/test_schema_models.py` fixa `users.email` em 320; passa a 254.
- `tests/contracts/schema_tables.json` e `schema_ddl.sql` mudam em quase toda tarefa.
- `ALTER TABLE` limitado do SQLite exige `render_as_batch`/`batch_alter_table`.
- A ordem de criação respeita dependências: satélite depois do pai, FK composta depois da UNIQUE
  composta no alvo.
- `docs/openapi.yaml` é atualizado antes de mudança de payload HTTP.
- `tests/test_module_boundaries.py` continua valendo: tabela nova nasce em `<entity>/models.py` +
  `repository.py`.

## Inconsistências conhecidas do dump

Duas declarações da modelagem final não são aplicáveis literalmente e foram
traduzidas com decisão registrada:

- `fiscal_invoices.currency` tem CHECK `^[a-z]{3}$` e default `'BRL'`, o que se
  contradiz; o helper portável aplica maiúsculas, coerente com o default e com as
  demais tabelas.
- `uq_captions_current` usa `WHERE is_current AND deleted_at IS NULL`, mas
  `captions` não tem `deleted_at`; o índice filtra apenas `is_current` para continuar
  válido no SQLite, e a divergência aparece no orçamento de paridade.

## Fora de escopo

- Reintroduzir PostgreSQL/MySQL como banco principal.
- ETL de dados PostgreSQL para SQLite (decisão C1, #99).
- Redesenhar a modelagem final ou criar entidades de produto novas.
- Interface do Lovable.
- Paridade de texto SQL literal de CHECKs entre PostgreSQL e SQLite; a paridade é estrutural e de
  vocabulário, com `CHECK_MAP` declarado.
