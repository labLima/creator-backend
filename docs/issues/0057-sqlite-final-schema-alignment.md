# 0057 — Alinhamento do schema SQLite ao Creator_DB_final.sql

- Status: planejado
- ADR primária: [ADR-021](../adr/0021-sqlite-default-database.md) (SQLite como banco padrão) e [ADR-015](../adr/0015-database-diagram-alignment.md) (alinhamento ao diagrama)
- Issue tracker: [#159](https://github.com/labLima/creator-backend/issues/159)
- Relacionadas: [#106](https://github.com/labLima/creator-backend/issues/106), [#97](https://github.com/labLima/creator-backend/issues/97)–[#102](https://github.com/labLima/creator-backend/issues/102)
- Plano: [tasks/plan-sqlite-final-schema.md](../../tasks/plan-sqlite-final-schema.md)
- Checklist: [tasks/todo-sqlite-final-schema.md](../../tasks/todo-sqlite-final-schema.md)
- Board local: projeto `SHC` do Shared Context (`SHC-1` e filhas)
- Branch: `feat/sqlite-final-schema-alignment`

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
| Índices | 173 (123 sem nome, 54 UNIQUE) | parcial |
| Tabelas só no modelo final | 18 (+5 renomeações) | — |
| Tabelas só no ORM | — | 4 extensões, 11 legadas, 2 sem alvo |
| Tabelas comuns com divergência | 31 de 31 | — |
| Foreign keys | 101 (10 compostas) | 36 equivalentes, 65 a criar |
| CHECK constraints | 80 (15 com regex, 3 com `num_nonnulls`) | portabilidade pendente |

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

Uma issue por tarefa do plano, cada uma declarando o workspace
`/home/emanueljtrodrigues/Documents/LeFil/creator-backend`.

| Tarefa | Issue | Título |
| --- | --- | --- |
| T1 | `SHC-2` | [T1] ADR-028, épico e tracker |
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
| T16 | `SHC-17` | [T16] ADR-029, 11 legadas e 2 tabelas sem alvo |
| T17 | `SHC-18` | [T17] Consolidar a baseline |
| T18 | `SHC-19` | [T18] Fechamento do épico |

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
