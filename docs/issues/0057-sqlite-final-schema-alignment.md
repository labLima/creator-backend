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
| T1 | `SHC-2` | ADR-028, épico e tracker |
| T2 | `SHC-3` | Comparador único e teste de paridade com orçamento |
| T3 | `SHC-4` | Helpers portáveis de enum e nome de índice |
| T4 | `SHC-5` | Portabilidade das CHECK constraints e defaults |
| T5 | `SHC-6` | Conformidade, consentimento e interesses |
| T6 | `SHC-7` | Satélites de Brand e Campanha |
| T7 | `SHC-8` | Satélites de Billing e Créditos |
| T8 | `SHC-9` | workspace_members: rename, status, invited_by e exclusão física |
| T9 | `SHC-10` | planning para content_plans e satélites |
| T10 | `SHC-11` | post_structure e design_structure para posts, captions, post_designs e design_slides |
| T11 | `SHC-12` | generated_image para generated_images e image_resizes |
| T12 | `SHC-13` | Backfill dos 4 redesenhos |
| T13 | `SHC-14` | Contract: remover as tabelas antigas |
| T14 | `SHC-15` | Lote A: identidade, notificações, brand, campanha e persona |
| T15 | `SHC-16` | Lote B: billing, créditos e cupons |
| T16 | `SHC-17` | ADR-029, 11 legadas e 2 tabelas sem alvo |
| T17 | `SHC-18` | Consolidar a baseline |
| T18 | `SHC-19` | Fechamento do épico |
| T19 | `SHC-20` | Snapshot como gate, índices no fixture e teste de upgrade anterior |
| T20 | `SHC-21` | Triggers, funções e view do dump |
| T21 | `SHC-22` | Vocabulário de workspace_role e autorização |

## Progresso

| Issue | Tarefa | Estado | Evidência |
| --- | --- | --- | --- |
| `SHC-2` | T1 — ADR-028, épico e tracker | done | `docs/adr/0028-sqlite-final-schema-alignment.md` |
| `SHC-3` | T2 — comparador único e orçamento | done | `final_schema.py`; `schema_parity_budget.json` |
| `SHC-20` | T19 — snapshot gate e upgrade anterior | done | `snapshot_contract.py --check`; `schema_prev_ddl.sql` |
| `SHC-4` | T3 — enums e nomes de índice | done | `portable_enums.py`; `naming.py` |
| `SHC-5` | T4 — CHECKs portáveis | done | `constraints.py` |
| `SHC-6` | T5 — audit, consent, persona interests | done | revisão 0006 |
| `SHC-7` | T6 — satélites de brand/campanha | done | revisão 0007 |
| `SHC-8` | T7 — satélites de billing/créditos | done | revisão 0008 |
| `SHC-9` | T8 — workspace_members | done | revisão 0009; rename, status, exclusão física |
| `SHC-22` | T21 — vocabulário de workspace_role | done | revisão 0010; MANAGER e rebuild do CHECK |
| `SHC-23` | T22 — chaves pai de campaigns/personas e brand_business_details | done | revisão 0011; FKs compostas de tenant |
| `SHC-10` | T9 — content_plans e satélites | done | revisão 0012; expand do planejamento |
| `SHC-11` | T10 — posts, captions, post_designs, design_slides | done | revisão 0013; expand editorial |
| `SHC-12` | T11 — generated_images e image_resizes | done | revisão 0014; **0 tabelas ausentes** |

Orçamento de paridade: **728 divergências**, com **0 tabelas ausentes**. O restante é
alinhamento de colunas/índices/FKs/CHECKs nas tabelas existentes (T14/T15) e as
legacy substituídas no contract (T13).

T8 foi dividida: o vocabulário de `role` e a autorização por papel ficam em T21
(`SHC-22`).

## Objetos de armazenamento

O dump declara 69 funções/triggers e a view `charges_with_last_transaction`,
decididos objeto a objeto em T20 (`SHC-21`).

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
