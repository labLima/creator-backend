# Alinhamento ao Creator_DB_final.sql

> Documento gerado por análise read-only de `docs/migration/Creator_DB_final.sql`
> contra `Base.metadata`. Reproduza com:
>
> ```sh
> python scripts/schema_parity_report.py
> ```

## Resumo

- Tabelas no modelo final: **54**
- Tabelas no metadata atual: **53**
- Tipos ENUM no modelo final: **52**
- Índices no modelo final: **173** (52 tabelas; 123 sem nome explícito; 54 UNIQUE)
- Tabelas novas a criar: **18**
- Tabelas a renomear: **5**
- Extensões de ADR preservadas: **4**
- Tabelas legadas a decidir: **11**
- Tabelas sem alvo no modelo final: **2**

## 1. Tabelas a renomear

| Atual | Final | Colunas atual → final |
| --- | --- | --- |
| `workspace_memberships` | `workspace_members` | 7 → 8 |
| `planning` | `content_plans` | 24 → 11 |
| `post_structure` | `posts` | 18 → 17 |
| `design_structure` | `post_designs` | 5 → 6 |
| `generated_image` | `generated_images` | 11 → 23 |

## 2. Tabelas do modelo final ausentes no ORM

- **`audit_logs`** (11 colunas, 0 constraints): `id`, `actor_id`, `workspace_id`, `action`, `entity_type`, `entity_id`, `before`, `after`, `ip_address`, `user_agent`, `created_at`
- **`brand_business_details`** (10 colunas, 0 constraints): `id`, `brand_id`, `campaign_id`, `persona_id`, `output`, `model`, `spec_version`, `created_by`, `created_at`, `updated_at`
- **`brand_hashtags`** (5 colunas, 0 constraints): `id`, `brand_id`, `hashtag`, `created_at`, `updated_at`
- **`brand_values`** (5 colunas, 0 constraints): `id`, `brand_id`, `value`, `created_at`, `updated_at`
- **`campaign_hashtags`** (5 colunas, 0 constraints): `id`, `campaign_id`, `hashtag`, `created_at`, `updated_at`
- **`campaign_voices`** (6 colunas, 0 constraints): `id`, `campaign_id`, `voice`, `created_by`, `created_at`, `updated_at`
- **`captions`** (8 colunas, 0 constraints): `id`, `post_id`, `created_by`, `body`, `version`, `is_current`, `created_at`, `updated_at`
- **`charge_transactions`** (10 colunas, 1 constraints): `id`, `charge_id`, `provider`, `external_id`, `status`, `amount_cents`, `gateway_response`, `antifraud_response`, `created_at`, `updated_at`
- **`content_plan_items`** (6 colunas, 0 constraints): `id`, `content_plan_id`, `format`, `quantity`, `created_at`, `updated_at`
- **`content_plan_special_dates`** (6 colunas, 0 constraints): `id`, `content_plan_id`, `special_date`, `label`, `created_at`, `updated_at`
- **`design_slides`** (9 colunas, 0 constraints): `id`, `post_design_id`, `position`, `headline`, `subtitle`, `cta`, `art_direction`, `created_at`, `updated_at`
- **`fiscal_invoices`** (21 colunas, 3 constraints): `id`, `billing_account_id`, `order_id`, `invoice_id`, `subscription_id`, `number`, `series`, `access_key`, `service_code`, `amount_cents`, `currency`, `status`, `pdf_storage_bucket`, `pdf_storage_key`, `xml_storage_bucket`, `xml_storage_key`, `error_message`, `issued_at`, `canceled_at`, `created_at`, `updated_at`
- **`image_resizes`** (14 colunas, 5 constraints): `id`, `source_image_id`, `ratio`, `status`, `storage_bucket`, `storage_key`, `mime_type`, `size_bytes`, `width`, `height`, `error_message`, `created_by`, `created_at`, `updated_at`
- **`persona_interests`** (5 colunas, 0 constraints): `id`, `persona_id`, `interest`, `created_at`, `updated_at`
- **`plan_payment_methods`** (6 colunas, 0 constraints): `id`, `plan_id`, `method`, `max_installments`, `created_at`, `updated_at`
- **`user_consents`** (10 colunas, 0 constraints): `id`, `user_id`, `type`, `document_version`, `granted`, `granted_at`, `revoked_at`, `ip_address`, `user_agent`, `created_at`
- **`workspace_credit_lot_consumptions`** (6 colunas, 0 constraints): `id`, `workspace_id`, `lot_id`, `transaction_id`, `amount`, `created_at`
- **`workspace_credit_lots`** (8 colunas, 1 constraints): `id`, `workspace_id`, `grant_transaction_id`, `original_amount`, `remaining_amount`, `expires_at`, `created_at`, `updated_at`

## 3. Divergências nas tabelas comuns

Legenda: `+` exigida pelo modelo final e ausente no ORM; `-` presente no ORM e ausente
no modelo final; `!` nullability divergente. `uuid`→`CHAR(32)` e `timestamptz`→`DATETIME`
são conversões portáveis esperadas (ADR-021) e não aparecem como divergência.

### `billing_accounts`
- `+` `document_hash`, `external_code`, `external_id`
- `-` `deleted_at`, `document_type`, `provider_customer_code`, `provider_customer_id`
- `!` NOT NULL no modelo final: `provider`
- tamanho/tipo: `email` final `varchar(254)` vs ORM `varchar(64)`
- enums: `payer_type`, `provider`

### `billing_addresses`
- `+` `country`, `district`, `external_id`, `is_default`, `line_1`, `line_2`, `metadata`, `status`
- `-` `complement`, `deleted_at`, `neighborhood`, `street`
- `!` NOT NULL no modelo final: `city`, `number`, `state`, `zip_code`
- tamanho/tipo: `number` final `varchar(20)` vs ORM `varchar(16)`, `state` final `varchar(2)` vs ORM `varchar(16)`, `zip_code` final `varchar(8)` vs ORM `varchar(16)`

### `billing_payment_methods`
- `+` `billing_address_id`, `brand`, `external_id`, `external_network_token_id`, `first_six_digits`, `metadata`, `status`, `type`
- `-` `card_brand`, `card_status`, `card_type`, `deleted_at`, `provider_card_id`

### `brand_assets`
- `+` `created_by`, `storage_bucket`, `storage_key`
- `-` `deleted_at`, `file_url`
- enums: `type`

### `brand_colors`
- `+` `hex`, `name`, `position`
- `-` `brand_goals`, `brand_indicators`, `brand_inspirations`, `brand_main_hashtags`, `brand_name`, `brand_promise`, `brand_restrictions`, `brand_segment`, `brand_values`, `color_name`, `created_by`, `deleted_at`, `hex_code`, `order`, `workspace_id`

### `brands`
- `+` `created_by`, `goals`, `indicators`, `inspirations`, `promise`, `restrictions`, `segment`
- `-` `brand_voice`, `created_by_user_id`, `description`, `metadata`
- tamanho/tipo: `name` final `varchar(100)` vs ORM `varchar(255)`

### `campaigns`
- `+` `brand_id`, `expected_action`
- `-` `end_at`, `start_at`, `voice`, `workspace_id`
- tamanho/tipo: `name` final `varchar(100)` vs ORM `varchar(30)`

### `charges`
- `+` `canceled_amount_cents`, `canceled_at`, `code`, `due_at`, `external_id`, `funding_source`, `gateway_id`, `installments`, `order_id`, `paid_amount_cents`, `paid_at`, `payment_method`, `payment_method_id`, `provider`, `provider_payload`
- `-` `deleted_at`, `provider_card_id`, `provider_charge_id`
- tamanho/tipo: `amount_cents` final `bigint` vs ORM `int`

### `coupon_redemptions`
- `+` `canceled_at`, `credit_transaction_id`, `currency`, `external_id`, `invoice_id`, `once_per_workspace`, `provider`, `redeemed_at`, `user_id`, `workspace_id`
- `-` `billing_account_id`, `deleted_at`, `provider_discount_id`
- tamanho/tipo: `discount_amount_cents` final `bigint` vs ORM `int`
- enums: `status`

### `coupons`
- `+` `credits`, `credits_validity_days`, `currency`
- `-` `credits_amount`, `redemptions_count`
- tamanho/tipo: `min_purchase_cents` final `bigint` vs ORM `int`
- enums: `applies_to`, `type`

### `credit_packages`
- `+` `credits`, `credits_validity_days`
- `-` `code`, `credits_amount`, `deleted_at`
- tamanho/tipo: `price_cents` final `bigint` vs ORM `int`

### `invoices`
- `+` `external_id`, `provider`
- `-` `deleted_at`, `provider_charge_id`, `provider_invoice_id`
- `!` NOT NULL no modelo final: `subscription_id`
- tamanho/tipo: `amount_cents` final `bigint` vs ORM `int`, `total_discount_cents` final `bigint` vs ORM `int`, `total_increment_cents` final `bigint` vs ORM `int`
- enums: `payment_method`, `status`

### `notification_preferences`
- `-` `deleted_at`
- enums: `channel`, `type`

### `notification_recipients`
- `+` `external_message_id`
- `-` `deleted_at`, `provider_message_id`, `workspace_member_id`
- enums: `channel`, `status`

### `notifications`
- `-` `deleted_at`
- enums: `resource_type`, `type`

### `orders`
- `+` `code`, `external_id`, `provider`
- `-` `closed`, `deleted_at`, `provider_order_id`
- tamanho/tipo: `amount_cents` final `bigint` vs ORM `int`, `discount_cents` final `bigint` vs ORM `int`, `subtotal_cents` final `bigint` vs ORM `int`
- enums: `status`

### `personas`
- `+` `age_range`, `trigger_event`
- `-` `age`, `interest`, `trigger`
- tamanho/tipo: `name` final `varchar(100)` vs ORM `varchar(30)`
- enums: `gender`

### `plan_items`
- `+` `currency`, `external_id`, `provider`
- `-` `deleted_at`, `gateway_id`, `provider_plan_item_id`
- `!` NOT NULL no modelo final: `status`
- tamanho/tipo: `price_cents` final `bigint` vs ORM `int`
- enums: `pricing_scheme_type`, `status`

### `plans`
- `+` `billing_interval`, `billing_type`, `credits_per_month`, `credits_validity_days`, `currency`, `external_id`, `interval_count`, `minimum_price_cents`, `price_cents`, `provider`, `statement_descriptor`, `status`, `trial_period_days`
- `-` `code`, `description`, `is_active`
- enums: `type`

### `provider_disputes`
- `+` `amount_cents`, `currency`, `external_id`, `provider`, `resolved_at`, `result`
- `-` `code`, `deleted_at`, `provider_dispute_id`
- enums: `status`

### `provider_idempotency_keys`
- `+` `expires_at`
- `-` `deleted_at`
- enums: `provider`, `status`

### `provider_webhook_events`
- `+` `external_id`
- `-` `created_at`, `deleted_at`, `provider_event_id`
- enums: `provider`, `status`

### `refunds`
- `+` `charge_id`, `external_id`, `metadata`, `processed_at`, `provider`, `reason_code`, `requested_by`
- `-` `billing_account_id`, `deleted_at`, `invoice_id`, `provider_charge_id`, `provider_refund_id`, `reason`
- tamanho/tipo: `amount_cents` final `bigint` vs ORM `int`
- enums: `status`

### `subscription_history`
- `+` `changed_by`, `new_plan_id`, `new_provider_status`, `new_status`, `old_plan_id`, `old_provider_status`, `old_status`, `reason_code`, `reason_text`
- `-` `deleted_at`, `plan_id`, `previous_plan_id`, `previous_status`, `reason`, `status`, `updated_at`
- enums: `change_type`

### `subscriptions`
- `+` `billing_interval`, `contracted_price_cents`, `currency`, `current_cycle_id`, `external_code`, `external_id`, `payment_method_id`, `provider`, `status_reason`
- `-` `billing_day`, `deleted_at`, `interval`, `provider_card_id`, `provider_code`, `provider_subscription_id`, `start_at`
- `!` NOT NULL no modelo final: `installments`
- tamanho/tipo: `minimum_price_cents` final `bigint` vs ORM `int`
- enums: `billing_type`, `payment_method`, `provider_status`, `status`

### `user_devices`
- `-` `deleted_at`
- enums: `platform`

### `users`
- `+` `auth_provider_id`
- `-` `cnpj`, `cpf`, `external_id`, `global_role`, `password_hash`
- `!` NOT NULL no modelo final: `display_name`
- tamanho/tipo: `email` final `varchar(254)` vs ORM `varchar(320)`

### `workspace_credit_transactions`
- `+` `balance_after`, `created_by`, `generated_image_id`, `image_resize_id`, `invoice_id`, `order_id`, `type`
- `-` `deleted_at`, `reference_id`, `reference_type`, `transaction_type`, `updated_at`

### `workspace_invite_usages`
- `-` `created_at`, `deleted_at`, `user_id`, `workspace_id`
- `!` NOT NULL no modelo final: `member_id`

### `workspace_invites`
- `+` `token_hash`
- `-` `deleted_at`, `is_active`, `token`, `uses_count`
- tamanho/tipo: `email` final `varchar(254)` vs ORM `varchar(255)`
- enums: `role`, `status`, `type`

## 4. Índices por tabela

O modelo final declara 173 índices. `SQLite` aceita nomes
automáticos, mas a paridade precisa ser decidida tabela a tabela:
nome, colunas, UNIQUE e predicado parcial.

### `audit_logs`
- `CREATE INDEX ON "audit_logs" ("entity_type", "entity_id", "created_at")`
- `CREATE INDEX ON "audit_logs" ("actor_id", "created_at")`
- `CREATE INDEX ON "audit_logs" ("workspace_id", "created_at")`
- `CREATE INDEX ON "audit_logs" ("action", "created_at")`

### `billing_accounts`
- `CREATE INDEX ON "billing_accounts" ("user_id")`
- `CREATE INDEX ON "billing_accounts" ("document_hash")`
- `CREATE UNIQUE INDEX ON "billing_accounts" ("provider", "external_id")`

### `billing_addresses`
- `CREATE INDEX ON "billing_addresses" ("billing_account_id")`
- `CREATE UNIQUE INDEX "uq_billing_addresses_default" ON "billing_addresses" ("billing_account_id") WHERE "is_default" AND "status" = 'ACTIVE'`

### `billing_payment_methods`
- `CREATE UNIQUE INDEX ON "billing_payment_methods" ("billing_account_id", "external_id")`
- `CREATE INDEX ON "billing_payment_methods" ("billing_account_id", "is_default")`
- `CREATE UNIQUE INDEX "uq_billing_payment_methods_default" ON "billing_payment_methods" ("billing_account_id") WHERE "is_default" AND "status" = 'ACTIVE'`
- `CREATE INDEX "idx_m8_billing_payment_methods_billing_address_id" ON "billing_payment_methods" ("billing_address_id") WHERE "billing_address_id" IS NOT NULL`

### `brand_assets`
- `CREATE INDEX ON "brand_assets" ("brand_id")`
- `CREATE INDEX ON "brand_assets" ("created_by")`
- `CREATE UNIQUE INDEX ON "brand_assets" ("storage_bucket", "storage_key")`

### `brand_business_details`
- `CREATE INDEX ON "brand_business_details" ("brand_id", "campaign_id", "persona_id")`
- `CREATE INDEX ON "brand_business_details" ("created_at")`
- `CREATE INDEX "idx_m8_brand_business_details_campaign_id_brand_id" ON "brand_business_details" ("campaign_id", "brand_id")`
- `CREATE INDEX "idx_m8_brand_business_details_persona_id_brand_id" ON "brand_business_details" ("persona_id", "brand_id")`
- `CREATE INDEX "idx_m8_brand_business_details_created_by" ON "brand_business_details" ("created_by") WHERE "created_by" IS NOT NULL`

### `brand_colors`
- `CREATE INDEX ON "brand_colors" ("brand_id")`

### `brand_hashtags`
- `CREATE UNIQUE INDEX ON "brand_hashtags" ("brand_id", "hashtag")`

### `brand_values`
- `CREATE UNIQUE INDEX ON "brand_values" ("brand_id", "value")`

### `brands`
- `CREATE INDEX ON "brands" ("workspace_id")`
- `CREATE INDEX "idx_m8_brands_created_by" ON "brands" ("created_by") WHERE "created_by" IS NOT NULL`

### `campaign_hashtags`
- `CREATE UNIQUE INDEX ON "campaign_hashtags" ("campaign_id", "hashtag")`

### `campaign_voices`
- `CREATE UNIQUE INDEX ON "campaign_voices" ("campaign_id", "voice")`

### `campaigns`
- `CREATE UNIQUE INDEX ON "campaigns" ("id", "brand_id")`
- `CREATE INDEX ON "campaigns" ("brand_id")`
- `CREATE INDEX "idx_m8_campaigns_created_by" ON "campaigns" ("created_by") WHERE "created_by" IS NOT NULL`

### `captions`
- `CREATE UNIQUE INDEX ON "captions" ("post_id", "version")`
- `CREATE UNIQUE INDEX "uq_captions_current" ON "captions" ("post_id") WHERE "is_current" AND "deleted_at" IS NULL`
- `CREATE INDEX "idx_m8_captions_created_by" ON "captions" ("created_by") WHERE "created_by" IS NOT NULL`

### `charge_transactions`
- `CREATE INDEX ON "charge_transactions" ("status")`
- `CREATE INDEX ON "charge_transactions" ("created_at")`
- `CREATE UNIQUE INDEX ON "charge_transactions" ("charge_id", "provider", "external_id")`
- `CREATE INDEX "idx_charge_transactions_latest" ON "charge_transactions" ("charge_id", "created_at" DESC NULLS LAST, "id" DESC)`

### `charges`
- `CREATE UNIQUE INDEX ON "charges" ("provider", "external_id")`
- `CREATE INDEX ON "charges" ("billing_account_id", "status")`
- `CREATE INDEX ON "charges" ("invoice_id")`
- `CREATE INDEX ON "charges" ("order_id")`
- `CREATE INDEX ON "charges" ("status")`
- `CREATE INDEX ON "charges" ("code")`
- `CREATE INDEX ON "charges" ("paid_at")`
- `CREATE INDEX "idx_m8_charges_payment_method_id" ON "charges" ("payment_method_id") WHERE "payment_method_id" IS NOT NULL`

### `content_plan_items`
- `CREATE UNIQUE INDEX ON "content_plan_items" ("content_plan_id", "format")`

### `content_plan_special_dates`
- `CREATE UNIQUE INDEX ON "content_plan_special_dates" ("content_plan_id", "special_date", "label")`

### `content_plans`
- `CREATE INDEX ON "content_plans" ("brand_id")`
- `CREATE INDEX ON "content_plans" ("campaign_id")`
- `CREATE INDEX ON "content_plans" ("persona_id")`
- `CREATE INDEX "idx_m8_content_plans_campaign_id_brand_id" ON "content_plans" ("campaign_id", "brand_id")`
- `CREATE INDEX "idx_m8_content_plans_persona_id_brand_id" ON "content_plans" ("persona_id", "brand_id")`
- `CREATE INDEX "idx_m8_content_plans_created_by" ON "content_plans" ("created_by") WHERE "created_by" IS NOT NULL`

### `coupon_redemptions`
- `CREATE INDEX ON "coupon_redemptions" ("coupon_id", "workspace_id")`
- `CREATE INDEX ON "coupon_redemptions" ("user_id")`
- `CREATE INDEX ON "coupon_redemptions" ("workspace_id")`
- `CREATE INDEX ON "coupon_redemptions" ("order_id", "workspace_id")`
- `CREATE INDEX ON "coupon_redemptions" ("subscription_id", "workspace_id")`
- `CREATE UNIQUE INDEX ON "coupon_redemptions" ("provider", "external_id")`
- `CREATE UNIQUE INDEX "uq_coupon_redemptions_once_per_workspace" ON "coupon_redemptions" ("coupon_id", "workspace_id") WHERE "once_per_workspace" AND "status" = 'APPLIED'`
- `CREATE INDEX "idx_m8_coupon_redemptions_invoice_id" ON "coupon_redemptions" ("invoice_id") WHERE "invoice_id" IS NOT NULL`
- `CREATE INDEX "idx_m8_coupon_redemptions_credit_transaction_id" ON "coupon_redemptions" ("credit_transaction_id") WHERE "credit_transaction_id" IS NOT NULL`

### `coupons`
- `CREATE UNIQUE INDEX "uq_coupons_code_active" ON "coupons" ("code") WHERE "deleted_at" IS NULL`
- `CREATE INDEX ON "coupons" ("type")`
- `CREATE INDEX ON "coupons" ("is_active")`
- `CREATE INDEX "idx_m8_coupons_created_by" ON "coupons" ("created_by") WHERE "created_by" IS NOT NULL`

### `design_slides`
- `CREATE UNIQUE INDEX ON "design_slides" ("post_design_id", "position")`

### `fiscal_invoices`
- `CREATE UNIQUE INDEX "uq_fiscal_invoices_access_key" ON "fiscal_invoices" ("access_key") WHERE "access_key" IS NOT NULL`
- `CREATE UNIQUE INDEX "uq_fiscal_invoices_number_series_account" ON "fiscal_invoices" ("billing_account_id", "series", "number") WHERE "series" IS NOT NULL AND "number" IS NOT NULL`
- `CREATE INDEX ON "fiscal_invoices" ("billing_account_id")`
- `CREATE INDEX ON "fiscal_invoices" ("status")`
- `CREATE INDEX ON "fiscal_invoices" ("order_id")`
- `CREATE INDEX ON "fiscal_invoices" ("invoice_id")`
- `CREATE INDEX ON "fiscal_invoices" ("subscription_id")`

### `generated_images`
- `CREATE UNIQUE INDEX "uq_generated_images_current_per_slide" ON "generated_images" ("design_slide_id") WHERE "is_current" AND "deleted_at" IS NULL`
- `CREATE INDEX ON "generated_images" ("design_slide_id")`
- `CREATE INDEX ON "generated_images" ("generation_status")`
- `CREATE INDEX ON "generated_images" ("approval_status")`
- `CREATE INDEX ON "generated_images" ("approved_by")`
- `CREATE UNIQUE INDEX ON "generated_images" ("storage_bucket", "storage_key")`
- `CREATE INDEX "idx_m8_generated_images_created_by" ON "generated_images" ("created_by") WHERE "created_by" IS NOT NULL`

### `image_resizes`
- `CREATE INDEX "idx_image_resizes_source_image" ON "image_resizes" ("source_image_id")`
- `CREATE UNIQUE INDEX "uq_image_resizes_storage" ON "image_resizes" ("storage_bucket", "storage_key")`
- `CREATE INDEX "idx_image_resizes_created_by" ON "image_resizes" ("created_by") WHERE "created_by" IS NOT NULL`

### `invoices`
- `CREATE UNIQUE INDEX ON "invoices" ("provider", "external_id")`
- `CREATE INDEX ON "invoices" ("billing_account_id")`
- `CREATE INDEX ON "invoices" ("subscription_id", "due_at")`
- `CREATE INDEX ON "invoices" ("status", "due_at")`

### `notification_preferences`
- `CREATE UNIQUE INDEX ON "notification_preferences" ("user_id", "type", "channel")`

### `notification_recipients`
- `CREATE INDEX ON "notification_recipients" ("user_id", "channel")`
- `CREATE INDEX ON "notification_recipients" ("user_id", "read_at")`
- `CREATE INDEX ON "notification_recipients" ("user_id", "created_at")`
- `CREATE UNIQUE INDEX ON "notification_recipients" ("notification_id", "user_id", "channel")`

### `notifications`
- `CREATE UNIQUE INDEX ON "notifications" ("workspace_id", "dedupe_key")`
- `CREATE INDEX ON "notifications" ("type")`
- `CREATE INDEX ON "notifications" ("created_at")`
- `CREATE INDEX "idx_m8_notifications_created_by" ON "notifications" ("created_by") WHERE "created_by" IS NOT NULL`

### `orders`
- `CREATE UNIQUE INDEX ON "orders" ("provider", "external_id")`
- `CREATE UNIQUE INDEX ON "orders" ("id", "workspace_id")`
- `CREATE INDEX ON "orders" ("billing_account_id")`
- `CREATE INDEX ON "orders" ("workspace_id")`
- `CREATE INDEX ON "orders" ("status")`
- `CREATE INDEX "idx_m8_orders_credit_package_id" ON "orders" ("credit_package_id") WHERE "credit_package_id" IS NOT NULL`

### `persona_interests`
- `CREATE UNIQUE INDEX ON "persona_interests" ("persona_id", "interest")`

### `personas`
- `CREATE UNIQUE INDEX ON "personas" ("id", "brand_id")`
- `CREATE INDEX ON "personas" ("brand_id")`
- `CREATE INDEX "idx_m8_personas_created_by" ON "personas" ("created_by") WHERE "created_by" IS NOT NULL`

### `plan_items`
- `CREATE UNIQUE INDEX ON "plan_items" ("provider", "external_id")`
- `CREATE INDEX "idx_m8_plan_items_plan_id" ON "plan_items" ("plan_id")`

### `plan_payment_methods`
- `CREATE UNIQUE INDEX ON "plan_payment_methods" ("plan_id", "method")`

### `plans`
- `CREATE UNIQUE INDEX ON "plans" ("provider", "external_id")`

### `post_designs`
- `CREATE INDEX ON "post_designs" ("post_id")`

### `posts`
- `CREATE INDEX ON "posts" ("content_plan_id", "publication_status")`
- `CREATE INDEX ON "posts" ("content_plan_id", "created_at")`
- `CREATE INDEX ON "posts" ("publication_status")`
- `CREATE INDEX ON "posts" ("approval_status")`
- `CREATE INDEX ON "posts" ("scheduled_at")`
- `CREATE INDEX ON "posts" ("approved_by")`
- `CREATE INDEX "idx_m8_posts_created_by" ON "posts" ("created_by") WHERE "created_by" IS NOT NULL`

### `provider_disputes`
- `CREATE UNIQUE INDEX ON "provider_disputes" ("provider", "external_id")`
- `CREATE INDEX ON "provider_disputes" ("charge_id")`
- `CREATE INDEX ON "provider_disputes" ("status", "resolved_at")`
- `CREATE INDEX "idx_m8_provider_disputes_billing_account_id" ON "provider_disputes" ("billing_account_id") WHERE "billing_account_id" IS NOT NULL`

### `provider_idempotency_keys`
- `CREATE UNIQUE INDEX ON "provider_idempotency_keys" ("provider", "idempotency_key")`
- `CREATE INDEX ON "provider_idempotency_keys" ("expires_at")`

### `provider_webhook_events`
- `CREATE INDEX ON "provider_webhook_events" ("event_type")`
- `CREATE INDEX ON "provider_webhook_events" ("resource_id")`
- `CREATE INDEX ON "provider_webhook_events" ("status", "received_at")`
- `CREATE UNIQUE INDEX ON "provider_webhook_events" ("provider", "external_id")`

### `refunds`
- `CREATE INDEX ON "refunds" ("charge_id")`
- `CREATE INDEX ON "refunds" ("status")`
- `CREATE UNIQUE INDEX ON "refunds" ("provider", "external_id")`
- `CREATE INDEX "idx_m8_refunds_requested_by" ON "refunds" ("requested_by") WHERE "requested_by" IS NOT NULL`

### `subscription_history`
- `CREATE INDEX ON "subscription_history" ("subscription_id", "created_at")`
- `CREATE INDEX "idx_m8_subscription_history_old_plan_id" ON "subscription_history" ("old_plan_id") WHERE "old_plan_id" IS NOT NULL`
- `CREATE INDEX "idx_m8_subscription_history_new_plan_id" ON "subscription_history" ("new_plan_id") WHERE "new_plan_id" IS NOT NULL`
- `CREATE INDEX "idx_m8_subscription_history_changed_by" ON "subscription_history" ("changed_by") WHERE "changed_by" IS NOT NULL`

### `subscriptions`
- `CREATE UNIQUE INDEX ON "subscriptions" ("provider", "external_id")`
- `CREATE UNIQUE INDEX ON "subscriptions" ("id", "workspace_id")`
- `CREATE INDEX ON "subscriptions" ("billing_account_id")`
- `CREATE INDEX ON "subscriptions" ("next_billing_at")`
- `CREATE INDEX ON "subscriptions" ("workspace_id")`
- `CREATE UNIQUE INDEX "uq_subscriptions_workspace_current" ON "subscriptions" ("workspace_id") WHERE "status" IN ('ACTIVE', 'TRIALING', 'PAST_DUE')`
- `CREATE INDEX "idx_m8_subscriptions_plan_id" ON "subscriptions" ("plan_id")`
- `CREATE INDEX "idx_m8_subscriptions_payment_method_id" ON "subscriptions" ("payment_method_id") WHERE "payment_method_id" IS NOT NULL`

### `user_consents`
- `CREATE UNIQUE INDEX ON "user_consents" ("user_id", "type", "document_version")`

### `user_devices`
- `CREATE INDEX ON "user_devices" ("user_id")`

### `users`
- `CREATE UNIQUE INDEX "uq_users_email_active" ON "users" ("email") WHERE "deleted_at" IS NULL`

### `workspace_credit_lot_consumptions`
- `CREATE INDEX ON "workspace_credit_lot_consumptions" ("transaction_id")`
- `CREATE UNIQUE INDEX ON "workspace_credit_lot_consumptions" ("lot_id", "transaction_id")`
- `CREATE INDEX "idx_m8_workspace_credit_lot_consumptions_lot_id_workspace_id" ON "workspace_credit_lot_consumptions" ("lot_id", "workspace_id")`
- `CREATE INDEX "idx_m8_lot_consumptions_transaction_workspace" ON "workspace_credit_lot_consumptions" ("transaction_id", "workspace_id")`

### `workspace_credit_lots`
- `CREATE INDEX ON "workspace_credit_lots" ("workspace_id", "expires_at")`
- `CREATE UNIQUE INDEX "uq_credit_lots_id_workspace" ON "workspace_credit_lots" ("id", "workspace_id")`
- `CREATE INDEX "idx_m8_workspace_credit_lots_grant_transaction_id_workspace_id" ON "workspace_credit_lots" ("grant_transaction_id", "workspace_id")`

### `workspace_credit_transactions`
- `CREATE INDEX ON "workspace_credit_transactions" ("workspace_id", "created_at")`
- `CREATE UNIQUE INDEX ON "workspace_credit_transactions" ("order_id", "type")`
- `CREATE UNIQUE INDEX ON "workspace_credit_transactions" ("invoice_id", "type")`
- `CREATE UNIQUE INDEX ON "workspace_credit_transactions" ("generated_image_id", "type")`
- `CREATE UNIQUE INDEX "uq_credit_tx_id_workspace" ON "workspace_credit_transactions" ("id", "workspace_id")`
- `CREATE UNIQUE INDEX "uq_credit_tx_image_resize" ON "workspace_credit_transactions" ("image_resize_id", "type")`
- `CREATE INDEX "idx_m8_workspace_credit_transactions_created_by" ON "workspace_credit_transactions" ("created_by") WHERE "created_by" IS NOT NULL`

### `workspace_invite_usages`
- `CREATE INDEX ON "workspace_invite_usages" ("member_id")`
- `CREATE UNIQUE INDEX ON "workspace_invite_usages" ("invite_id", "member_id")`

### `workspace_invites`
- `CREATE INDEX ON "workspace_invites" ("workspace_id")`
- `CREATE INDEX ON "workspace_invites" ("email")`
- `CREATE INDEX ON "workspace_invites" ("status")`
- `CREATE INDEX "idx_m8_workspace_invites_created_by" ON "workspace_invites" ("created_by")`

### `workspace_members`
- `CREATE UNIQUE INDEX "uq_workspace_members_workspace_user" ON "workspace_members" ("workspace_id", "user_id")`
- `CREATE INDEX ON "workspace_members" ("user_id")`
- `CREATE INDEX ON "workspace_members" ("workspace_id", "role")`
- `CREATE INDEX ON "workspace_members" ("invited_by")`

## 5. Constraints CHECK/UNIQUE/REFERENCES

**`billing_accounts`**
- `CONSTRAINT "chk_billing_accounts_company_name" CHECK ((payer_type = 'COMPANY') = (company_name IS NOT NULL))`
- `CONSTRAINT "chk_billing_accounts_document_pair" CHECK ((document IS NULL) = (document_hash IS NULL))`

**`billing_addresses`**
- `CONSTRAINT "chk_billing_addresses_zip_code" CHECK (country <> 'BR' OR zip_code ~ '^[0-9]{8}$')`
- `CONSTRAINT "chk_billing_addresses_state_uf" CHECK (country <> 'BR' OR state ~ '^[A-Z]{2}$')`

**`billing_payment_methods`**
- `CONSTRAINT "chk_billing_payment_methods_exp_month" CHECK (exp_month IS NULL OR exp_month BETWEEN 1 AND 12)`
- `CONSTRAINT "chk_billing_payment_methods_exp_year" CHECK (exp_year IS NULL OR exp_year BETWEEN 2000 AND 2100)`

**`brand_colors`**
- `CONSTRAINT "chk_brand_colors_hex" CHECK (hex ~ '^#[0-9A-Fa-f]{6}$')`

**`charge_transactions`**
- `CONSTRAINT "chk_charge_transactions_amount_nonnegative" CHECK (amount_cents >= 0)`

**`charges`**
- `CONSTRAINT "chk_charges_cents_nonnegative" CHECK (amount_cents >= 0 AND (paid_amount_cents IS NULL OR paid_amount_cents >= 0) AND (canceled_amount_cents IS NULL OR canceled_amount_cents >= 0))`
- `CONSTRAINT "chk_charges_installments" CHECK (installments IS NULL OR installments >= 1)`
- `CONSTRAINT "chk_charges_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')`

**`content_plans`**
- `CONSTRAINT "chk_content_plans_period_order" CHECK (start_date IS NULL OR end_date IS NULL OR end_date >= start_date)`

**`coupon_redemptions`**
- `CONSTRAINT "chk_coupon_redemptions_single_target" CHECK (num_nonnulls(order_id, subscription_id) = 1)`
- `CONSTRAINT "chk_coupon_redemptions_discount_percent" CHECK (discount_percent_applied IS NULL OR (discount_percent_applied > 0 AND discount_percent_applied <= 100))`
- `CONSTRAINT "chk_coupon_redemptions_amount_nonnegative" CHECK (discount_amount_cents IS NULL OR discount_amount_cents >= 0)`
- `CONSTRAINT "chk_coupon_redemptions_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`

**`coupons`**
- `CONSTRAINT "chk_coupons_type_exclusive_fields" CHECK ((type = 'DISCOUNT' AND discount_percent IS NOT NULL AND credits IS NULL) OR (type = 'CREDIT' AND credits IS NOT NULL AND discount_percent IS NULL))`
- `CONSTRAINT "chk_coupons_discount_percent" CHECK (discount_percent IS NULL OR (discount_percent > 0 AND discount_percent <= 100))`
- `CONSTRAINT "chk_coupons_min_purchase_nonnegative" CHECK (min_purchase_cents IS NULL OR min_purchase_cents >= 0)`
- `CONSTRAINT "chk_coupons_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`
- `CONSTRAINT "chk_coupons_code_upper" CHECK (code = upper(code))`

**`credit_packages`**
- `CONSTRAINT "chk_credit_packages_price_nonnegative" CHECK (price_cents >= 0)`
- `CONSTRAINT "chk_credit_packages_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')`

**`fiscal_invoices`**
- `CONSTRAINT "chk_fiscal_invoices_one_origin" CHECK (num_nonnulls(order_id, invoice_id, subscription_id) = 1)`
- `CONSTRAINT "chk_fiscal_invoices_amount_nonnegative" CHECK (amount_cents >= 0)`
- `CONSTRAINT "chk_fiscal_invoices_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`

**`generated_images`**
- `CONSTRAINT "chk_generated_images_current_complete" CHECK (NOT is_current OR (generation_status = 'SUCCEEDED' AND deleted_at IS NULL))`
- `CONSTRAINT "chk_generated_images_size_bytes" CHECK (size_bytes >= 0)`
- `CONSTRAINT "chk_generated_images_dimensions" CHECK (width > 0 AND height > 0)`
- `CONSTRAINT "chk_generated_images_approval_pair" CHECK ((approved_at IS NULL) = (approved_by IS NULL))`
- `CONSTRAINT "chk_generated_images_rejected_reason" CHECK (approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL)`
- `CONSTRAINT "chk_generated_images_approved_metadata" CHECK (approval_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))`
- `CONSTRAINT "chk_generated_images_approval_after_generation" CHECK (approval_status = 'PENDING' OR generation_status = 'SUCCEEDED')`
- `CONSTRAINT "chk_generated_images_file_by_status" CHECK ( generation_status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL AND storage_key IS NOT NULL AND size_bytes IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL) )`
- `CONSTRAINT "chk_generated_images_failed_message" CHECK ( generation_status <> 'FAILED' OR error_message IS NOT NULL )`

**`image_resizes`**
- `CONSTRAINT "uq_image_resizes_source_ratio" UNIQUE (source_image_id, ratio)`
- `CONSTRAINT "chk_image_resizes_file" CHECK ( status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL AND storage_key IS NOT NULL AND size_bytes IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL) )`
- `CONSTRAINT "chk_image_resizes_failed" CHECK (status <> 'FAILED' OR error_message IS NOT NULL)`
- `CONSTRAINT "chk_image_resizes_size" CHECK (size_bytes IS NULL OR size_bytes > 0)`
- `CONSTRAINT "chk_image_resizes_dimensions" CHECK ((width IS NULL OR width > 0) AND (height IS NULL OR height > 0))`

**`invoices`**
- `CONSTRAINT "chk_invoices_cents_nonnegative" CHECK (amount_cents >= 0 AND (total_discount_cents IS NULL OR total_discount_cents >= 0) AND (total_increment_cents IS NULL OR total_increment_cents >= 0))`
- `CONSTRAINT "chk_invoices_installments" CHECK (installments IS NULL OR installments >= 1)`
- `CONSTRAINT "chk_invoices_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')`

**`notifications`**
- `CONSTRAINT "chk_notifications_resource_pair" CHECK ((resource_type IS NULL) = (resource_id IS NULL))`

**`orders`**
- `CONSTRAINT "chk_orders_amount_consistency" CHECK (amount_cents = subtotal_cents - discount_cents)`
- `CONSTRAINT "chk_orders_cents_nonnegative" CHECK (subtotal_cents >= 0 AND amount_cents >= 0 AND (discount_cents IS NULL OR discount_cents >= 0))`
- `CONSTRAINT "chk_orders_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')`

**`plan_items`**
- `CONSTRAINT "chk_plan_items_price_nonnegative" CHECK (price_cents IS NULL OR price_cents >= 0)`
- `CONSTRAINT "chk_plan_items_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`

**`plans`**
- `CONSTRAINT "chk_plans_cents_nonnegative" CHECK (price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0))`
- `CONSTRAINT "chk_plans_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`

**`post_designs`**
- `CONSTRAINT "chk_post_designs_stories_ratio" CHECK (format <> 'STORIES' OR ratio = 'RATIO_9_16')`

**`posts`**
- `CONSTRAINT "chk_posts_approval_pair" CHECK ((approved_at IS NULL) = (approved_by IS NULL))`
- `CONSTRAINT "chk_posts_rejected_reason" CHECK (approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL)`
- `CONSTRAINT "chk_posts_approved_metadata" CHECK (approval_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))`
- `CONSTRAINT "chk_posts_scheduled_at" CHECK (publication_status <> 'SCHEDULED' OR scheduled_at IS NOT NULL)`
- `CONSTRAINT "chk_posts_published_at" CHECK (publication_status <> 'PUBLISHED' OR published_at IS NOT NULL)`
- `CONSTRAINT "chk_posts_publish_requires_approval" CHECK (publication_status = 'DRAFT' OR approval_status = 'APPROVED')`

**`provider_disputes`**
- `CONSTRAINT "chk_provider_disputes_amount_nonnegative" CHECK (amount_cents IS NULL OR amount_cents >= 0)`
- `CONSTRAINT "chk_provider_disputes_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`
- `CONSTRAINT "chk_provider_disputes_result" CHECK ((status = 'RESOLVED') = (result IS NOT NULL))`
- `CONSTRAINT "chk_provider_disputes_resolved_at" CHECK ((status = 'RESOLVED') = (resolved_at IS NOT NULL))`

**`refunds`**
- `CONSTRAINT "chk_refunds_amount_nonnegative" CHECK (amount_cents >= 0)`
- `CONSTRAINT "chk_refunds_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`
- `CONSTRAINT "chk_refunds_processed_by_status" CHECK ((status = 'PENDING') = (processed_at IS NULL))`

**`subscriptions`**
- `CONSTRAINT "chk_subscriptions_installments" CHECK (installments IS NULL OR installments >= 1)`
- `CONSTRAINT "chk_subscriptions_cents_nonnegative" CHECK (contracted_price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0))`
- `CONSTRAINT "chk_subscriptions_currency_format" CHECK (currency ~ '^[A-Z]{3}$')`

**`workspace_credit_lots`**
- `CONSTRAINT "chk_credit_lots_amounts" CHECK (original_amount > 0 AND remaining_amount >= 0 AND remaining_amount <= original_amount)`

**`workspace_credit_transactions`**
- `CONSTRAINT "chk_credit_tx_single_reference" CHECK (num_nonnulls(order_id, invoice_id, generated_image_id, image_resize_id) <= 1)`
- `CONSTRAINT "chk_credit_tx_balance_nonnegative" CHECK (balance_after >= 0)`
- `CONSTRAINT "chk_credit_tx_amount_by_type" CHECK ( (type IN ('SUBSCRIPTION_CREDIT', 'TOP_UP', 'COUPON_CREDIT', 'REFUND') AND amount > 0) OR (type IN ('GENERATION', 'EXPIRATION') AND amount < 0) OR type = 'ADJUSTMENT' )`

**`workspace_invites`**
- `CONSTRAINT "chk_workspace_invites_email_by_type" CHECK ((type = 'EMAIL') = (email IS NOT NULL))`
- `CONSTRAINT "chk_workspace_invites_max_uses_by_type" CHECK ((type = 'LINK') = (max_uses IS NOT NULL))`
- `CONSTRAINT "chk_workspace_invites_max_uses_positive" CHECK (max_uses IS NULL OR max_uses >= 1)`

## 6. Tabelas fora do modelo final

| Tabela | Categoria | Ação |
| --- | --- | --- |
| `activity_events` | extensão de ADR | manter |
| `auth_sessions` | extensão de ADR | manter |
| `content_text_versions` | extensão de ADR | manter |
| `outbox_events` | extensão de ADR | manter |
| `agent_workflow_runs` | legado com consumidores | decidir em issue própria |
| `agent_workflow_steps` | legado com consumidores | decidir em issue própria |
| `assets` | legado com consumidores | decidir em issue própria |
| `brand_settings` | legado com consumidores | decidir em issue própria |
| `contents` | legado com consumidores | decidir em issue própria |
| `generation_job_status_events` | legado com consumidores | decidir em issue própria |
| `generation_jobs` | legado com consumidores | decidir em issue própria |
| `generations` | legado com consumidores | decidir em issue própria |
| `images` | legado com consumidores | decidir em issue própria |
| `projects` | legado com consumidores | decidir em issue própria |
| `settings` | legado com consumidores | decidir em issue própria |
| `provider_customers` | sem alvo no modelo final | remover após migrar consumidores |
| `provider_subscriptions` | sem alvo no modelo final | remover após migrar consumidores |

