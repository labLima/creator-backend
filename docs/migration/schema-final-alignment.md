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
- Divergências: **689**

## Divergências por categoria

| Categoria | Ocorrências |
| --- | --- |
| `table_missing` | 6 |
| `table_extra` | 4 |
| `allowlisted` | 17 |
| `rename_collision` | 0 |
| `pk_mismatch` | 0 |
| `column_missing` | 129 |
| `column_extra` | 115 |
| `nullability` | 11 |
| `width` | 27 |
| `kind` | 4 |
| `enum` | 34 |
| `unique_missing` | 4 |
| `unique_extra` | 7 |
| `index_missing` | 100 |
| `index_extra` | 3 |
| `index_name` | 27 |
| `fk_missing` | 33 |
| `fk_extra` | 49 |
| `fk_ondelete` | 35 |
| `check_missing` | 58 |
| `check_extra` | 20 |
| `default_missing` | 6 |
| `default_value` | 0 |

## 1. Tabelas com nome divergente

O mapa é aplicado uma vez na comparação, então a tabela renomeada não conta
como ausente nem excedente. Nenhum caso é `ALTER TABLE ... RENAME` puro:
`role` muda de vocabulário, entra `status` e sai `deleted_at`.

| Final | Metadata |
| --- | --- |

## 2. Tabelas do modelo final ausentes no ORM

- **`captions`** (8 colunas, 1 CHECKs): `id`, `post_id`, `created_by`, `body`, `version`, `is_current`, `created_at`, `updated_at`
- **`design_slides`** (9 colunas, 1 CHECKs): `id`, `post_design_id`, `position`, `headline`, `subtitle`, `cta`, `art_direction`, `created_at`, `updated_at`
- **`generated_images`** (23 colunas, 9 CHECKs): `id`, `design_slide_id`, `storage_bucket`, `storage_key`, `mime_type`, `size_bytes`, `width`, `height`, `model`, `prompt`, `created_by`, `error_message`, `generation_status`, `is_current`, `approval_status`, `approved_by`, `approved_at`, `rejection_reason`, `feedback_type`, `feedback_text`, `created_at`, `updated_at`, `deleted_at`
- **`image_resizes`** (14 colunas, 4 CHECKs): `id`, `source_image_id`, `ratio`, `status`, `storage_bucket`, `storage_key`, `mime_type`, `size_bytes`, `width`, `height`, `error_message`, `created_by`, `created_at`, `updated_at`
- **`post_designs`** (6 colunas, 1 CHECKs): `id`, `post_id`, `format`, `ratio`, `created_at`, `updated_at`
- **`posts`** (17 colunas, 6 CHECKs): `id`, `content_plan_id`, `created_by`, `title`, `objective`, `big_idea`, `main_message`, `publication_status`, `approval_status`, `approved_by`, `approved_at`, `rejection_reason`, `scheduled_at`, `published_at`, `created_at`, `updated_at`, `deleted_at`

## 3. Colunas, tipos e nullability

Total: **288**.

### `column_missing` (129)

- `billing_accounts.document_hash`
- `billing_accounts.external_code`
- `billing_accounts.external_id`
- `billing_addresses.country`
- `billing_addresses.district`
- `billing_addresses.external_id`
- `billing_addresses.is_default`
- `billing_addresses.line_1`
- `billing_addresses.line_2`
- `billing_addresses.metadata`
- `billing_addresses.status`
- `billing_payment_methods.billing_address_id`
- `billing_payment_methods.brand`
- `billing_payment_methods.external_id`
- `billing_payment_methods.external_network_token_id`
- `billing_payment_methods.first_six_digits`
- `billing_payment_methods.metadata`
- `billing_payment_methods.status`
- `billing_payment_methods.type`
- `brand_assets.created_by`
- `brand_assets.storage_bucket`
- `brand_assets.storage_key`
- `brand_colors.hex`
- `brand_colors.name`
- `brand_colors.position`
- `brands.created_by`
- `brands.goals`
- `brands.indicators`
- `brands.inspirations`
- `brands.promise`
- `brands.restrictions`
- `brands.segment`
- `campaigns.expected_action`
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
- `notification_recipients.external_message_id`
- `orders.code`
- `orders.external_id`
- `orders.provider`
- `personas.age_range`
- `personas.trigger_event`
- `plan_items.currency`
- `plan_items.external_id`
- `plan_items.provider`
- `plans.billing_interval`
- `plans.billing_type`
- `plans.credits_per_month`
- `plans.credits_validity_days`
- `plans.currency`
- `plans.external_id`
- `plans.interval_count`
- `plans.minimum_price_cents`
- `plans.price_cents`
- `plans.provider`
- `plans.statement_descriptor`
- `plans.status`
- `plans.trial_period_days`
- `provider_disputes.amount_cents`
- `provider_disputes.currency`
- `provider_disputes.external_id`
- `provider_disputes.provider`
- `provider_disputes.resolved_at`
- `provider_disputes.result`
- `provider_idempotency_keys.expires_at`
- `provider_webhook_events.external_id`
- `refunds.charge_id`
- `refunds.external_id`
- `refunds.metadata`
- `refunds.processed_at`
- `refunds.provider`
- `refunds.reason_code`
- `refunds.requested_by`
- `subscription_history.changed_by`
- `subscription_history.new_plan_id`
- `subscription_history.new_provider_status`
- `subscription_history.new_status`
- `subscription_history.old_plan_id`
- `subscription_history.old_provider_status`
- `subscription_history.old_status`
- `subscription_history.reason_code`
- `subscription_history.reason_text`
- `subscriptions.billing_interval`
- `subscriptions.contracted_price_cents`
- `subscriptions.currency`
- `subscriptions.current_cycle_id`
- `subscriptions.external_code`
- `subscriptions.external_id`
- `subscriptions.payment_method_id`
- `subscriptions.provider`
- `subscriptions.status_reason`
- `users.auth_provider_id`
- `workspace_credit_transactions.balance_after`
- `workspace_credit_transactions.created_by`
- `workspace_credit_transactions.generated_image_id`
- `workspace_credit_transactions.image_resize_id`
- `workspace_credit_transactions.invoice_id`
- `workspace_credit_transactions.order_id`
- `workspace_credit_transactions.type`
- `workspace_invites.token_hash`

### `column_extra` (115)

- `billing_accounts.deleted_at`
- `billing_accounts.document_type`
- `billing_accounts.provider_customer_code`
- `billing_accounts.provider_customer_id`
- `billing_addresses.complement`
- `billing_addresses.deleted_at`
- `billing_addresses.neighborhood`
- `billing_addresses.street`
- `billing_payment_methods.card_brand`
- `billing_payment_methods.card_status`
- `billing_payment_methods.card_type`
- `billing_payment_methods.deleted_at`
- `billing_payment_methods.provider_card_id`
- `brand_assets.deleted_at`
- `brand_assets.file_url`
- `brand_colors.brand_goals`
- `brand_colors.brand_indicators`
- `brand_colors.brand_inspirations`
- `brand_colors.brand_main_hashtags`
- `brand_colors.brand_name`
- `brand_colors.brand_promise`
- `brand_colors.brand_restrictions`
- `brand_colors.brand_segment`
- `brand_colors.brand_values`
- `brand_colors.color_name`
- `brand_colors.created_by`
- `brand_colors.deleted_at`
- `brand_colors.hex_code`
- `brand_colors.order`
- `brand_colors.workspace_id`
- `brands.brand_voice`
- `brands.created_by_user_id`
- `brands.description`
- `brands.metadata`
- `campaigns.end_at`
- `campaigns.start_at`
- `campaigns.voice`
- `campaigns.workspace_id`
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
- `notification_preferences.deleted_at`
- `notification_recipients.deleted_at`
- `notification_recipients.provider_message_id`
- `notification_recipients.workspace_member_id`
- `notifications.deleted_at`
- `orders.closed`
- `orders.deleted_at`
- `orders.provider_order_id`
- `personas.age`
- `personas.interest`
- `personas.trigger`
- `plan_items.deleted_at`
- `plan_items.gateway_id`
- `plan_items.provider_plan_item_id`
- `plans.code`
- `plans.description`
- `plans.is_active`
- `provider_disputes.code`
- `provider_disputes.deleted_at`
- `provider_disputes.provider_dispute_id`
- `provider_idempotency_keys.deleted_at`
- `provider_webhook_events.created_at`
- `provider_webhook_events.deleted_at`
- `provider_webhook_events.provider_event_id`
- `refunds.billing_account_id`
- `refunds.deleted_at`
- `refunds.invoice_id`
- `refunds.provider_charge_id`
- `refunds.provider_refund_id`
- `refunds.reason`
- `subscription_history.deleted_at`
- `subscription_history.plan_id`
- `subscription_history.previous_plan_id`
- `subscription_history.previous_status`
- `subscription_history.reason`
- `subscription_history.status`
- `subscription_history.updated_at`
- `subscriptions.billing_day`
- `subscriptions.deleted_at`
- `subscriptions.interval`
- `subscriptions.provider_card_id`
- `subscriptions.provider_code`
- `subscriptions.provider_subscription_id`
- `subscriptions.start_at`
- `user_devices.deleted_at`
- `users.cnpj`
- `users.cpf`
- `users.external_id`
- `users.global_role`
- `users.password_hash`
- `workspace_credit_transactions.deleted_at`
- `workspace_credit_transactions.reference_id`
- `workspace_credit_transactions.reference_type`
- `workspace_credit_transactions.transaction_type`
- `workspace_credit_transactions.updated_at`
- `workspace_invite_usages.created_at`
- `workspace_invite_usages.deleted_at`
- `workspace_invite_usages.user_id`
- `workspace_invite_usages.workspace_id`
- `workspace_invites.deleted_at`
- `workspace_invites.is_active`
- `workspace_invites.token`
- `workspace_invites.uses_count`

### `nullability` (11)

- `billing_accounts.provider: final NOT NULL, model nullable`
- `billing_addresses.city: final NOT NULL, model nullable`
- `billing_addresses.number: final NOT NULL, model nullable`
- `billing_addresses.state: final NOT NULL, model nullable`
- `billing_addresses.zip_code: final NOT NULL, model nullable`
- `campaigns.brand_id: final NOT NULL, model nullable`
- `invoices.subscription_id: final NOT NULL, model nullable`
- `plan_items.status: final NOT NULL, model nullable`
- `subscriptions.installments: final NOT NULL, model nullable`
- `users.display_name: final NOT NULL, model nullable`
- `workspace_invite_usages.member_id: final NOT NULL, model nullable`

### `width` (27)

- `billing_accounts.email: final varchar(254), model varchar(64)`
- `billing_addresses.number: final varchar(20), model varchar(16)`
- `billing_addresses.state: final varchar(2), model varchar(16)`
- `billing_addresses.zip_code: final varchar(8), model varchar(16)`
- `brand_assets.description: final unbounded varchar, model varchar(500)`
- `brand_assets.file_name: final unbounded varchar, model varchar(255)`
- `brands.name: final varchar(100), model varchar(255)`
- `campaigns.name: final varchar(100), model varchar(30)`
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
- `personas.name: final varchar(100), model varchar(30)`
- `plan_items.price_cents: final bigint, model integer`
- `refunds.amount_cents: final bigint, model integer`
- `subscriptions.minimum_price_cents: final bigint, model integer`
- `users.email: final varchar(254), model varchar(320)`
- `workspace_invites.email: final varchar(254), model varchar(255)`

### `default_missing` (6)

- `charges.currency: final default 'BRL'`
- `credit_packages.currency: final default 'BRL'`
- `invoices.currency: final default 'BRL'`
- `orders.currency: final default 'BRL'`
- `refunds.currency: final default 'BRL'`
- `subscriptions.installments: final default 1`

## 4. Enums

Total: **34**.

### `enum` (34)

- `billing_accounts.payer_type: model has no vocabulary (expected ['INDIVIDUAL', 'COMPANY'])`
- `billing_accounts.provider: model has no vocabulary (expected ['PAGARME', 'STRIPE'])`
- `brand_assets.type: model has no vocabulary (expected ['LOGO', 'IMAGE', 'FONT', 'ICON', 'DOCUMENT', 'OTHER'])`
- `coupon_redemptions.status: model has no vocabulary (expected ['APPLIED', 'CANCELED'])`
- `coupons.applies_to: model has no vocabulary (expected ['SUBSCRIPTION_AND_CREDITS', 'SUBSCRIPTION_ONLY', 'CREDITS_ONLY'])`
- `coupons.type: model has no vocabulary (expected ['DISCOUNT', 'CREDIT'])`
- `invoices.payment_method: model has no vocabulary (expected ['CREDIT_CARD', 'DEBIT_CARD', 'BOLETO', 'PIX'])`
- `invoices.status: model has no vocabulary (expected ['PENDING', 'PAID', 'CANCELED', 'SCHEDULED', 'FAILED'])`
- `notification_preferences.channel: model has no vocabulary (expected ['EMAIL', 'IN_APP', 'PUSH'])`
- `notification_preferences.type: model has no vocabulary (expected ['CONTENT_GENERATION', 'CONTENT_APPROVAL', 'INVITE', 'BILLING', 'CREDITS', 'COUPON', 'SYSTEM'])`
- `notification_recipients.channel: model has no vocabulary (expected ['EMAIL', 'IN_APP', 'PUSH'])`
- `notification_recipients.status: model has no vocabulary (expected ['PENDING', 'SENT', 'FAILED'])`
- `notifications.resource_type: model has no vocabulary (expected ['WORKSPACE_INVITE', 'WORKSPACE_MEMBER', 'POST', 'GENERATED_IMAGE', 'SUBSCRIPTION', 'ORDER', 'INVOICE', 'CHARGE', 'COUPON'])`
- `notifications.type: model has no vocabulary (expected ['CONTENT_GENERATION', 'CONTENT_APPROVAL', 'INVITE', 'BILLING', 'CREDITS', 'COUPON', 'SYSTEM'])`
- `orders.status: model has no vocabulary (expected ['PENDING', 'PAID', 'CANCELED', 'FAILED'])`
- `personas.gender: model has no vocabulary (expected ['MALE', 'FEMALE', 'NON_BINARY', 'OTHER', 'PREFER_NOT_TO_SAY'])`
- `plan_items.pricing_scheme_type: model has no vocabulary (expected ['FLAT', 'TIERED', 'VOLUME', 'STAIRSTEP'])`
- `plan_items.status: model has no vocabulary (expected ['ACTIVE', 'INACTIVE', 'ARCHIVED'])`
- `plans.type: model has no vocabulary (expected ['FREE', 'STARTER', 'PRO', 'STUDIO', 'ENTERPRISE'])`
- `provider_disputes.status: model has no vocabulary (expected ['OPEN', 'UNDER_REVIEW', 'RESOLVED'])`
- `provider_idempotency_keys.provider: model has no vocabulary (expected ['PAGARME', 'STRIPE'])`
- `provider_idempotency_keys.status: model has no vocabulary (expected ['STARTED', 'COMPLETED', 'FAILED'])`
- `provider_webhook_events.provider: model has no vocabulary (expected ['PAGARME', 'STRIPE'])`
- `provider_webhook_events.status: model has no vocabulary (expected ['RECEIVED', 'PROCESSING', 'PROCESSED', 'FAILED', 'IGNORED'])`
- `refunds.status: model has no vocabulary (expected ['PENDING', 'SUCCEEDED', 'FAILED'])`
- `subscription_history.change_type: model has no vocabulary (expected ['CREATE', 'UPGRADE', 'DOWNGRADE', 'CANCEL', 'RENEW'])`
- `subscriptions.billing_type: model has no vocabulary (expected ['PREPAID', 'POSTPAID'])`
- `subscriptions.payment_method: model has no vocabulary (expected ['CREDIT_CARD', 'DEBIT_CARD', 'BOLETO', 'PIX'])`
- `subscriptions.provider_status: model has no vocabulary (expected ['ACTIVE', 'CANCELED', 'FUTURE'])`
- `subscriptions.status: model has no vocabulary (expected ['ACTIVE', 'TRIALING', 'PAST_DUE', 'CANCELED', 'EXPIRED'])`
- `user_devices.platform: model has no vocabulary (expected ['IOS', 'ANDROID', 'WEB'])`
- `workspace_invites.role: model has no vocabulary (expected ['OWNER', 'MANAGER', 'EDITOR', 'VIEWER'])`
- `workspace_invites.status: model has no vocabulary (expected ['PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED'])`
- `workspace_invites.type: model has no vocabulary (expected ['EMAIL', 'LINK'])`

## 5. Índices

Total: **130**.

### `index_missing` (100)

- `billing_accounts: (document_hash)`
- `billing_accounts: (user_id)`
- `billing_accounts: UNIQUE (provider, external_id)`
- `billing_addresses: (billing_account_id)`
- `billing_addresses: UNIQUE (billing_account_id) WHERE is_default and status = 'active'`
- `billing_payment_methods: (billing_account_id, is_default)`
- `billing_payment_methods: (billing_address_id) WHERE billing_address_id is not null`
- `billing_payment_methods: UNIQUE (billing_account_id) WHERE is_default and status = 'active'`
- `billing_payment_methods: UNIQUE (billing_account_id, external_id)`
- `brand_assets: (brand_id)`
- `brand_assets: (created_by)`
- `brand_assets: UNIQUE (storage_bucket, storage_key)`
- `brand_colors: (brand_id)`
- `brands: (created_by) WHERE created_by is not null`
- `brands: (workspace_id)`
- `campaigns: (created_by) WHERE created_by is not null`
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
- `notification_preferences: UNIQUE (user_id, type, channel)`
- `notification_recipients: (user_id, channel)`
- `notification_recipients: (user_id, created_at)`
- `notification_recipients: (user_id, read_at)`
- `notification_recipients: UNIQUE (notification_id, user_id, channel)`
- `notifications: (created_at)`
- `notifications: (created_by) WHERE created_by is not null`
- `notifications: (type)`
- `notifications: UNIQUE (workspace_id, dedupe_key)`
- `orders: (billing_account_id)`
- `orders: (credit_package_id) WHERE credit_package_id is not null`
- `orders: (status)`
- `orders: (workspace_id)`
- `orders: UNIQUE (id, workspace_id)`
- `orders: UNIQUE (provider, external_id)`
- `personas: (created_by) WHERE created_by is not null`
- `plan_items: (plan_id)`
- `plan_items: UNIQUE (provider, external_id)`
- `plans: UNIQUE (provider, external_id)`
- `provider_disputes: (billing_account_id) WHERE billing_account_id is not null`
- `provider_disputes: (charge_id)`
- `provider_disputes: (status, resolved_at)`
- `provider_disputes: UNIQUE (provider, external_id)`
- `provider_idempotency_keys: (expires_at)`
- `provider_idempotency_keys: UNIQUE (provider, idempotency_key)`
- `provider_webhook_events: (event_type)`
- `provider_webhook_events: (resource_id)`
- `provider_webhook_events: (status, received_at)`
- `provider_webhook_events: UNIQUE (provider, external_id)`
- `refunds: (charge_id)`
- `refunds: (requested_by) WHERE requested_by is not null`
- `refunds: (status)`
- `refunds: UNIQUE (provider, external_id)`
- `subscription_history: (changed_by) WHERE changed_by is not null`
- `subscription_history: (new_plan_id) WHERE new_plan_id is not null`
- `subscription_history: (old_plan_id) WHERE old_plan_id is not null`
- `subscription_history: (subscription_id, created_at)`
- `subscriptions: (billing_account_id)`
- `subscriptions: (next_billing_at)`
- `subscriptions: (payment_method_id) WHERE payment_method_id is not null`
- `subscriptions: (plan_id)`
- `subscriptions: (workspace_id)`
- `subscriptions: UNIQUE (id, workspace_id)`
- `subscriptions: UNIQUE (provider, external_id)`
- `subscriptions: UNIQUE (workspace_id) WHERE status in ('active', 'trialing', 'past_due')`
- `user_devices: (user_id)`
- `users: UNIQUE (email) WHERE deleted_at is null`
- `workspace_credit_transactions: (created_by) WHERE created_by is not null`
- `workspace_credit_transactions: (workspace_id, created_at)`
- `workspace_credit_transactions: UNIQUE (generated_image_id, type)`
- `workspace_credit_transactions: UNIQUE (image_resize_id, type)`
- `workspace_credit_transactions: UNIQUE (invoice_id, type)`
- `workspace_credit_transactions: UNIQUE (order_id, type)`
- `workspace_invite_usages: (member_id)`
- `workspace_invite_usages: UNIQUE (invite_id, member_id)`
- `workspace_invites: (created_by)`
- `workspace_invites: (email)`
- `workspace_invites: (status)`
- `workspace_invites: (workspace_id)`

### `index_extra` (3)

- `brands: (created_by_user_id)`
- `brands: (workspace_id, deleted_at, created_at)`
- `users: (deleted_at)`

### `index_name` (27)

- `billing_addresses: missing index name uq_billing_addresses_default`
- `billing_payment_methods: missing index name idx_m8_billing_payment_methods_billing_address_id`
- `billing_payment_methods: missing index name uq_billing_payment_methods_default`
- `brands: missing index name idx_m8_brands_created_by`
- `campaigns: missing index name idx_m8_campaigns_created_by`
- `charges: missing index name idx_m8_charges_payment_method_id`
- `coupon_redemptions: missing index name idx_m8_coupon_redemptions_credit_transaction_id`
- `coupon_redemptions: missing index name idx_m8_coupon_redemptions_invoice_id`
- `coupon_redemptions: missing index name uq_coupon_redemptions_once_per_workspace`
- `coupons: missing index name idx_m8_coupons_created_by`
- `coupons: missing index name uq_coupons_code_active`
- `notifications: missing index name idx_m8_notifications_created_by`
- `orders: missing index name idx_m8_orders_credit_package_id`
- `personas: missing index name idx_m8_personas_created_by`
- `plan_items: missing index name idx_m8_plan_items_plan_id`
- `provider_disputes: missing index name idx_m8_provider_disputes_billing_account_id`
- `refunds: missing index name idx_m8_refunds_requested_by`
- `subscription_history: missing index name idx_m8_subscription_history_changed_by`
- `subscription_history: missing index name idx_m8_subscription_history_new_plan_id`
- `subscription_history: missing index name idx_m8_subscription_history_old_plan_id`
- `subscriptions: missing index name idx_m8_subscriptions_payment_method_id`
- `subscriptions: missing index name idx_m8_subscriptions_plan_id`
- `subscriptions: missing index name uq_subscriptions_workspace_current`
- `users: missing index name uq_users_email_active`
- `workspace_credit_transactions: missing index name idx_m8_workspace_credit_transactions_created_by`
- `workspace_credit_transactions: missing index name uq_credit_tx_image_resize`
- `workspace_invites: missing index name idx_m8_workspace_invites_created_by`

## 6. Foreign keys

Total: **117**.

### `fk_missing` (33)

- `billing_payment_methods['billing_address_id']->billing_addresses['id'] [SET NULL]`
- `brand_assets['created_by']->users['id'] [SET NULL]`
- `brands['created_by']->users['id'] [SET NULL]`
- `captions['created_by']->users['id'] [SET NULL]`
- `captions['post_id']->posts['id'] [CASCADE]`
- `charges['order_id']->orders['id'] [SET NULL]`
- `charges['payment_method_id']->billing_payment_methods['id'] [SET NULL]`
- `coupon_redemptions['credit_transaction_id']->workspace_credit_transactions['id'] [SET NULL]`
- `coupon_redemptions['invoice_id']->invoices['id'] [SET NULL]`
- `coupon_redemptions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`
- `coupon_redemptions['subscription_id', 'workspace_id']->subscriptions['id', 'workspace_id'] [RESTRICT]`
- `coupon_redemptions['user_id']->users['id'] [RESTRICT]`
- `design_slides['post_design_id']->post_designs['id'] [CASCADE]`
- `generated_images['approved_by']->users['id'] [SET NULL]`
- `generated_images['created_by']->users['id'] [SET NULL]`
- `generated_images['design_slide_id']->design_slides['id'] [CASCADE]`
- `image_resizes['created_by']->users['id'] [SET NULL]`
- `image_resizes['source_image_id']->generated_images['id'] [CASCADE]`
- `post_designs['post_id']->posts['id'] [CASCADE]`
- `posts['approved_by']->users['id'] [SET NULL]`
- `posts['content_plan_id']->content_plans['id'] [CASCADE]`
- `posts['created_by']->users['id'] [SET NULL]`
- `refunds['charge_id']->charges['id'] [RESTRICT]`
- `refunds['requested_by']->users['id'] [SET NULL]`
- `subscription_history['changed_by']->users['id'] [SET NULL]`
- `subscription_history['new_plan_id']->plans['id'] [SET NULL]`
- `subscription_history['old_plan_id']->plans['id'] [SET NULL]`
- `subscriptions['payment_method_id']->billing_payment_methods['id'] [SET NULL]`
- `workspace_credit_transactions['created_by']->users['id'] [SET NULL]`
- `workspace_credit_transactions['generated_image_id']->generated_images['id'] [RESTRICT]`
- `workspace_credit_transactions['image_resize_id']->image_resizes['id'] [RESTRICT]`
- `workspace_credit_transactions['invoice_id']->invoices['id'] [RESTRICT]`
- `workspace_credit_transactions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`

### `fk_extra` (49)

- `billing_accounts['user_id']->users['id'] [CASCADE]`
- `billing_addresses['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `billing_payment_methods['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `brand_assets['brand_id']->brands['id'] [NO ACTION]`
- `brand_colors['brand_id']->brands['id'] [NO ACTION]`
- `brand_colors['created_by']->users['id'] [NO ACTION]`
- `brand_colors['workspace_id']->workspaces['id'] [NO ACTION]`
- `brands['created_by_user_id']->users['id'] [SET NULL]`
- `brands['workspace_id']->workspaces['id'] [RESTRICT]`
- `campaigns['created_by']->users['id'] [NO ACTION]`
- `campaigns['workspace_id']->workspaces['id'] [NO ACTION]`
- `charges['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `charges['invoice_id']->invoices['id'] [NO ACTION]`
- `coupon_redemptions['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `coupon_redemptions['coupon_id']->coupons['id'] [NO ACTION]`
- `coupon_redemptions['order_id']->orders['id'] [NO ACTION]`
- `coupon_redemptions['subscription_id']->subscriptions['id'] [NO ACTION]`
- `coupons['created_by']->users['id'] [NO ACTION]`
- `invoices['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `invoices['subscription_id']->subscriptions['id'] [NO ACTION]`
- `notification_preferences['user_id']->users['id'] [NO ACTION]`
- `notification_recipients['notification_id']->notifications['id'] [NO ACTION]`
- `notification_recipients['user_id']->users['id'] [NO ACTION]`
- `notification_recipients['workspace_member_id']->workspace_members['id'] [NO ACTION]`
- `notifications['created_by']->users['id'] [NO ACTION]`
- `notifications['workspace_id']->workspaces['id'] [NO ACTION]`
- `orders['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `orders['credit_package_id']->credit_packages['id'] [NO ACTION]`
- `orders['workspace_id']->workspaces['id'] [NO ACTION]`
- `personas['brand_id']->brands['id'] [NO ACTION]`
- `personas['created_by']->users['id'] [NO ACTION]`
- `provider_disputes['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `provider_disputes['charge_id']->charges['id'] [NO ACTION]`
- `refunds['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `refunds['invoice_id']->invoices['id'] [NO ACTION]`
- `subscription_history['plan_id']->plans['id'] [NO ACTION]`
- `subscription_history['previous_plan_id']->plans['id'] [NO ACTION]`
- `subscription_history['subscription_id']->subscriptions['id'] [NO ACTION]`
- `subscriptions['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `subscriptions['plan_id']->plans['id'] [NO ACTION]`
- `subscriptions['workspace_id']->workspaces['id'] [NO ACTION]`
- `user_devices['user_id']->users['id'] [NO ACTION]`
- `workspace_credit_transactions['workspace_id']->workspaces['id'] [NO ACTION]`
- `workspace_invite_usages['invite_id']->workspace_invites['id'] [NO ACTION]`
- `workspace_invite_usages['member_id']->workspace_members['id'] [NO ACTION]`
- `workspace_invite_usages['user_id']->users['id'] [NO ACTION]`
- `workspace_invite_usages['workspace_id']->workspaces['id'] [NO ACTION]`
- `workspace_invites['created_by']->users['id'] [NO ACTION]`
- `workspace_invites['workspace_id']->workspaces['id'] [NO ACTION]`

### `fk_ondelete` (35)

- `billing_accounts['user_id']->users['id']: final RESTRICT vs model ['CASCADE']`
- `billing_addresses['billing_account_id']->billing_accounts['id']: final CASCADE vs model ['NO ACTION']`
- `billing_payment_methods['billing_account_id']->billing_accounts['id']: final CASCADE vs model ['NO ACTION']`
- `brand_assets['brand_id']->brands['id']: final CASCADE vs model ['NO ACTION']`
- `brand_colors['brand_id']->brands['id']: final CASCADE vs model ['NO ACTION']`
- `brands['workspace_id']->workspaces['id']: final CASCADE vs model ['RESTRICT']`
- `campaigns['created_by']->users['id']: final SET NULL vs model ['NO ACTION']`
- `charges['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `charges['invoice_id']->invoices['id']: final SET NULL vs model ['NO ACTION']`
- `coupon_redemptions['coupon_id']->coupons['id']: final RESTRICT vs model ['NO ACTION']`
- `coupons['created_by']->users['id']: final SET NULL vs model ['NO ACTION']`
- `invoices['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `invoices['subscription_id']->subscriptions['id']: final RESTRICT vs model ['NO ACTION']`
- `notification_preferences['user_id']->users['id']: final CASCADE vs model ['NO ACTION']`
- `notification_recipients['notification_id']->notifications['id']: final CASCADE vs model ['NO ACTION']`
- `notification_recipients['user_id']->users['id']: final CASCADE vs model ['NO ACTION']`
- `notifications['created_by']->users['id']: final SET NULL vs model ['NO ACTION']`
- `notifications['workspace_id']->workspaces['id']: final CASCADE vs model ['NO ACTION']`
- `orders['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `orders['credit_package_id']->credit_packages['id']: final SET NULL vs model ['NO ACTION']`
- `orders['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`
- `personas['brand_id']->brands['id']: final CASCADE vs model ['NO ACTION']`
- `personas['created_by']->users['id']: final SET NULL vs model ['NO ACTION']`
- `provider_disputes['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `provider_disputes['charge_id']->charges['id']: final RESTRICT vs model ['NO ACTION']`
- `subscription_history['subscription_id']->subscriptions['id']: final CASCADE vs model ['NO ACTION']`
- `subscriptions['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `subscriptions['plan_id']->plans['id']: final RESTRICT vs model ['NO ACTION']`
- `subscriptions['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`
- `user_devices['user_id']->users['id']: final CASCADE vs model ['NO ACTION']`
- `workspace_credit_transactions['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`
- `workspace_invite_usages['invite_id']->workspace_invites['id']: final CASCADE vs model ['NO ACTION']`
- `workspace_invite_usages['member_id']->workspace_members['id']: final CASCADE vs model ['NO ACTION']`
- `workspace_invites['created_by']->users['id']: final RESTRICT vs model ['NO ACTION']`
- `workspace_invites['workspace_id']->workspaces['id']: final CASCADE vs model ['NO ACTION']`

## 7. CHECK constraints

Total: **78**.

### `check_missing` (58)

- `unmapped:billing_accounts.chk_billing_accounts_company_name`
- `unmapped:billing_accounts.chk_billing_accounts_document_pair`
- `unmapped:billing_addresses.chk_billing_addresses_state_uf`
- `unmapped:billing_addresses.chk_billing_addresses_zip_code`
- `unmapped:billing_payment_methods.chk_billing_payment_methods_exp_month`
- `unmapped:billing_payment_methods.chk_billing_payment_methods_exp_year`
- `unmapped:brand_colors.chk_brand_colors_hex`
- `unmapped:charge_transactions.chk_charge_transactions_amount_nonnegative`
- `unmapped:charges.chk_charges_cents_nonnegative`
- `unmapped:charges.chk_charges_currency_format`
- `unmapped:charges.chk_charges_installments`
- `unmapped:content_plan_items.content_plan_items.quantity`
- `unmapped:content_plans.chk_content_plans_period_order`
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
- `unmapped:fiscal_invoices.chk_fiscal_invoices_amount_nonnegative`
- `unmapped:fiscal_invoices.chk_fiscal_invoices_currency_format`
- `unmapped:fiscal_invoices.chk_fiscal_invoices_one_origin`
- `unmapped:invoices.chk_invoices_cents_nonnegative`
- `unmapped:invoices.chk_invoices_currency_format`
- `unmapped:invoices.chk_invoices_installments`
- `unmapped:notifications.chk_notifications_resource_pair`
- `unmapped:orders.chk_orders_amount_consistency`
- `unmapped:orders.chk_orders_cents_nonnegative`
- `unmapped:orders.chk_orders_currency_format`
- `unmapped:plan_items.chk_plan_items_currency_format`
- `unmapped:plan_items.chk_plan_items_price_nonnegative`
- `unmapped:plan_payment_methods.plan_payment_methods.max_installments`
- `unmapped:plans.chk_plans_cents_nonnegative`
- `unmapped:plans.chk_plans_currency_format`
- `unmapped:provider_disputes.chk_provider_disputes_amount_nonnegative`
- `unmapped:provider_disputes.chk_provider_disputes_currency_format`
- `unmapped:provider_disputes.chk_provider_disputes_resolved_at`
- `unmapped:provider_disputes.chk_provider_disputes_result`
- `unmapped:refunds.chk_refunds_amount_nonnegative`
- `unmapped:refunds.chk_refunds_currency_format`
- `unmapped:refunds.chk_refunds_processed_by_status`
- `unmapped:subscriptions.chk_subscriptions_cents_nonnegative`
- `unmapped:subscriptions.chk_subscriptions_currency_format`
- `unmapped:subscriptions.chk_subscriptions_installments`
- `unmapped:workspace_credit_lot_consumptions.workspace_credit_lot_consumptions.amount`
- `unmapped:workspace_credit_lots.chk_credit_lots_amounts`
- `unmapped:workspace_credit_transactions.chk_credit_tx_amount_by_type`
- `unmapped:workspace_credit_transactions.chk_credit_tx_balance_nonnegative`
- `unmapped:workspace_credit_transactions.chk_credit_tx_single_reference`
- `unmapped:workspace_credit_transactions.workspace_credit_transactions.amount`
- `unmapped:workspace_invites.chk_workspace_invites_email_by_type`
- `unmapped:workspace_invites.chk_workspace_invites_max_uses_by_type`
- `unmapped:workspace_invites.chk_workspace_invites_max_uses_positive`

### `check_extra` (20)

- `brands.ck_brands_deleted_after_created`
- `campaign_voices.campaign_voice`
- `charge_transactions.chk_charge_transactions_amount_nonnegative`
- `charge_transactions.payment_provider`
- `charge_transactions.transaction_status`
- `content_plan_items.ck_content_plan_items_quantity`
- `content_plan_items.content_format`
- `content_plans.chk_content_plans_period_order`
- `fiscal_invoices.chk_fiscal_invoices_amount_nonnegative`
- `fiscal_invoices.chk_fiscal_invoices_currency_format`
- `fiscal_invoices.chk_fiscal_invoices_one_origin`
- `fiscal_invoices.fiscal_invoice_status`
- `plan_payment_methods.chk_plan_payment_methods_max_installments`
- `plan_payment_methods.payment_method_type`
- `user_consents.consent_type`
- `users.global_role`
- `workspace_credit_lot_consumptions.chk_lot_consumptions_amount`
- `workspace_credit_lots.chk_credit_lots_amounts`
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

