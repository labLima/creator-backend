# ADR-031: Aposentadoria das tabelas legadas e das tabelas sem alvo

- Status: accepted
- Fonte: T16 do plano de alinhamento do schema (`SHC-17`), 2026-11-13
- Tracker: [docs/issues/0060](../issues/0060-sqlite-final-schema-alignment.md) / [#164](https://github.com/labLima/creator-backend/issues/164)
- ADR primária da frente: [ADR-030](0030-sqlite-final-schema-alignment.md) (alinhamento ao `Creator_DB_final.sql`)
- ADRs relacionadas: [ADR-014](0014-agent-workflow.md) e [ADR-018](0018-event-driven-agent-pipeline.md) (estado durável do Agent Workflow), [ADR-019](0019-credit-ledger.md) (ledger append-only), [ADR-020](0020-self-hosted-authentication.md) (autenticação própria), [ADR-021](0021-sqlite-default-database.md) (SQLite como banco padrão), [ADR-025](0025-generation-independente-com-especialistas.md) (Generation Jobs independentes)
- Issues de implementação: [#164](https://github.com/labLima/creator-backend/issues/164) (`SHC-17`); épico [#159](https://github.com/labLima/creator-backend/issues/159)

## Contexto

A ADR-030 fechou o alinhamento à modelagem final: as 54 tabelas do dump estão no
metadata, com colunas, enums, índices, FKs e CHECKs verificados por um orçamento de
paridade que só diminui. Ficaram fora do alvo, por decisão adiada, **13 tabelas**:

- **11 legadas**, ainda escritas por consumidores vivos (workers de geração, agent
  workflow, settings de usuário e brand). Elas não existem em
  `docs/migration/Creator_DB_final.sql`, mas também não podem ser dropadas enquanto
  houver escritor — a remoção exige migrar o consumidor, não só apagar a tabela.
- **2 sem alvo**: `provider_customers` e `provider_subscriptions`, um cache do lado
  do provider que a modelagem final nunca declarou. A ADR-030 registrou que a
  decisão é desta ADR, e que uma tabela retida precisa virar exceção declarada no
  teste de paridade em vez de dívida silenciosa.

A ADR-030 também deixou uma exceção de transição explícita: o UNIQUE
`brands(id, workspace_id)` existe porque cinco tabelas legadas
(`contents`, `assets`, `projects`, `generations`, `agent_workflow_runs`) declaram FK
composta para `brands`. O dump não declara esse UNIQUE.

O banco é pré-produção (ADR-021), então a decisão é reversível em dados apenas por
backup: não há ETL de PostgreSQL para SQLite (decisão C1, [#99](https://github.com/labLima/creator-backend/issues/99)).

## Decisão

### 1. Onze tabelas legadas são retidas com prazo, não por omissão

As 11 legadas **permanecem no metadata** com destino declarado e **prazo de
retenção até 2027-06-30**. O prazo é único por decisão: uma única janela de revisão,
reavaliada obrigatoriamente na T18 (fechamento do épico
[#159](https://github.com/labLima/creator-backend/issues/159)), em vez de 11
calendários independentes que ninguém acompanha. Vencido o prazo sem consumidor
migrado, a tabela entra em uma issue de remoção própria — retenção vencida não se
renova por silêncio.

Nenhuma das 11 é removida nesta entrega: cada uma tem escritor vivo, e a ordem
`expand → backfill → contract` da ADR-030 (decisão 3) exige que o consumidor seja
migrado antes do `DROP TABLE`.

As 11 retidas são **`DOMAIN_EXTENSIONS`** (extensões de domínio) declaradas no
vocabulário do tracker: o prazo é uma janela de reavaliação, não uma fila de remoção
automática. Uma tabela só sai se o consumidor for migrado ou se uma nova ADR
explicitamente encerrar a extensão. A T23 migrou os leitores de `planning`,
`post_structure`, `design_structure` e `generated_image`; as 11 restantes são
justamente as que ainda têm escrita de worker, preferência de usuário ou CRUD legado.

### 2. As duas tabelas de provider são removidas

`provider_customers` e `provider_subscriptions` saem do schema e do metadata na
revisão `0037_retire_provider_tables`. A justificativa é a modelagem final, não
conveniência:

- o dump declara `billing_accounts.external_id`/`external_code` e
  `subscriptions.external_id`/`external_code` — o identificador do provider vive na
  própria entidade de negócio, não em uma tabela de cache paralela;
- `provider_webhook_events`, `provider_idempotency_keys` e `provider_disputes`
  continuam existindo: são fatos do provider auditáveis, e o dump os declara. A
  remoção atinge só as duas linhas de cache;
- a superfície HTTP das duas coleções sai junto (10 operações CRUD): uma rota cuja
  tabela não existe não pode responder. O restante da superfície de provider
  (`webhook-events`, `idempotency-keys`, `disputes`) não muda.

### 3. `brands(id, workspace_id)` passa a extensão permanente

As tabelas de provider removidas nunca declararam FK para `brands`, então a remoção
delas não altera esta decisão. O UNIQUE **`brands(id, workspace_id)` é extensão
permanente do modelo final**, não dívida residual: as cinco tabelas retidas
(`contents`, `assets`, `projects`, `generations`, `agent_workflow_runs`) continuam
declarando FK composta para `brands`, e a chave de tenant prova que o recurso
pertence ao workspace correto. Uma FK composta exige UNIQUE composta no alvo
(ADR-030, decisão 9).

Consequência para o orçamento de paridade: `unique_extra` fica em **1**, e esse 1 é
uma decisão registrada aqui, não um item pendente. `unexpected_total` continua 1
pelo mesmo motivo.

### 4. O downgrade recria estrutura, nunca dados

`0037_retire_provider_tables` é um passo de **contract** (ADR-030, decisão 3): o
`downgrade` recria `provider_customers` e `provider_subscriptions` com a forma exata
da revisão anterior — colunas, ordem, nullability, `metadata JSON DEFAULT '{}'`,
`deleted_at`, PK `CHAR(32)` e as FKs `NO ACTION` para `billing_accounts` e
`subscriptions`. **Nenhuma linha volta**: a perda dos dados de cache do provider é
conhecida e documentada, e a recuperação depende de backup, não do `downgrade`.

A perda é aceitável porque o conteúdo é derivável do provider (`provider_customer_id`,
`provider_subscription_id` e status) e porque a aplicação já lê os identificadores de
`billing_accounts`/`subscriptions`. Não há outra tabela com FK para as duas, então
`PRAGMA foreign_key_check` fica limpo depois do upgrade.

### 5. Entrypoints de worker não mudam

Nenhuma tabela retida nem removida altera os caminhos de módulo persistidos no
Redis. Os entrypoints `creator.workers.*` permanecem **exatamente** como estão; a
regra do `AGENTS.md` vale aqui: renomear um entrypoint quebraria jobs já enfileirados.

## Classificação das 13 tabelas

Destino, decisão e prazo por tabela. As 11 legadas retêm com o mesmo prazo de
revisão; as duas de provider são removidas.

| Tabela | Destino | Decisão | Prazo | Consumidor / evidência |
| --- | --- | --- | --- | --- |
| `agent_workflow_runs` | estado durável do Agent Workflow (ADR-014/018) | retida | 2027-06-30 | readers em `creator/workflow`; sem alvo no dump — extensão de fato |
| `agent_workflow_steps` | estado durável do Agent Workflow (ADR-014/018) | retida | 2027-06-30 | steps por run; remoção só com a migração do workflow |
| `assets` | `brand_assets`/`generated_images` | retida | 2027-06-30 | metadados de upload; separar brand-owned de gerado antes do drop |
| `brand_settings` | extensão de Brand (Brand Settings) | retida | 2027-06-30 | extensão de Brand; absorção em `brands` sem consumidor migrado |
| `contents` | `posts` + `captions` | retida | 2027-06-30 | dual-read com o modelo final; conversão de payload pendente |
| `generation_job_status_events` | `activity_events` | retida | 2027-06-30 | event log de jobs; sai junto com `generation_jobs` |
| `generation_jobs` | `generated_images` + status | retida | 2027-06-30 | boundary de worker; entrypoint `creator.workers.*` inalterado |
| `generations` | `generated_images`/`content_text_versions` | retida | 2027-06-30 | intenção de Generation; sem alvo direto no dump |
| `images` | `generated_images` | retida | 2027-06-30 | writer real em `generation/repository.complete_job` |
| `projects` | `content_plans`/`campaigns` | retida | 2027-06-30 | modelo transitório; migração de consumidores pendente |
| `settings` | preferências de usuário (sem alvo no dump) | retida | 2027-06-30 | `user/settings`; manter até existir configuração de workspace |
| `provider_customers` | — | removida (`0037_retire_provider_tables`) | — | sem alvo no dump; identificador vive em `billing_accounts.external_id` |
| `provider_subscriptions` | — | removida (`0037_retire_provider_tables`) | — | sem alvo no dump; identificador vive em `subscriptions.external_id` |

### Ordem de remoção, se o prazo vencer

As duas tabelas de provider já foram removidas na `0037_retire_provider_tables`.
Para as 11 retidas, a ordem é por dependência de consumidor, nunca por nome:

1. `contents` → `posts` + `captions`; `images` → `generated_images`;
2. `projects` → `content_plans`/`campaigns`; `assets` → `brand_assets`/`generated_images`;
3. `generations`/`generation_jobs`/`generation_job_status_events` → `generated_images`
   + `activity_events`;
4. `agent_workflow_runs`/`agent_workflow_steps` → estado de workflow/`activity_events`;
5. `brand_settings`/`settings` → `brands`/configuração de workspace, por último.

Extensão permanente registrada por esta ADR:

| Extensão | Escopo | Decisão | Evidência |
| --- | --- | --- | --- |
| `brands` | UNIQUE `(id, workspace_id)` | extensão permanente do modelo final | chave de tenant para as FKs compostas das tabelas satélites; entra como `unique_extra` declarado no orçamento |

## Consequências

- O metadata passa de **71 para 69 tabelas**: 54 do dump + 4 extensões de ADR + 11
  legadas retidas. `provider_customers` e `provider_subscriptions` saem do
  `schema_manifest.PDF_TABLES`, do `final_schema.NO_TARGET` (agora vazio) e do
  conjunto esperado de `tests/test_schema_models.py`.
- O orçamento de paridade cai de 53 para **51** itens: `allowlisted` 17 → 15
  (4 extensões de ADR + 11 legadas), `declared_exception` 35, `unique_extra` 1. O
  único item não declarado continua sendo o UNIQUE de `brands`, que esta ADR declara
  permanente.
- O contrato HTTP perde 10 operações (218 no total: 215 `/api/v1` + 3 de System).
  `tests/contracts/route_table.json` e `docs/openapi.yaml` são regenerados na mesma
  PR.
- `tests/contracts/schema_tables.json` passa a 69 tabelas e `schema_ddl.sql` perde
  os dois `CREATE TABLE`, mais os `CREATE INDEX` que existissem sobre eles.
- A `docs/SCHEMA-MIGRATION-MATRIX.md` registra a retirada das duas tabelas de
  provider e o prazo das 11 legadas; o cabeçalho passa a contar 69 tabelas e 11
  legadas.

## Inversão

A remoção das duas tabelas de provider é irreversível em dados fora de um backup. A
condição de inversão é a mesma da ADR-030: **se aparecer consumidor real de
`provider_customers`/`provider_subscriptions`** — leitura de cache do provider que
não possa ser derivada de `billing_accounts`/`subscriptions` — a remoção é revertida
por uma revisão que recria as tabelas e um backfill a partir do provider, e o
`unique_extra`/allowlist volta ao orçamento com a justificativa escrita.

Para as 11 legadas, a inversão é o vencimento do prazo: passada a data de
2027-06-30 sem consumidor migrado, a retenção deixa de valer e a remoção passa a ser
a ação padrão.

## Fora de escopo

- Migrar os consumidores das 11 legadas (T23 fez os quatro redesenhos; o restante
  exige issue própria).
- Redesenhar a modelagem final ou reintroduzir tabela de cache de provider.
- Renomear entrypoints `creator.workers.*` ou o caminho de módulo de qualquer job.
- Devolver dados pelo `downgrade`; recuperação é por backup.
