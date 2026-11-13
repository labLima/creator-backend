# Alinhamento ao Creator_DB_final.sql

> Gerado por `scripts/schema_parity_report.py` a partir de
> `docs/migration/Creator_DB_final.sql` contra `Base.metadata`.
> Não edite à mão: regenere o arquivo.

## Resumo

- Dump: `sha256 619512b778e1f03a315efe5d7d8710a5a540442b5df66ddc144b78e915bbb583`
- Tabelas no modelo final: **54**
- Tabelas no metadata atual: **69**
- Tipos ENUM: **52**
- Índices: **173** (50 nomeados, 123 anônimos)
- Foreign keys: **101** (10 compostas)
- Funções/triggers/views: **70**
- Divergências: **51**
- Divergências não declaradas: **1** (exclui `allowlisted` e `declared_exception`)

## Divergências por categoria

| Categoria | Ocorrências |
| --- | --- |
| `table_missing` | 0 |
| `table_extra` | 0 |
| `allowlisted` | 15 |
| `declared_exception` | 35 |
| `rename_collision` | 0 |
| `pk_mismatch` | 0 |
| `column_missing` | 0 |
| `column_extra` | 0 |
| `nullability` | 0 |
| `width` | 0 |
| `kind` | 0 |
| `enum` | 0 |
| `unique_missing` | 0 |
| `unique_extra` | 1 |
| `index_missing` | 0 |
| `index_extra` | 0 |
| `index_name` | 0 |
| `fk_missing` | 0 |
| `fk_extra` | 0 |
| `fk_ondelete` | 0 |
| `check_missing` | 0 |
| `check_extra` | 0 |
| `default_missing` | 0 |
| `default_value` | 0 |

## 1. Tabelas com nome divergente

O mapa é aplicado uma vez na comparação, então a tabela renomeada não conta
como ausente nem excedente. Nenhum caso é `ALTER TABLE ... RENAME` puro:
`role` muda de vocabulário, entra `status` e sai `deleted_at`.

| Final | Metadata |
| --- | --- |

## 2. Tabelas do modelo final ausentes no ORM

Nenhuma.

## 3. Colunas, tipos, nullability e defaults

Total: **0**.

Sem divergência.

## 4. Enums

Total: **0**.

Sem divergência.

## 5. UNIQUEs

Total: **1**.

### `unique_extra` (1)

- `brands['id', 'workspace_id']`

## 6. Índices

Total: **0**.

Sem divergência.

## 7. Foreign keys

Total: **0**.

Sem divergência.

## 8. CHECK constraints

Total: **0**.

Sem divergência.

## 9. Exceções declaradas

Total: **35**.

### `declared_exception` (35)

- `adr-020:users.global_role`
- `adr-020:users.password_hash`
- `dump-inconsistency:captions: dump index UNIQUE (post_id) WHERE is_current and deleted_at is null (the dump filters deleted_at, a column captions does not declare; the model index keeps only is_current so the predicate stays portable)`
- `dump-inconsistency:captions: model index UNIQUE (post_id) WHERE is_current kept; the dump predicate is not portable`
- `enum-check:brand_assets.brand_asset_type`
- `enum-check:campaign_voices.campaign_voice`
- `enum-check:content_plan_items.content_format`
- `enum-check:fiscal_invoices.fiscal_invoice_status`
- `enum-check:generated_images.approval_status`
- `enum-check:generated_images.generation_status`
- `enum-check:generated_images.image_feedback_type`
- `enum-check:image_resizes.art_ratio`
- `enum-check:image_resizes.resize_status`
- `enum-check:notification_preferences.notification_channel`
- `enum-check:notification_preferences.notification_type`
- `enum-check:notification_recipients.notification_channel`
- `enum-check:notification_recipients.notification_delivery_status`
- `enum-check:notifications.notification_resource_type`
- `enum-check:notifications.notification_type`
- `enum-check:personas.age_range`
- `enum-check:personas.persona_gender`
- `enum-check:plan_payment_methods.payment_method_type`
- `enum-check:post_designs.art_ratio`
- `enum-check:post_designs.content_format`
- `enum-check:posts.approval_status`
- `enum-check:posts.publication_status`
- `enum-check:user_consents.consent_type`
- `enum-check:user_devices.device_platform`
- `enum-check:users.global_role`
- `enum-check:workspace_credit_transactions.credit_transaction_type`
- `enum-check:workspace_invites.invite_status`
- `enum-check:workspace_invites.invite_type`
- `enum-check:workspace_invites.workspace_role`
- `enum-check:workspace_members.member_status`
- `enum-check:workspace_members.workspace_role`

## 10. Funções, triggers e views

Objetos com regra de negócio no banco. A decisão é objeto a objeto na tarefa
T20 (`SHC-21`), que classifica cada um em trigger SQLite, guarda de aplicação
com teste, ou fora de escopo justificado.

| Tipo | Nome |
| --- | --- |
| FUNCTION | `coupon_redemptions_set_once` |
| TRIGGER | `trg_coupon_redemptions_set_once` |
| FUNCTION | `workspace_credit_balance` |
| FUNCTION | `workspace_credit_lot_available` |
| FUNCTION | `m1_validate_credit_transaction` |
| TRIGGER | `trg_m1_credit_tx_validate` |
| FUNCTION | `check_credit_tx_image_workspace` |
| TRIGGER | `trg_credit_tx_image_workspace` |
| FUNCTION | `m1_validate_credit_lot` |
| TRIGGER | `trg_m1_credit_lot_validate` |
| FUNCTION | `m1_validate_credit_consumption` |
| TRIGGER | `trg_m1_credit_consumption_validate` |
| FUNCTION | `m1_reject_credit_mutation` |
| TRIGGER | `trg_m1_tx_immutable` |
| TRIGGER | `trg_m1_consumption_immutable` |
| FUNCTION | `m1_guard_credit_lot_update` |
| TRIGGER | `trg_m1_lot_guard` |
| VIEW | `charges_with_last_transaction` |
| FUNCTION | `m7_reject_subscription_history_mutation` |
| TRIGGER | `trg_subscription_history_append_only` |
| FUNCTION | `set_updated_at` |
| TRIGGER | `trg_updated_at_workspace_credit_lots` |
| TRIGGER | `trg_updated_at_users` |
| TRIGGER | `trg_updated_at_workspaces` |
| TRIGGER | `trg_updated_at_workspace_members` |
| TRIGGER | `trg_updated_at_workspace_invites` |
| TRIGGER | `trg_updated_at_workspace_invite_usages` |
| TRIGGER | `trg_updated_at_notifications` |
| TRIGGER | `trg_updated_at_notification_recipients` |
| TRIGGER | `trg_updated_at_user_devices` |
| TRIGGER | `trg_updated_at_notification_preferences` |
| TRIGGER | `trg_updated_at_billing_accounts` |
| TRIGGER | `trg_updated_at_billing_addresses` |
| TRIGGER | `trg_updated_at_billing_payment_methods` |
| TRIGGER | `trg_updated_at_plans` |
| TRIGGER | `trg_updated_at_plan_items` |
| TRIGGER | `trg_updated_at_plan_payment_methods` |
| TRIGGER | `trg_updated_at_subscriptions` |
| TRIGGER | `trg_updated_at_orders` |
| TRIGGER | `trg_updated_at_invoices` |
| TRIGGER | `trg_updated_at_charges` |
| TRIGGER | `trg_updated_at_charge_transactions` |
| TRIGGER | `trg_updated_at_refunds` |
| TRIGGER | `trg_updated_at_provider_disputes` |
| TRIGGER | `trg_updated_at_provider_webhook_events` |
| TRIGGER | `trg_updated_at_provider_idempotency_keys` |
| TRIGGER | `trg_updated_at_credit_packages` |
| TRIGGER | `trg_updated_at_coupons` |
| TRIGGER | `trg_updated_at_coupon_redemptions` |
| TRIGGER | `trg_updated_at_brands` |
| TRIGGER | `trg_updated_at_brand_values` |
| TRIGGER | `trg_updated_at_brand_hashtags` |
| TRIGGER | `trg_updated_at_brand_colors` |
| TRIGGER | `trg_updated_at_brand_assets` |
| TRIGGER | `trg_updated_at_brand_business_details` |
| TRIGGER | `trg_updated_at_campaigns` |
| TRIGGER | `trg_updated_at_campaign_hashtags` |
| TRIGGER | `trg_updated_at_campaign_voices` |
| TRIGGER | `trg_updated_at_personas` |
| TRIGGER | `trg_updated_at_persona_interests` |
| TRIGGER | `trg_updated_at_content_plans` |
| TRIGGER | `trg_updated_at_content_plan_items` |
| TRIGGER | `trg_updated_at_content_plan_special_dates` |
| TRIGGER | `trg_updated_at_posts` |
| TRIGGER | `trg_updated_at_captions` |
| TRIGGER | `trg_updated_at_post_designs` |
| TRIGGER | `trg_updated_at_design_slides` |
| TRIGGER | `trg_updated_at_generated_images` |
| TRIGGER | `trg_updated_at_fiscal_invoices` |
| TRIGGER | `trg_updated_at_image_resizes` |

## 11. Tabelas fora do modelo final

| Tabela | Categoria |
| --- | --- |
| `auth_sessions` | extensão de ADR (preservada) |
| `outbox_events` | extensão de ADR (preservada) |
| `activity_events` | extensão de ADR (preservada) |
| `content_text_versions` | extensão de ADR (preservada) |
| `agent_workflow_runs` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `agent_workflow_steps` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `assets` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `brand_settings` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `contents` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `generation_job_status_events` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `generation_jobs` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `generations` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `images` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `projects` | legado retido pela ADR-031 (prazo 2027-06-30) |
| `settings` | legado retido pela ADR-031 (prazo 2027-06-30) |

