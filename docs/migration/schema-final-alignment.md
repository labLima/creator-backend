# Alinhamento ao Creator_DB_final.sql

> Gerado por `scripts/schema_parity_report.py` a partir de
> `docs/migration/Creator_DB_final.sql` contra `Base.metadata`.
> Não edite à mão: regenere o arquivo.

## Resumo

- Dump: `sha256 619512b778e1f03a315efe5d7d8710a5a540442b5df66ddc144b78e915bbb583`
- Tabelas no modelo final: **54**
- Tabelas no metadata atual: **71**
- Tipos ENUM: **52**
- Índices: **173** (50 nomeados, 123 anônimos)
- Foreign keys: **101** (10 compostas)
- Funções/triggers/views: **70**
- Divergências: **291**

## Divergências por categoria

| Categoria | Ocorrências |
| --- | --- |
| `table_missing` | 0 |
| `table_extra` | 0 |
| `allowlisted` | 17 |
| `rename_collision` | 0 |
| `pk_mismatch` | 0 |
| `column_missing` | 50 |
| `column_extra` | 33 |
| `nullability` | 1 |
| `width` | 14 |
| `kind` | 3 |
| `enum` | 9 |
| `unique_missing` | 1 |
| `unique_extra` | 3 |
| `index_missing` | 46 |
| `index_extra` | 1 |
| `index_name` | 12 |
| `fk_missing` | 14 |
| `fk_extra` | 15 |
| `fk_ondelete` | 10 |
| `check_missing` | 27 |
| `check_extra` | 30 |
| `default_missing` | 5 |
| `default_value` | 0 |

## 1. Tabelas com nome divergente

O mapa é aplicado uma vez na comparação, então a tabela renomeada não conta
como ausente nem excedente. Nenhum caso é `ALTER TABLE ... RENAME` puro:
`role` muda de vocabulário, entra `status` e sai `deleted_at`.

| Final | Metadata |
| --- | --- |

## 2. Tabelas do modelo final ausentes no ORM

Nenhuma.

## 3. Colunas, tipos e nullability

Total: **103**.

### `column_missing` (50)

- `charges.canceled_amount_cents`
- `charges.canceled_at`
- `charges.code`
- `charges.due_at`
- `charges.external_id`
- `charges.funding_source`
- `charges.gateway_id`
- `charges.installments`
- `charges.order_id`
- `charges.paid_amount_cents`
- `charges.paid_at`
- `charges.payment_method`
- `charges.payment_method_id`
- `charges.provider`
- `charges.provider_payload`
- `coupon_redemptions.canceled_at`
- `coupon_redemptions.credit_transaction_id`
- `coupon_redemptions.currency`
- `coupon_redemptions.external_id`
- `coupon_redemptions.invoice_id`
- `coupon_redemptions.once_per_workspace`
- `coupon_redemptions.provider`
- `coupon_redemptions.redeemed_at`
- `coupon_redemptions.user_id`
- `coupon_redemptions.workspace_id`
- `coupons.credits`
- `coupons.credits_validity_days`
- `coupons.currency`
- `credit_packages.credits`
- `credit_packages.credits_validity_days`
- `invoices.external_id`
- `invoices.provider`
- `orders.code`
- `orders.external_id`
- `orders.provider`
- `provider_webhook_events.external_id`
- `refunds.charge_id`
- `refunds.external_id`
- `refunds.metadata`
- `refunds.processed_at`
- `refunds.provider`
- `refunds.reason_code`
- `refunds.requested_by`
- `workspace_credit_transactions.balance_after`
- `workspace_credit_transactions.created_by`
- `workspace_credit_transactions.generated_image_id`
- `workspace_credit_transactions.image_resize_id`
- `workspace_credit_transactions.invoice_id`
- `workspace_credit_transactions.order_id`
- `workspace_credit_transactions.type`

### `column_extra` (33)

- `charges.deleted_at`
- `charges.provider_card_id`
- `charges.provider_charge_id`
- `coupon_redemptions.billing_account_id`
- `coupon_redemptions.deleted_at`
- `coupon_redemptions.provider_discount_id`
- `coupons.credits_amount`
- `coupons.redemptions_count`
- `credit_packages.code`
- `credit_packages.credits_amount`
- `credit_packages.deleted_at`
- `invoices.deleted_at`
- `invoices.provider_charge_id`
- `invoices.provider_invoice_id`
- `orders.closed`
- `orders.deleted_at`
- `orders.provider_order_id`
- `provider_webhook_events.created_at`
- `provider_webhook_events.deleted_at`
- `provider_webhook_events.provider_event_id`
- `refunds.billing_account_id`
- `refunds.deleted_at`
- `refunds.invoice_id`
- `refunds.provider_charge_id`
- `refunds.provider_refund_id`
- `refunds.reason`
- `users.global_role`
- `users.password_hash`
- `workspace_credit_transactions.deleted_at`
- `workspace_credit_transactions.reference_id`
- `workspace_credit_transactions.reference_type`
- `workspace_credit_transactions.transaction_type`
- `workspace_credit_transactions.updated_at`

### `nullability` (1)

- `invoices.subscription_id: final NOT NULL, model nullable`

### `width` (14)

- `charges.amount_cents: final bigint, model integer`
- `charges.status: final unbounded varchar, model varchar(20)`
- `coupon_redemptions.discount_amount_cents: final bigint, model integer`
- `coupons.min_purchase_cents: final bigint, model integer`
- `credit_packages.name: final unbounded varchar, model varchar(64)`
- `credit_packages.price_cents: final bigint, model integer`
- `invoices.amount_cents: final bigint, model integer`
- `invoices.total_discount_cents: final bigint, model integer`
- `invoices.total_increment_cents: final bigint, model integer`
- `invoices.url: final unbounded varchar, model varchar(2048)`
- `orders.amount_cents: final bigint, model integer`
- `orders.discount_cents: final bigint, model integer`
- `orders.subtotal_cents: final bigint, model integer`
- `refunds.amount_cents: final bigint, model integer`

### `default_missing` (5)

- `charges.currency: final default 'BRL'`
- `credit_packages.currency: final default 'BRL'`
- `invoices.currency: final default 'BRL'`
- `orders.currency: final default 'BRL'`
- `refunds.currency: final default 'BRL'`

## 4. Enums

Total: **9**.

### `enum` (9)

- `coupon_redemptions.status: model has no vocabulary (expected ['APPLIED', 'CANCELED'])`
- `coupons.applies_to: model has no vocabulary (expected ['SUBSCRIPTION_AND_CREDITS', 'SUBSCRIPTION_ONLY', 'CREDITS_ONLY'])`
- `coupons.type: model has no vocabulary (expected ['DISCOUNT', 'CREDIT'])`
- `invoices.payment_method: model has no vocabulary (expected ['CREDIT_CARD', 'DEBIT_CARD', 'BOLETO', 'PIX'])`
- `invoices.status: model has no vocabulary (expected ['PENDING', 'PAID', 'CANCELED', 'SCHEDULED', 'FAILED'])`
- `orders.status: model has no vocabulary (expected ['PENDING', 'PAID', 'CANCELED', 'FAILED'])`
- `provider_webhook_events.provider: model has no vocabulary (expected ['PAGARME', 'STRIPE'])`
- `provider_webhook_events.status: model has no vocabulary (expected ['RECEIVED', 'PROCESSING', 'PROCESSED', 'FAILED', 'IGNORED'])`
- `refunds.status: model has no vocabulary (expected ['PENDING', 'SUCCEEDED', 'FAILED'])`

## 5. Índices

Total: **59**.

### `index_missing` (46)

- `captions: UNIQUE (post_id) WHERE is_current and deleted_at is null`
- `charges: (billing_account_id, status)`
- `charges: (code)`
- `charges: (invoice_id)`
- `charges: (order_id)`
- `charges: (paid_at)`
- `charges: (payment_method_id) WHERE payment_method_id is not null`
- `charges: (status)`
- `charges: UNIQUE (provider, external_id)`
- `coupon_redemptions: (coupon_id, workspace_id)`
- `coupon_redemptions: (credit_transaction_id) WHERE credit_transaction_id is not null`
- `coupon_redemptions: (invoice_id) WHERE invoice_id is not null`
- `coupon_redemptions: (order_id, workspace_id)`
- `coupon_redemptions: (subscription_id, workspace_id)`
- `coupon_redemptions: (user_id)`
- `coupon_redemptions: (workspace_id)`
- `coupon_redemptions: UNIQUE (coupon_id, workspace_id) WHERE once_per_workspace and status = 'applied'`
- `coupon_redemptions: UNIQUE (provider, external_id)`
- `coupons: (created_by) WHERE created_by is not null`
- `coupons: (is_active)`
- `coupons: (type)`
- `coupons: UNIQUE (code) WHERE deleted_at is null`
- `invoices: (billing_account_id)`
- `invoices: (status, due_at)`
- `invoices: (subscription_id, due_at)`
- `invoices: UNIQUE (provider, external_id)`
- `orders: (billing_account_id)`
- `orders: (credit_package_id) WHERE credit_package_id is not null`
- `orders: (status)`
- `orders: (workspace_id)`
- `orders: UNIQUE (id, workspace_id)`
- `orders: UNIQUE (provider, external_id)`
- `provider_webhook_events: (event_type)`
- `provider_webhook_events: (resource_id)`
- `provider_webhook_events: (status, received_at)`
- `provider_webhook_events: UNIQUE (provider, external_id)`
- `refunds: (charge_id)`
- `refunds: (requested_by) WHERE requested_by is not null`
- `refunds: (status)`
- `refunds: UNIQUE (provider, external_id)`
- `workspace_credit_transactions: (created_by) WHERE created_by is not null`
- `workspace_credit_transactions: (workspace_id, created_at)`
- `workspace_credit_transactions: UNIQUE (generated_image_id, type)`
- `workspace_credit_transactions: UNIQUE (image_resize_id, type)`
- `workspace_credit_transactions: UNIQUE (invoice_id, type)`
- `workspace_credit_transactions: UNIQUE (order_id, type)`

### `index_extra` (1)

- `captions: UNIQUE (post_id) WHERE is_current`

### `index_name` (12)

- `charges: missing index name idx_m8_charges_payment_method_id`
- `coupon_redemptions: missing index name idx_m8_coupon_redemptions_credit_transaction_id`
- `coupon_redemptions: missing index name idx_m8_coupon_redemptions_invoice_id`
- `coupon_redemptions: missing index name uq_coupon_redemptions_once_per_workspace`
- `coupons: missing index name idx_m8_coupons_created_by`
- `coupons: missing index name uq_coupons_code_active`
- `image_resizes: missing index name idx_image_resizes_source_image`
- `image_resizes: missing index name uq_image_resizes_storage`
- `orders: missing index name idx_m8_orders_credit_package_id`
- `refunds: missing index name idx_m8_refunds_requested_by`
- `workspace_credit_transactions: missing index name idx_m8_workspace_credit_transactions_created_by`
- `workspace_credit_transactions: missing index name uq_credit_tx_image_resize`

## 6. Foreign keys

Total: **39**.

### `fk_missing` (14)

- `charges['order_id']->orders['id'] [SET NULL]`
- `charges['payment_method_id']->billing_payment_methods['id'] [SET NULL]`
- `coupon_redemptions['credit_transaction_id']->workspace_credit_transactions['id'] [SET NULL]`
- `coupon_redemptions['invoice_id']->invoices['id'] [SET NULL]`
- `coupon_redemptions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`
- `coupon_redemptions['subscription_id', 'workspace_id']->subscriptions['id', 'workspace_id'] [RESTRICT]`
- `coupon_redemptions['user_id']->users['id'] [RESTRICT]`
- `refunds['charge_id']->charges['id'] [RESTRICT]`
- `refunds['requested_by']->users['id'] [SET NULL]`
- `workspace_credit_transactions['created_by']->users['id'] [SET NULL]`
- `workspace_credit_transactions['generated_image_id']->generated_images['id'] [RESTRICT]`
- `workspace_credit_transactions['image_resize_id']->image_resizes['id'] [RESTRICT]`
- `workspace_credit_transactions['invoice_id']->invoices['id'] [RESTRICT]`
- `workspace_credit_transactions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`

### `fk_extra` (15)

- `charges['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `charges['invoice_id']->invoices['id'] [NO ACTION]`
- `coupon_redemptions['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `coupon_redemptions['coupon_id']->coupons['id'] [NO ACTION]`
- `coupon_redemptions['order_id']->orders['id'] [NO ACTION]`
- `coupon_redemptions['subscription_id']->subscriptions['id'] [NO ACTION]`
- `coupons['created_by']->users['id'] [NO ACTION]`
- `invoices['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `invoices['subscription_id']->subscriptions['id'] [NO ACTION]`
- `orders['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `orders['credit_package_id']->credit_packages['id'] [NO ACTION]`
- `orders['workspace_id']->workspaces['id'] [NO ACTION]`
- `refunds['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `refunds['invoice_id']->invoices['id'] [NO ACTION]`
- `workspace_credit_transactions['workspace_id']->workspaces['id'] [NO ACTION]`

### `fk_ondelete` (10)

- `charges['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `charges['invoice_id']->invoices['id']: final SET NULL vs model ['NO ACTION']`
- `coupon_redemptions['coupon_id']->coupons['id']: final RESTRICT vs model ['NO ACTION']`
- `coupons['created_by']->users['id']: final SET NULL vs model ['NO ACTION']`
- `invoices['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `invoices['subscription_id']->subscriptions['id']: final RESTRICT vs model ['NO ACTION']`
- `orders['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `orders['credit_package_id']->credit_packages['id']: final SET NULL vs model ['NO ACTION']`
- `orders['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`
- `workspace_credit_transactions['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`

## 7. CHECK constraints

Total: **57**.

### `check_missing` (27)

- `unmapped:charges.chk_charges_cents_nonnegative`
- `unmapped:charges.chk_charges_currency_format`
- `unmapped:charges.chk_charges_installments`
- `unmapped:coupon_redemptions.chk_coupon_redemptions_amount_nonnegative`
- `unmapped:coupon_redemptions.chk_coupon_redemptions_currency_format`
- `unmapped:coupon_redemptions.chk_coupon_redemptions_discount_percent`
- `unmapped:coupon_redemptions.chk_coupon_redemptions_single_target`
- `unmapped:coupons.chk_coupons_code_upper`
- `unmapped:coupons.chk_coupons_currency_format`
- `unmapped:coupons.chk_coupons_discount_percent`
- `unmapped:coupons.chk_coupons_min_purchase_nonnegative`
- `unmapped:coupons.chk_coupons_type_exclusive_fields`
- `unmapped:credit_packages.chk_credit_packages_currency_format`
- `unmapped:credit_packages.chk_credit_packages_price_nonnegative`
- `unmapped:invoices.chk_invoices_cents_nonnegative`
- `unmapped:invoices.chk_invoices_currency_format`
- `unmapped:invoices.chk_invoices_installments`
- `unmapped:orders.chk_orders_amount_consistency`
- `unmapped:orders.chk_orders_cents_nonnegative`
- `unmapped:orders.chk_orders_currency_format`
- `unmapped:refunds.chk_refunds_amount_nonnegative`
- `unmapped:refunds.chk_refunds_currency_format`
- `unmapped:refunds.chk_refunds_processed_by_status`
- `unmapped:workspace_credit_transactions.chk_credit_tx_amount_by_type`
- `unmapped:workspace_credit_transactions.chk_credit_tx_balance_nonnegative`
- `unmapped:workspace_credit_transactions.chk_credit_tx_single_reference`
- `unmapped:workspace_credit_transactions.workspace_credit_transactions.amount`

### `check_extra` (30)

- `brand_assets.brand_asset_type`
- `campaign_voices.campaign_voice`
- `content_plan_items.content_format`
- `fiscal_invoices.fiscal_invoice_status`
- `generated_images.approval_status`
- `generated_images.generation_status`
- `generated_images.image_feedback_type`
- `image_resizes.art_ratio`
- `image_resizes.resize_status`
- `notification_preferences.notification_channel`
- `notification_preferences.notification_type`
- `notification_recipients.notification_channel`
- `notification_recipients.notification_delivery_status`
- `notifications.notification_resource_type`
- `notifications.notification_type`
- `personas.age_range`
- `personas.persona_gender`
- `plan_payment_methods.payment_method_type`
- `post_designs.art_ratio`
- `post_designs.content_format`
- `posts.approval_status`
- `posts.publication_status`
- `user_consents.consent_type`
- `user_devices.device_platform`
- `users.global_role`
- `workspace_invites.invite_status`
- `workspace_invites.invite_type`
- `workspace_invites.workspace_role`
- `workspace_members.member_status`
- `workspace_members.workspace_role`

## 8. Funções, triggers e views

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

## 9. Tabelas fora do modelo final

| Tabela | Categoria |
| --- | --- |
| `auth_sessions` | extensão de ADR (preservada) |
| `outbox_events` | extensão de ADR (preservada) |
| `activity_events` | extensão de ADR (preservada) |
| `content_text_versions` | extensão de ADR (preservada) |
| `agent_workflow_runs` | legado com consumidores (ADR-029 decide) |
| `agent_workflow_steps` | legado com consumidores (ADR-029 decide) |
| `assets` | legado com consumidores (ADR-029 decide) |
| `brand_settings` | legado com consumidores (ADR-029 decide) |
| `contents` | legado com consumidores (ADR-029 decide) |
| `generation_job_status_events` | legado com consumidores (ADR-029 decide) |
| `generation_jobs` | legado com consumidores (ADR-029 decide) |
| `generations` | legado com consumidores (ADR-029 decide) |
| `images` | legado com consumidores (ADR-029 decide) |
| `projects` | legado com consumidores (ADR-029 decide) |
| `settings` | legado com consumidores (ADR-029 decide) |
| `provider_customers` | sem alvo no modelo final (ADR-029 decide) |
| `provider_subscriptions` | sem alvo no modelo final (ADR-029 decide) |

