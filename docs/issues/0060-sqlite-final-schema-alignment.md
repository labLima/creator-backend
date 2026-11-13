# 0060 — Alinhamento do schema SQLite ao Creator_DB_final.sql

- Status: em execução (T24 concluída; T25/T23 e fechamento pendentes)
- ADR primária: [ADR-030](../adr/0030-sqlite-final-schema-alignment.md) (alinhamento ao modelo final), [ADR-021](../adr/0021-sqlite-default-database.md) (SQLite como banco padrão) e [ADR-015](../adr/0015-database-diagram-alignment.md) (alinhamento ao diagrama)
- Issue tracker: [#159](https://github.com/labLima/creator-backend/issues/159)
- Relacionadas: [#106](https://github.com/labLima/creator-backend/issues/106), [#97](https://github.com/labLima/creator-backend/issues/97)–[#102](https://github.com/labLima/creator-backend/issues/102)
- Plano: [tasks/plan-sqlite-final-schema.md](../../tasks/plan-sqlite-final-schema.md)
- Checklist: [tasks/todo-sqlite-final-schema.md](../../tasks/todo-sqlite-final-schema.md)
- Board local: projeto `SHC` do Shared Context (`SHC-1` e filhas)
- Branch: `feat/sqlite`

## Contexto

A substituição de PostgreSQL por SQLite está concluída e mergeada: ADR-021,
baseline `migrations/versions/0001_sqlite_baseline.py`, migrations PostgreSQL
arquivadas em `migrations/legacy_postgres/`, `docker-compose.yml` com
`DATABASE_URL` padrão `sqlite+pysqlite:////data/creator.db`, volume
`sqlite_data` e `PRAGMA` de WAL/foreign keys/busy timeout.

O que permanece aberto é a paridade entre o schema real e a modelagem final
`Creator_DB_final.sql`, versionada em
[docs/migration/Creator_DB_final.sql](../migration/Creator_DB_final.sql)
(sha256 `619512b778e1f03a315efe5d7d8710a5a540442b5df66ddc144b78e915bbb583`).

A issue [#106](https://github.com/labLima/creator-backend/issues/106) cobre
parte do alinhamento (constraints, índices, models legados, matriz, OpenAPI),
mas não foi escrita contra a modelagem final. Esta issue é o escopo ampliado.

## Evidência

Relatório reproduzível por `python scripts/schema_parity_report.py`:

- [docs/migration/schema-final-alignment.md](../migration/schema-final-alignment.md)

| Métrica | Modelo final | ORM hoje |
| --- | --- | --- |
| Tabelas | 54 | 53 |
| Tipos ENUM | 52 | 0 nativos (String + CHECK) |
| Índices | 173 (50 nomeados, 123 anônimos, 54 UNIQUE) | parcial |
| Tabelas só no modelo final | 18 (+5 renomeações) | — |
| Tabelas só no ORM | — | 4 extensões, 11 legadas, 2 sem alvo |
| Tabelas comuns com divergência | 31 de 31 | — |
| Foreign keys | 101 (10 compostas: 6 com `workspace_id`, 4 com `brand_id`) | 36 equivalentes, 65 a criar |
| CHECK constraints | 80 (15 com regex: 12 moeda, UF, CEP, cor; 3 com `num_nonnulls`) | portabilidade pendente |

Gate de baseline na branch: `make check` verde (lint, format, mypy, pytest,
`alembic check` sem operações pendentes).

## Escopo

- Criar as 18 tabelas ausentes, renomear 1 e substituir 4 tabelas redesenhadas.
- Alinhar colunas, nullability, tamanhos, enums, constraints e índices das 31
  tabelas em comum.
- Preservar as 4 extensões de ADR: `auth_sessions`, `outbox_events`,
  `activity_events`, `content_text_versions`.
- Decidir o destino das 11 tabelas legadas e das 2 sem alvo no modelo final
  (`provider_customers`, `provider_subscriptions`).
- Manter `docs/openapi.yaml`, `docs/SCHEMA-MIGRATION-MATRIX.md` e este tracker
  em paridade com o schema.

## Rastreabilidade por tabela

O plano contém a fase que traça a mudança de **todas** as 54 tabelas do modelo
final, agrupadas por domínio:

| Domínio | Tabelas do modelo final |
| --- | --- |
| Identidade/Workspace | `users`, `workspaces`, `workspace_members`, `workspace_invites`, `workspace_invite_usages` |
| Notificações | `notifications`, `notification_recipients`, `user_devices`, `notification_preferences` |
| Billing | `billing_accounts`, `billing_addresses`, `billing_payment_methods`, `plans`, `plan_items`, `plan_payment_methods`, `subscriptions`, `subscription_history`, `orders`, `invoices`, `charges`, `charge_transactions`, `refunds`, `provider_disputes`, `provider_webhook_events`, `provider_idempotency_keys`, `fiscal_invoices` |
| Créditos/Cupons | `credit_packages`, `coupons`, `coupon_redemptions`, `workspace_credit_transactions`, `workspace_credit_lots`, `workspace_credit_lot_consumptions` |
| Brand | `brands`, `brand_values`, `brand_hashtags`, `brand_colors`, `brand_assets`, `brand_business_details` |
| Campanha | `campaigns`, `campaign_hashtags`, `campaign_voices` |
| Persona | `personas`, `persona_interests` |
| Planejamento/Conteúdo | `content_plans`, `content_plan_items`, `content_plan_special_dates`, `posts`, `captions`, `post_designs`, `design_slides` |
| Geração/Mídia | `generated_images`, `image_resizes` |
| Conformidade/Auditoria | `audit_logs`, `user_consents` |

Nome divergente — apenas 1 é rename simples, 4 são redesenhos de modelo:

| Atual | Final | Veredito |
| --- | --- | --- |
| `workspace_memberships` | `workspace_members` | rename + alinhar (7→8 colunas) |
| `planning` | `content_plans` | redesenho (24→11); persona e quantidades vão para `content_plan_items`/`content_plan_special_dates` |
| `post_structure` | `posts` | redesenho (18→17); arte vai para `post_designs`/`design_slides`, texto para `captions` |
| `design_structure` | `post_designs` | redesenho (5→6) + `design_slides` |
| `generated_image` | `generated_images` | redesenho (11→23); storage, geração e aprovação reestruturados |

## Issues de implementação (board `SHC`)

Uma issue por tarefa do plano (T8 foi dividida: T8 mantém rename/colunas e T21
cuida do vocabulário de papel), cada uma declarando o workspace
`/home/emanueljtrodrigues/Documents/LeFil/creator-backend`.

| Tarefa | Issue | Título |
| --- | --- | --- |
| T1 | `SHC-2` | [T1] ADR-030, épico e tracker |
| T2 | `SHC-3` | [T2] Teste de paridade contra o DDL final |
| T3 | `SHC-4` | [T3] Helpers portáveis de coluna, enum e índice |
| T4 | `SHC-5` | [T4] Portabilidade das CHECK constraints e defaults |
| T5 | `SHC-6` | [T5] Conformidade, consentimento e interesses |
| T6 | `SHC-7` | [T6] Satélites de Brand e Campanha |
| T7 | `SHC-8` | [T7] Satélites de Billing e Créditos |
| T8 | `SHC-9` | [T8] Renomear workspace_memberships para workspace_members |
| T9 | `SHC-10` | [T9] planning para content_plans e satélites |
| T10 | `SHC-11` | [T10] post_structure e design_structure para posts, captions, post_designs e design_slides |
| T11 | `SHC-12` | [T11] generated_image para generated_images e image_resizes |
| T12 | `SHC-13` | [T12] Backfill dos 4 redesenhos |
| T13 | `SHC-14` | [T13] Contract: remover as tabelas antigas |
| T14 | `SHC-15` | [T14] Lote A: identidade, notificações, brand, campanha e persona |
| T15 | `SHC-16` | [T15] Lote B: billing, créditos e cupons |
| T16 | `SHC-17` | [T16] ADR-031, 11 legadas e 2 tabelas sem alvo |
| T17 | `SHC-18` | [T17] Consolidar a baseline |
| T18 | `SHC-19` | [T18] Fechamento do épico |
| T19 | `SHC-20` | [T19] Snapshot como gate, índices no fixture e teste de upgrade anterior |
| T20 | `SHC-21` | [T20] Triggers, funções e view do dump |
| T21 | `SHC-22` | [T21] Vocabulário de workspace_role e autorização |
| T22 | `SHC-23` | [T22] Chaves pai de campanhas/personas e brand_business_details |
| T23 | `SHC-24` | [T23] Migrar consumidores legados para os modelos finais |
| T24 | `SHC-25` | [T24] Lote A1: identidade, convites e notificações |
| T25 | `SHC-26` | [T25] Lote A2: brand, campanha e persona + backfill do brand_id |

## Handoff (2026-11-09)

Estado: **54/54 tabelas do modelo final presentes**; 728 divergências de
colunas/índices/FKs/CHECKs; `make check` 764 testes, `make security` e
`make e2e` verdes. Legado `planning`, `post_structure`, `design_structure` e
`generated_image` ainda ativo por causa dos consumidores.

Ordem de execução para a próxima sessão:

1. **T24** (`SHC-25`) — escopo medido na issue (86 divergências em 8 tabelas).
   Começar por `user_devices`/`notification_preferences`, depois
   `notifications`/`notification_recipients`, por último
   `users`/`workspaces`/`workspace_invites` (auth, `token`→`token_hash`, OpenAPI).
2. **T25** (`SHC-26`) — brand/campanha/persona e `campaigns.brand_id` NOT NULL.
3. **T23** (`SHC-24`) — migrar os 17 arquivos de consumidores legados;
   **T13** (`SHC-14`) só então dropa as tabelas antigas.
4. **T15**, **T16**, **T20**, **T17**, **T18**.

Comandos de verificação (ambiente local):

```sh
XDG_DATA_HOME=$PWD/.local/xdg make check PYTHON=.venv/bin/python
XDG_DATA_HOME=$PWD/.local/xdg make security PYTHON=.venv/bin/python
XDG_DATA_HOME=$PWD/.local/xdg make e2e PYTHON=.venv/bin/python
python scripts/schema_parity_report.py          # regenera o relatório
```

Notas de execução: `migrations/env.py` desliga `foreign_keys` na conexão DBAPI do
Alembic (rebuilds não podem cascatear); migrations antigas são história imutável
e não importam enums vivos; o review automático por subagente estourou o tempo
em várias rodadas e foi substituído por verificação dirigida (execução em banco
migrado, `PRAGMA foreign_key_check`, idempotência).

## Progresso (2026-11-10)

`origin/dev` integrada na branch (`92c7950`): a feature de importação de imagens
foi preservada e a issue local renumerada para `0058` (hoje `0060`) porque a `dev` publicou
`0057-image-import`. A revisão `0006_imported_image_versions` entrou na cadeia
antes de `0006_audit_consent_persona`, com head única em `0014_generated_images`.

T24 (SHC-25), primeira fatia concluída — grupo notificações:

- `user_devices`, `notification_preferences`, `notifications` e
  `notification_recipients` alinhados ao dump: sem `deleted_at`,
  `external_message_id` no lugar de `provider_message_id`, sem
  `workspace_member_id`, enums `notification_type`/`notification_channel`/
  `notification_delivery_status`/`device_platform`/`notification_resource_type`,
  FKs com `CASCADE`/`SET NULL`, índices e UNIQUE do modelo final.
- `migrations/versions/0015_notification_alignment.py` reconstrói as quatro
  tabelas (SQLite), remove linhas soft-deleted e deduplica chaves antes dos
  UNIQUE; downgrade recria a forma anterior sem restaurar as linhas removidas.
- `CHECK_MAP` populado com 27 CHECKs cujo nome já coincide entre dump e models,
  o que zerou quase toda a dívida de `check_extra` dessa frente
  (`check_missing` 80→53, `check_extra` 51→32).
- Relatório regenerado: **643 divergências** (era 728), `column_missing` 128,
  `enum` 27, `index_missing` 91, `fk_ondelete` 29.
- `docs/openapi.yaml` atualizado para os enums e para `body` opcional.

T24 (SHC-25), segunda fatia concluída — identidade e convites:

- `users`: `external_id` absorvido por `auth_provider_id` (ids sintéticos
  `local:*` viram NULL), `cpf`/`cnpj` removidos, `email` 254 com UNIQUE parcial
  `uq_users_email_active` em linhas ativas, `display_name` NOT NULL (backfill a
  partir do e-mail; signup deriva o nome) e `password_hash`/`global_role`
  mantidos como exceção da ADR-020.
- `workspace_invites`: `token` vira `token_hash` SHA-256, `role`/`type`/`status`
  viram enums do dump, `uses_count`/`is_active`/`deleted_at` saem; inativas e
  soft-deleted viram `status = REVOKED`; CHECKs de tipo/e-mail/`max_uses`.
- `workspace_invite_usages`: `user_id`/`workspace_id` derivados de `member_id`
  e removidos; `member_id` NOT NULL; escopo de listagem passa pelo workspace do
  membro.
- `migrations/versions/0016_identity_alignment.py` reconstrói as três tabelas,
  normaliza convites inválidos e tem downgrade documentado (tokens plaintext não
  são recuperáveis).
- `tests/test_identity_alignment_migration.py` cobre backfill de identidade,
  hash de token, revogação e derivação de `member_id`.
- OpenAPI: `auth_provider_id`, `email` 254, `display_name` obrigatório, enums de
  `type`/`role` nos convites e validação cruzada tipo×e-mail×`max_uses`.

Relatório regenerado: **589 divergências** (728 no handoff), `column_missing`
126, `column_extra` 98, `enum` 24, `index_missing` 84, `fk_ondelete` 25,
`check_missing` 45, `check_extra` 30.

T25 (SHC-26) concluída — brand, campanha e persona:

- `brands` passa a ter `created_by`, `segment`, `promise`, `goals`,
  `indicators`, `inspirations` e `restrictions`; `description`, `brand_voice`,
  `metadata` e `created_by_user_id` foram absorvidos/dobrados nos novos campos.
- `brand_colors` vira `name`/`hex`/`position` com CHECK GLOB; `brand_assets`
  vira `storage_bucket`/`storage_key` + enum `brand_asset_type` e UNIQUE de
  storage; `brand_settings` tem a FK composta estreitada para `brands.id`.
- `campaigns`: `brand_id` NOT NULL, `workspace_id` derivado de `brands`,
  `voice` migrado para `campaign_voices`, período removido e `expected_action`
  adicionado; `personas`: `age`→`age_range`, `trigger`→`trigger_event`,
  `interest`→`persona_interests`, `gender` validado pelo enum.
- `migrations/versions/0017_brand_alignment.py` e
  `0018_campaign_persona_alignment.py` com backfill e downgrade (perda de
  texto original documentada); testes de dados em
  `tests/test_campaign_persona_migration.py`.
- Contrato: novas colunas de brand, `brand_id` obrigatório em campanha,
  enums de cor/asset/persona e `expected_action`.
- Exceção de transição: `brands(id, workspace_id)` UNIQUE permanece porque
  cinco tabelas legadas ainda usam FK composta; T16 remove as tabelas e a
  constraint. Dois CHECKs de enum de `charge_transactions` ficam para T15.

Relatório regenerado: **505 divergências** (589 após T24), `column_missing`
110, `column_extra` 70, `enum` 22, `index_missing` 76, `check_extra` 30,
`unique_extra` 4.

T23 (SHC-24), fatia 1 — planning:

- `SqlAlchemyPlanningRepository` passou a ler/escrever `content_plans`,
  `content_plan_items` e `content_plan_special_dates`; `planning` não é mais
  escrito pelo router (a tabela só será dropada em T13).
- Contrato HTTP preservado: `info`↔`briefing`, quantidades↔itens por formato,
  `start_period`/`end_period`↔`start_date`/`end_date`, `special_dates`↔label
  (data ISO quando possível, senão data de início).
- `tests/test_planning_content_plans.py` prova que a API grava nas tabelas
  finais e que `planning` fica vazia.
- Dados legados aparecem após rodar `python scripts/backfill_redesigns.py`
  (T12); T18 deve exigir o backfill antes do fechamento.

T23 (SHC-24), fatia 2 — post_structure:

- `SqlAlchemyPostStructureRepository` grava `posts`, `post_designs` e o
  primeiro `design_slides`; a tabela `post_structure` não é mais escrita.
- Contrato HTTP preservado: título/objetivo/big idea/main message↔`posts`;
  headline/CTA/art_guiding↔slide; formato (`STATIC`→`IMAGE`) e ratio
  normalizados; `resolution` derivada do ratio.
- `status = PUBLISHED` grava `approval_status = APPROVED` e timestamps para
  satisfazer os CHECKs do modelo final.
- `tests/test_post_structure_content_models.py` cobre add/update/list/delete
  e prova que `post_structure` permanece vazia.

T23 (SHC-24) concluída — fatia 3 e fim dos consumidores legados:

- `SqlAlchemyDesignStructureRepository` lê/escreve `post_designs`;
  `SqlAlchemyGeneratedImageRepository` lê `generated_images`, derivando
  workspace do brand, design do slide, URL de bucket/key e resolution de
  width×height.
- Nenhum repositório referencia `planning`, `post_structure`,
  `design_structure` ou `generated_image`.

T13 (SHC-14) concluída — contract:

- `0019_legacy_contract` dropa as 4 tabelas; downgrade recria vazias.
- Models legados removidos, `scripts/backfill_redesigns.py` e seu teste
  removidos, manifesto atualizado (71 tabelas; `table_extra` 0).
- Relatório: **501 divergências**; `table_extra` 4→0.
- Ordem de deploy: rodar o backfill antes de aplicar 0019 em banco com dados
  legados (o downgrade não devolve dados).

T15 (SHC-16), fatia B1 concluída — contas, endereços e cartões:

- `billing_accounts`: documento vira `document` bytes + `document_hash`;
  `provider_customer_*` viram `external_id`/`external_code`; entram
  `document_hash`, `company_name`, enum `payment_provider` e os CHECKs de
  empresa/documento; `deleted_at` sai (delete físico).
- `billing_addresses`: `street`/`complement`/`neighborhood` viram
  `line_1`/`line_2`/`district`; entram `country`, `status`, `is_default`,
  `external_id`, `metadata` e os CHECKs de CEP/UF (GLOB).
- `billing_payment_methods`: `provider_card_id`→`external_id`,
  `card_brand`→`brand`, `card_type`→`type`, `card_status`→`status`; entra
  `billing_address_id`; `deleted_at` sai.
- `migrations/versions/0020_billing_account_alignment.py` reconstrói as três
  tabelas, normaliza tipos/status e tem downgrade funcional.
- Repositórios mantêm o vocabulário antigo no record (street/document_type/
  card_brand) traduzindo na borda; schemas exigem CEP/UF válidos e enums de
  cartão.
- `tests/test_billing_account_alignment_migration.py` cobre o backfill.
- CHECK_MAP ganha os 6 CHECKs do lote; CHECKs de enum ficam adiados para a
  fatia que reescrever cada tabela.
- Relatório: **431 divergências** (501 antes da B1).

T15 (SHC-16), fatia B2 concluída — planos e itens:

- `plans`: colunas finais (`provider`, `external_id`, `price_cents`,
  `currency`, `credits_per_month`, `credits_validity_days`,
  `billing_interval`, `interval_count`, `billing_type`,
  `minimum_price_cents`, `trial_period_days`, `statement_descriptor`,
  `status`); `code`/`description`/`is_active` migram para `metadata`/`status`
  e continuam no contrato do record.
- `plan_items`: `provider`, `external_id`, `currency`, `pricing_scheme_type`
  e `status` como enum; `gateway_id`/`provider_plan_item_id` viram
  `external_id`; `deleted_at` sai (delete físico).
- `0021_plan_alignment` com backfill e downgrade funcional;
  `tests/test_plan_alignment_migration.py` cobre ida e volta.
- CHECK_MAP ganha os 4 CHECKs do lote; CHECKs de enum ficam adiados.
- Relatório: **395 divergências** (431 antes da B2).

T15 (SHC-16), fatia B3 concluída — assinaturas e histórico:

- `subscriptions`: colunas finais (`contracted_price_cents`, `currency`,
  `status`/`provider_status`/`status_reason`, `provider`, `external_id/code`,
  `payment_method(_id)`, `billing_interval/type`, `installments`,
  `current_cycle_id`, períodos, `canceled_at`); `provider_subscription_id`/
  `provider_code` viram `external_*`; `billing_day`/`start_at`/`deleted_at`
  saem (cancelamento vira `CANCELED` + `canceled_at`).
- `subscription_history`: `old_/new_plan_id`, `old_/new_status`,
  `old_/new_provider_status`, `changed_by`, `reason_code/text`; append-only
  no schema (sem `updated_at`/`deleted_at`).
- `0022_subscription_alignment` com backfill determinístico (preço do plano,
  normalização de enums, dedupe de assinatura ativa por workspace) e downgrade
  funcional; `tests/test_subscription_alignment_migration.py` cobre o
  mapeamento.
- CHECK_MAP +3; CHECKs de enum adiados.
- Relatório: **320 divergências** (395 antes da B3).

T15 (SHC-16), fatia B4a concluída — disputas de provider:

- `provider_disputes`: `provider_dispute_id`/`code` viram `external_id`; entram
  `provider`, `amount_cents`, `currency`, `result`, `resolved_at`; `status`
  vira enum `dispute_status`; `deleted_at` sai (delete físico) e
  `billing_account_id` passa a nullable.
- CHECKs de centavos/moeda/result/resolved_at e índices do dump (unique
  provider+external, charge, status+resolved_at e parcial por billing account).
- `0023_provider_dispute_alignment` com backfill e downgrade funcional.
- CHECK_MAP ganha os 4 CHECKs; `check_extra` segue em 30.
- Relatório: **297 divergências** (320 antes da B4a).

T15 (SHC-16), fatia B4b iniciada — provider_idempotency_keys:

- `expires_at` adicionado; `deleted_at` removido (delete físico); `provider`
  e `status` viram enums; UNIQUE `(provider, idempotency_key)` e índice de
  `expires_at`.
- `0024_provider_idempotency` com backfill e downgrade funcional.
- Relatório: **291 divergências** (297 antes).

T15 (SHC-16), fatia B4c — provider_webhook_events:

- `provider_event_id` vira `external_id`; `provider`/`status` em enums;
  `created_at`/`deleted_at` saem (retention usa `received_at`); UNIQUE de
  `dedupe_key` e `(provider, external_id)`; índices de event_type,
  resource_id e (status, received_at).
- `0025_provider_webhook` com backfill/dedupe e downgrade funcional.
- Relatório: **281 divergências** (291 antes).

T15 (SHC-16), fatia B4d — refunds:

- `charge_id` NOT NULL (derivado de `provider_charge_id`), `provider`,
  `external_id` (de `provider_refund_id`), `reason_code` enum e `status`
  enum; `billing_account_id`/`invoice_id`/`provider_charge_id`/`reason` saem;
  CHECKs de centavos/moeda/processed_by_status e índices do dump.
- `0026_refund_alignment` com backfill e downgrade funcional; schema aceita
  `charge_id` e mantém `reason` no record.
- Relatório: **253 divergências** (281 antes).

T15 (SHC-16), fatia B4e — invoices:

- `provider_invoice_id` vira `external_id`; entra `provider`; saem
  `provider_charge_id` e `deleted_at`; `subscription_id` NOT NULL;
  `amount`/`total_*` em bigint, `url` sem limite e enums
  `invoice_status`/`payment_method_type`.
- CHECKs de centavos/parcelas/moeda, FKs RESTRICT e índices do dump.
- `0027_invoice_alignment` com backfill (linhas sem subscription são
  descartadas) e downgrade funcional; CHECK_MAP +3.
- Relatório: **229 divergências** (253 antes).

T15 (SHC-16), fatia B4f — orders:

- `provider_order_id` vira `external_id`; entram `provider` e `code`; saem
  `closed` e `deleted_at`; valores em bigint; `status` no enum `order_status`.
- CHECKs de consistência/centavos/moeda, FKs RESTRICT/SET NULL e índices do
  dump (incluindo UNIQUE `(id, workspace_id)` para as FKs compostas).
- `0028_order_alignment` com backfill (recalcula `amount = subtotal - discount`)
  e downgrade funcional; CHECK_MAP +3.
- Relatório: **204 divergências** (229 antes).

T15 (SHC-16), fatia B4g — charges:

- `provider_charge_id` vira `external_id`; entram `provider`,
  `payment_method(_id)`, `order_id`, `code`, valores pagos/cancelados,
  `funding_source`, `gateway_id`, `provider_payload` e timestamps de
  due/paid/canceled; saem `provider_card_id` e `deleted_at`.
- Valores em bigint; `status` no enum `charge_status`; CHECKs de
  centavos/parcelas/moeda, FKs RESTRICT/SET NULL e índices do dump.
- `0029_charge_alignment` com backfill e downgrade funcional; CHECK_MAP +3.
- Relatório: **166 divergências** (204 antes).

T15 (SHC-16), fatia B5a — credit_packages:

- `credits_amount` vira `credits`; `code`/`deleted_at` saem (delete físico);
  entram `credits_validity_days` (default 30), `name` sem limite,
  `price_cents` bigint e `currency` com default BRL; CHECKs de preço/moeda.
- `0030_credit_package` com backfill e downgrade funcional; CHECK_MAP +2.
- Relatório: **155 divergências** (166 antes).

T15 (SHC-16), fatia B5b — coupons:

- `credits_amount` vira `credits`; entram `credits_validity_days` e `currency`;
  `redemptions_count` sai e é derivado; `min_purchase_cents` em bigint;
  `type`/`applies_to` em enums; `code` sempre maiúsculo.
- CHECKs de tipo/campos exclusivos, desconto, compra mínima, moeda e code
  upper; índices e UNIQUE parcial do código ativo.
- `0031_coupon_alignment` com backfill e downgrade; CHECK_MAP +5.
- Relatório: **133 divergências** (155 antes).

T15 (SHC-16), fatia B5c — coupon_redemptions:

- `user_id`/`workspace_id`/`invoice_id`/`credit_transaction_id`, `provider`,
  `external_id`, `currency`, `once_per_workspace`, `redeemed_at` e
  `canceled_at`; saem `billing_account_id`, `provider_discount_id` e
  `deleted_at`; `status` no enum `coupon_redemption_status`.
- FKs compostas para orders/subscriptions, FKs RESTRICT/SET NULL, índices e
  UNIQUE parciais (`once_per_workspace`, `provider+external_id`).
- `0032_coupon_redemption`, com derivação de usuário/workspace a partir de
  order/subscription, backfill e downgrade; CHECK_MAP +4.
- Relatório: **94 divergências** (133 antes).

T15 (SHC-16) concluída — workspace_credit_transactions (issue #162):

- `workspace_credit_transactions` vira o ledger final: `balance_after`
  (bigint, default 0, CHECK >= 0), `type` no enum `credit_transaction_type`
  (CHECK gerado pelo `Enum`, `create_constraint=True`; entra em
  `declared_exception`) e as quatro referências dedicadas
  (`order_id`/`invoice_id`/`generated_image_id`/`image_resize_id`); saem
  `transaction_type`/`reference_type`/`reference_id` e o par
  `updated_at`/`deleted_at`.
- CHECKs `chk_credit_tx_single_reference`, `chk_credit_tx_balance_nonnegative`,
  `chk_credit_tx_amount_nonzero` e `chk_credit_tx_amount_by_type`; FK composta
  `(order_id, workspace_id) ->
  orders(id, workspace_id)` RESTRICT, FKs RESTRICT para as outras três
  referências, `created_by` SET NULL e `workspace_id` RESTRICT.
- `0035_credit_ledger_alignment` reconstrói a tabela, copia apenas linhas vivas
  com `amount <> 0`, mapeia o vocabulário legado (aliases e `ADJUSTMENT` como
  fallback), preenche as referências dedicadas só quando o alvo existe (a ordem
  também precisa pertencer ao workspace) e calcula `balance_after` com
  `SUM(amount) OVER (PARTITION BY workspace_id ORDER BY created_at, id)`.
  Saldo cumulativo negativo aborta com `ValueError` nomeando workspace e saldo.
  Downgrade restaura as colunas legadas e preserva as linhas sobreviventes
  (perda do valor legado original e das linhas descartadas é documentada).
- A API perde `POST` e `DELETE`: um Credit Transaction é append-only
  (ADR-019), então sobram `GET` lista e `GET` por id; `docs/openapi.yaml`,
  `route_table.json` (231 operações) e o schema de criação removidos.
- `credit/ports.py` publica só `list_for_user`/`get_for_user`, ambos filtrando
  `WorkspaceMembership.status == ACTIVE`; o payload publica os campos finais e
  não vaza mais o triplo legado.
- `CHECK_MAP` +4; orçamento de paridade: **53 divergências** (17 allowlisted,
  35 declaradas, 1 `unique_extra` de `brands`), `gap_digest`
  `c8e4803edd2c9092d5a8386c9b568cc030425605bca3f69e044388647fbd7e64`.

Próximo passo: T15 encerrada; seguir para T20, T16, T17 e T18.

### Progresso T15 (2026-11-13)

- O ledger de créditos está alinhado ao modelo final: `workspace_credit_transactions`
  + `workspace_credit_lots` + `workspace_credit_lot_consumptions`, sem
  `credit_wallets`/`credit_prices` e sem `idempotency_key`.
- Orçamento de paridade atual: **53 divergências totais e 1 não declarada**
  (17 `allowlisted`, 35 `declared_exception`, 1 `unique_extra` de `brands`). O
  total subiu de 52 para 53 porque o CHECK de vocabulário do ledger passou a ser
  gerado pelo enum (`declared_exception` 34 -> 35), não por `fiscal_invoices`.
- T20 continua dona dos triggers/guards de append-only, do recálculo de
  `balance_after` e da validação de procedência de imagem/resize; nada disso
  está implementado nesta entrega.
- A issue **não** está concluída: restam T16, T17, T18 e T20.

## Rastreabilidade GitHub (2026-11-10)

As tarefas restantes foram abertas no repositório e agrupadas na milestone
**08 · Alinhamento SQLite — Creator_DB_final** (milestone #11):

| Tarefa | Issue | Board |
| --- | --- | --- |
| T15 (restante: credit ledger e fiscal_invoices) | [#162](https://github.com/labLima/creator-backend/issues/162) | `SHC-16` |
| T20 (triggers, funções e view) | [#163](https://github.com/labLima/creator-backend/issues/163) | `SHC-21` |
| T16 (ADR-031 e legadas) | [#164](https://github.com/labLima/creator-backend/issues/164) | `SHC-17` |
| T17 (consolidar baseline) | [#165](https://github.com/labLima/creator-backend/issues/165) | `SHC-18` |
| T18 (fechamento do épico) | [#166](https://github.com/labLima/creator-backend/issues/166) | `SHC-19` |

O épico permanece em [#159](https://github.com/labLima/creator-backend/issues/159).

## Critérios de aceite

- [ ] ADR registrada para a estratégia de migração (reconstruir do baseline vs
      migrar dados) e para as renomeações.
- [ ] Migration Alembic SQLite-safe aplicada com `alembic upgrade head` em banco
      vazio e em banco existente.
- [ ] Teste de paridade de schema (tabelas, colunas, nullability, enums,
      índices) falha quando o schema diverge do modelo final.
- [ ] Paridade de vocabulário dos 52 enums verificada por teste.
- [ ] Nenhum construtor exclusivo de PostgreSQL em models ou migrations.
- [ ] Extensões de ADR preservadas e documentadas como exceção ao modelo final.
- [ ] Cada tabela legada com decisão registrada.
- [ ] `docs/SCHEMA-MIGRATION-MATRIX.md`, `docs/ADR-ISSUE-TRACKER.md` e
      `docs/openapi.yaml` atualizados.
- [ ] `make check`, `make security` e `make e2e` verdes.

## Fora de escopo

- Reintroduzir PostgreSQL como banco principal.
- ETL de dados PostgreSQL para SQLite (C1: banco novo, decidido em #99).
- Redesenhar a modelagem final ou criar entidades de produto.
