# Schema migration matrix

Fonte: `src/creator/infrastructure/database/schema_manifest.py`, `docs/migration/legacy-compatibility-matrix.md` e `docs/migration/legacy-inventory.md`.

A matriz cobre as **51 tabelas** registradas no metadata: 38 do PDF, 11 legadas e 2 extensões de ADR (`auth_sessions`, `outbox_events`).

## Tabelas legadas e extensões

| Tabela | Categoria | Situação atual | Alvo / boundary | Ação de migração | Evidência |
| --- | --- | --- | --- | --- | --- |
| `agent_workflow_runs` | legado | ativo | extensão de ADR — sem alvo PDF | Ativo; estado durável do Agent Workflow (ADR-014/018). Extensão aceita; não é dívida de migração. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `agent_workflow_steps` | legado | ativo | extensão de ADR — sem alvo PDF | Ativo; estado durável do Agent Workflow (ADR-014/018). Extensão aceita; não é dívida de migração. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `assets` | legado | ativo | ver matriz de comportamento | Ativo; metadados de upload. Alvo brand_assets; separar brand-owned de gerado. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `brand_settings` | legado | ativo | ver matriz de comportamento | Ativo; extensão de Brand (ADR-014/024). Sem alvo PDF; permanece. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `contents` | legado | ativo | ver matriz de comportamento | Ativo; dual-read com post_structure. Conversão de payload e consumidores pendente. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `generation_job_status_events` | legado | ativo | ver matriz de comportamento | Ativo; event log de jobs. Remover junto com generation_jobs após migração. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `generation_jobs` | legado | ativo | ver matriz de comportamento | Ativo; lifecycle assíncrono. Boundary de worker; não criar nova tabela silenciosamente. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `generations` | legado | ativo | ver matriz de comportamento | Ativo; intenção de geração. Alvo design_structure/Generation Job; design_structure ainda vazio, requer decisão. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `images` | legado | ativo | ver matriz de comportamento | Ativo; writer real em generation/repository.complete_job. Alvo generated_image; generated_image ainda não tem writer. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `projects` | legado | ativo | ver matriz de comportamento | Ativo; modelo transitório. Alvo em campaigns/planning; migração de consumidores pendente. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `settings` | legado | ativo | ver matriz de comportamento | Ativo em user/settings; preferências do usuário. Sem alvo PDF direto; manter até migrar preferências. | [#44](https://github.com/labLima/creator-backend/issues/44) / 0050 |
| `auth_sessions` | extensão de ADR | ativo | sem alvo PDF | extensão aceita (ADR-018/020); não migrar | ADR-018/020 |
| `outbox_events` | extensão de ADR | ativo | sem alvo PDF | extensão aceita (ADR-018/020); não migrar | ADR-018/020 |

## Tabelas nativas do PDF

Estas tabelas já correspondem ao alvo do PDF e não têm migração pendente:

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

- `generated_image` só pode substituir `images` quando houver writer e teste de contrato; hoje `images` ainda é o destino real da geração.
- `design_structure` está vazio por decisão de contrato (CONTEXT.md); não usar como destino de `generations` sem extensão/ADR.
- `agent_workflow_runs`/`agent_workflow_steps` são estado durável do Agent Workflow (ADR-014/018), não dívida de migração.
- Dados legados exigem ETL explícito; a ADR-021 assume banco novo e não migra PostgreSQL automaticamente.
- A matriz de comportamento e o inventário completo estão em `docs/migration/`.
