# Schema migration matrix

Fonte: `src/creator/infrastructure/database/schema_manifest.py`, `docs/migration/legacy-compatibility-matrix.md` e `docs/migration/legacy-inventory.md`.

A matriz cobre as **69 tabelas** registradas no metadata: 54 do PDF, 11 legadas retidas e 4 extensões de ADR (`auth_sessions`, `outbox_events`, `activity_events`, `content_text_versions`). As 2 tabelas de provider sem alvo foram removidas pela [ADR-031](adr/0031-legacy-table-retirement.md).

> **Decisão de 2026-11-04:** a migração de comportamento do Create Bloom foi
> encerrada como não planejada (#134 / [0050](issues/0050-legacy-behavior-parity.md)).
> As tabelas legadas continuam ativas enquanto tiverem consumidores; a coluna de
> evidência abaixo deixa de apontar ETL ou paridade de comportamento. Remoção de
> tabela legada exige issue própria com migração de consumidores.
>
> **Decisão de 2026-11-13 ([ADR-031](adr/0031-legacy-table-retirement.md)):** as 11
> tabelas legadas são retidas com **prazo de revisão até 2027-06-30**; passado o
> prazo sem consumidor migrado, a remoção passa a ser a ação padrão. `provider_customers`
> e `provider_subscriptions` foram **removidas** pela revisão
> `0037_retire_provider_tables`.

## Tabelas legadas e extensões

| Tabela | Categoria | Situação atual | Alvo / boundary | Ação de migração | Evidência |
| --- | --- | --- | --- | --- | --- |
| `agent_workflow_runs` | legado | ativo | extensão de ADR — sem alvo PDF | Ativo; estado durável do Agent Workflow (ADR-014/018). Extensão aceita; não é dívida de migração. | Retenção ADR-031, prazo 2027-06-30 |
| `agent_workflow_steps` | legado | ativo | extensão de ADR — sem alvo PDF | Ativo; estado durável do Agent Workflow (ADR-014/018). Extensão aceita; não é dívida de migração. | Retenção ADR-031, prazo 2027-06-30 |
| `activity_events` | extensão de ADR | ativo | sem alvo PDF | Histórico append-oriented de eventos de negócio (ADR-008 emendada). | [#52](https://github.com/labLima/creator-backend/issues/52) |
| `assets` | legado | ativo | ver matriz de comportamento | Ativo; metadados de upload. Alvo brand_assets; separar brand-owned de gerado. | Retenção ADR-031, prazo 2027-06-30 |
| `brand_settings` | legado | ativo | ver matriz de comportamento | Ativo; extensão de Brand (ADR-014/024). Sem alvo PDF; permanece. | Retenção ADR-031, prazo 2027-06-30 |
| `contents` | legado | ativo | ver matriz de comportamento | Ativo; dual-read com post_structure. Conversão de payload e consumidores pendente. | Retenção ADR-031, prazo 2027-06-30 |
| `content_text_versions` | extensão de ADR | ativo | sem alvo PDF | Extensão de Content para versões imutáveis produzidas por Generation Jobs (ADR-025). | [#141](https://github.com/labLima/creator-backend/issues/141) |
| `generation_job_status_events` | legado | ativo | ver matriz de comportamento | Ativo; event log de jobs. Remover junto com generation_jobs após migração. | Retenção ADR-031, prazo 2027-06-30 |
| `generation_jobs` | legado | ativo | ver matriz de comportamento | Ativo; lifecycle assíncrono. Boundary de worker; não criar nova tabela silenciosamente. | Retenção ADR-031, prazo 2027-06-30 |
| `generations` | legado | ativo | Generation/Generation Job; sem alvo PDF direto | Ativo; intenção de geração. Não usar design_structure (vazio) sem extensão/ADR. | Retenção ADR-031, prazo 2027-06-30 |
| `images` | legado | ativo | generated_image, após post_structure → design_structure | Ativo; writer real em generation/repository.complete_job. generated_image exige design_structure_id NOT NULL; a cadeia de dados ainda não existe. | Retenção ADR-031, prazo 2027-06-30 |
| `projects` | legado | ativo | ver matriz de comportamento | Ativo; modelo transitório. Alvo em campaigns/planning; migração de consumidores pendente. | Retenção ADR-031, prazo 2027-06-30 |
| `settings` | legado | ativo | ver matriz de comportamento | Ativo em user/settings; preferências do usuário. Sem alvo PDF direto; manter até migrar preferências. | Retenção ADR-031, prazo 2027-06-30 |
| `auth_sessions` | extensão de ADR | ativo | sem alvo PDF | extensão aceita (ADR-018/020); não migrar | ADR-018/020 |
| `outbox_events` | extensão de ADR | ativo | sem alvo PDF | extensão aceita (ADR-018/020); não migrar | ADR-018/020 |

## Tabelas nativas do PDF

Estas tabelas já correspondem ao alvo do PDF e não têm migração de schema pendente; dados/consumidores seguem as regras abaixo:

- `billing_accounts`
- `billing_addresses`
- `billing_payment_methods`
- `brand_assets`
- `brand_colors`
- `brands`
- `campaigns`
- `charges`
- `coupon_redemptions`
- `coupons`
- `credit_packages`
- `invoices`
- `notification_preferences`
- `notification_recipients`
- `notifications`
- `orders`
- `personas`
- `plan_items`
- `plans`
- `provider_disputes`
- `provider_idempotency_keys`
- `provider_webhook_events`
- `refunds`
- `subscription_history`
- `subscriptions`
- `user_devices`
- `users`
- `workspace_credit_transactions`
- `workspace_invite_usages`
- `workspace_invites`
- `workspace_members`
- `workspaces`

## Tabelas retiradas pelo contract da ADR-030

Estas tabelas legadas foram substituídas pelo modelo final e dropadas pela
revisão `0019_legacy_contract` (T13). O downgrade recria apenas a estrutura,
sem dados.

| Tabela retirada | Substituta |
| --- | --- |
| `planning` | `content_plans`, `content_plan_items`, `content_plan_special_dates` |
| `post_structure` | `posts`, `captions`, `post_designs`, `design_slides` |
| `design_structure` | `post_designs`, `design_slides` |
| `generated_image` | `generated_images`, `image_resizes` |

## Tabelas de provider retiradas pela ADR-031

Estas tabelas não têm alvo no modelo final: o identificador do provider vive em
`billing_accounts.external_id`/`external_code` e
`subscriptions.external_id`/`external_code`. A revisão
`0037_retire_provider_tables` (T16) as removeu; o downgrade recria a estrutura,
sem dados — a perda dos registros de cache é documentada na
[ADR-031](adr/0031-legacy-table-retirement.md) e a recuperação depende de backup.

| Tabela retirada | Revisão | Motivo |
| --- | --- | --- |
| `provider_customers` | `0037_retire_provider_tables` | removida: sem alvo no dump, cache do provider substituído por `billing_accounts.external_*` (ADR-031) |
| `provider_subscriptions` | `0037_retire_provider_tables` | removida: sem alvo no dump, cache do provider substituído por `subscriptions.external_*` (ADR-031) |

## Tabelas do modelo final adicionadas por ADR-030

Estas tabelas vêm de `docs/migration/Creator_DB_final.sql` e entram por fases
(ADR-030), antes de qualquer rota consumi-las.

| Tabela | Fase | Situação | Consumidor |
| --- | --- | --- | --- |
| `audit_logs` | T5 (`0006`) | ativo, append-only | nenhum ainda; escrita prevista na camada de serviço |
| `user_consents` | T5 (`0006`) | ativo | nenhum ainda; consentimento versionado por usuário |
| `persona_interests` | T5 (`0006`) | ativo | nenhum ainda; vocabulário de interesses da persona |
| `brand_hashtags` | T6 (`0007`) | ativo | nenhum ainda; hashtags por marca |
| `brand_values` | T6 (`0007`) | ativo | nenhum ainda; valores por marca |
| `campaign_hashtags` | T6 (`0007`) | ativo | nenhum ainda; hashtags por campanha |
| `campaign_voices` | T6 (`0007`) | ativo | nenhum ainda; vozes por campanha com vocabulário fechado |
| `plan_payment_methods` | T7 (`0008`) | ativo | nenhum ainda; meios e parcelamento por plano |
| `charge_transactions` | T7 (`0008`) | ativo | nenhum ainda; transações por cobrança com idempotência |
| `fiscal_invoices` | T7 (`0008`) | ativo | nenhum ainda; metadados fiscais com origem exclusiva |
| `workspace_credit_lots` | T7 (`0008`) | ativo | nenhum ainda; lote de créditos com validade |
| `workspace_credit_lot_consumptions` | T7 (`0008`) | ativo | nenhum ainda; consumo de lote sem dupla contagem |
| `brand_business_details` | T22 (`0011`) | ativo | nenhum ainda; briefing gerado com FKs compostas de tenant |
| `content_plans` | T9 (`0012`) | ativo (expand) | substitui `planning` no contract T13 |
| `content_plan_items` | T9 (`0012`) | ativo | quantidades por formato do plano |
| `content_plan_special_dates` | T9 (`0012`) | ativo | datas especiais por plano |
| `posts` | T10 (`0013`) | ativo (expand) | substitui `post_structure` no contract T13 |
| `captions` | T10 (`0013`) | ativo | legendas versionadas por post |
| `post_designs` | T10 (`0013`) | ativo | formato/proporção da arte por post |
| `design_slides` | T10 (`0013`) | ativo | slides ordenados por design |
| `generated_images` | T11 (`0014`) | ativo (expand) | substitui `generated_image` no contract T13 |
| `image_resizes` | T11 (`0014`) | ativo | variações por proporção da imagem gerada |

## Regras

- `generated_image` só pode substituir `images` quando a cadeia `post_structure -> design_structure -> generated_image` tiver dados, writer e teste de contrato; hoje `images` ainda é o destino real da geração.
- `design_structure` está vazio por decisão de contrato (CONTEXT.md); não usar como destino de `generations` sem extensão/ADR.
- `agent_workflow_runs`/`agent_workflow_steps` são estado durável do Agent Workflow (ADR-014/018), não dívida de migração.
- Dados legados exigem ETL explícito; a ADR-021 assume banco novo e não migra PostgreSQL automaticamente.
- A matriz de comportamento e o inventário completo estão em `docs/migration/`.

`activity_events` — Creator-owned business audit history; introduced by issue #52.
