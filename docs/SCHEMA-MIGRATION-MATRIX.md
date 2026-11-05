# Schema migration matrix

Fonte: `src/creator/infrastructure/database/schema_manifest.py`, `docs/migration/legacy-compatibility-matrix.md` e `docs/migration/legacy-inventory.md`.

A matriz cobre as **51 tabelas** registradas no metadata: 38 do PDF, 11 legadas e 2 extensões de ADR (`auth_sessions`, `outbox_events`).

> **Decisão de 2026-11-04:** a migração de comportamento do Create Bloom foi
> encerrada como não planejada (#134 / [0050](issues/0050-legacy-behavior-parity.md)).
> As tabelas legadas continuam ativas enquanto tiverem consumidores; a coluna de
> evidência abaixo deixa de apontar ETL ou paridade de comportamento. Remoção de
> tabela legada exige issue própria com migração de consumidores.

## Tabelas legadas e extensões

| Tabela | Categoria | Situação atual | Alvo / boundary | Ação de migração | Evidência |
| --- | --- | --- | --- | --- | --- |
| `agent_workflow_runs` | legado | ativo | extensão de ADR — sem alvo PDF | Ativo; estado durável do Agent Workflow (ADR-014/018). Extensão aceita; não é dívida de migração. | Sem migração de legado (2026-11-04) |
| `agent_workflow_steps` | legado | ativo | extensão de ADR — sem alvo PDF | Ativo; estado durável do Agent Workflow (ADR-014/018). Extensão aceita; não é dívida de migração. | Sem migração de legado (2026-11-04) |
| `assets` | legado | ativo | ver matriz de comportamento | Ativo; metadados de upload. Alvo brand_assets; separar brand-owned de gerado. | Sem migração de legado (2026-11-04) |
| `brand_settings` | legado | ativo | ver matriz de comportamento | Ativo; extensão de Brand (ADR-014/024). Sem alvo PDF; permanece. | Sem migração de legado (2026-11-04) |
| `contents` | legado | ativo | ver matriz de comportamento | Ativo; dual-read com post_structure. Conversão de payload e consumidores pendente. | Sem migração de legado (2026-11-04) |
| `generation_job_status_events` | legado | ativo | ver matriz de comportamento | Ativo; event log de jobs. Remover junto com generation_jobs após migração. | Sem migração de legado (2026-11-04) |
| `generation_jobs` | legado | ativo | ver matriz de comportamento | Ativo; lifecycle assíncrono. Boundary de worker; não criar nova tabela silenciosamente. | Sem migração de legado (2026-11-04) |
| `generations` | legado | ativo | Generation/Generation Job; sem alvo PDF direto | Ativo; intenção de geração. Não usar design_structure (vazio) sem extensão/ADR. | Sem migração de legado (2026-11-04) |
| `images` | legado | ativo | generated_image, após post_structure → design_structure | Ativo; writer real em generation/repository.complete_job. generated_image exige design_structure_id NOT NULL; a cadeia de dados ainda não existe. | Sem migração de legado (2026-11-04) |
| `projects` | legado | ativo | ver matriz de comportamento | Ativo; modelo transitório. Alvo em campaigns/planning; migração de consumidores pendente. | Sem migração de legado (2026-11-04) |
| `settings` | legado | ativo | ver matriz de comportamento | Ativo em user/settings; preferências do usuário. Sem alvo PDF direto; manter até migrar preferências. | Sem migração de legado (2026-11-04) |
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
- `design_structure`
- `generated_image`
- `invoices`
- `notification_preferences`
- `notification_recipients`
- `notifications`
- `orders`
- `personas`
- `plan_items`
- `planning`
- `plans`
- `post_structure`
- `provider_customers`
- `provider_disputes`
- `provider_idempotency_keys`
- `provider_subscriptions`
- `provider_webhook_events`
- `refunds`
- `subscription_history`
- `subscriptions`
- `user_devices`
- `users`
- `workspace_credit_transactions`
- `workspace_invite_usages`
- `workspace_invites`
- `workspace_memberships`
- `workspaces`

## Regras

- `generated_image` só pode substituir `images` quando a cadeia `post_structure -> design_structure -> generated_image` tiver dados, writer e teste de contrato; hoje `images` ainda é o destino real da geração.
- `design_structure` está vazio por decisão de contrato (CONTEXT.md); não usar como destino de `generations` sem extensão/ADR.
- `agent_workflow_runs`/`agent_workflow_steps` são estado durável do Agent Workflow (ADR-014/018), não dívida de migração.
- Dados legados exigem ETL explícito; a ADR-021 assume banco novo e não migra PostgreSQL automaticamente.
- A matriz de comportamento e o inventário completo estão em `docs/migration/`.

`activity_events` — Creator-owned business audit history; introduced by issue #52.
