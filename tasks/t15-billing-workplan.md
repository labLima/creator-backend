# T15 — Plano de trabalho do lote B (billing, créditos e cupons)

> Levantamento automático pelo comparador de paridade em 2026-11-10, após T24/T25/T23/T13.
> Fonte: `tests/contracts/creator_db_final.sql` contra `Base.metadata`.
> Detalhamento completo por tabela nas seções abaixo; issues filhas no board `SHC`.

## Fatias propostas

> **B1 e B2 concluídas** em 2026-11-10 (`0020_billing_account_alignment` e
> `0021_plan_alignment`); as demais fatias seguem o plano abaixo.

| Fatia | Tabelas | Risco principal |
| --- | --- | --- |
| B1 | `billing_accounts`, `billing_addresses`, `billing_payment_methods` | `document` vira bytea + hash; `street`→`line_1`; enums de cartão; APIs de billing account |
| B2 | `plans`, `plan_items`, `plan_payment_methods` | preços/intervalos, enum `plan_type`, remoção de colunas legadas |
| B3 | `subscriptions`, `subscription_history` | status/enums, histórico append-only (depende de T20) |
| B4 | `orders`, `invoices`, `charges`, `charge_transactions`, `refunds`, `provider_*`, `fiscal_invoices` | dinheiro em bigint, FKs RESTRICT, view `charges_with_last_transaction` |
| B5 | `credit_packages`, `coupons`, `coupon_redemptions`, `workspace_credit_*` | ledger imutável, lotes/consumos, índices únicos parciais |

Regras por fatia: model + revisão Alembic no mesmo PR, snapshot/orçamento regenerados,
`make check`/`make e2e`/`make security` verdes, OpenAPI atualizado antes de payload.

## `billing_accounts`

### column_missing (3)
- `billing_accounts.document_hash`
- `billing_accounts.external_code`
- `billing_accounts.external_id`

### column_extra (4)
- `billing_accounts.deleted_at`
- `billing_accounts.document_type`
- `billing_accounts.provider_customer_code`
- `billing_accounts.provider_customer_id`

### nullability (1)
- `billing_accounts.provider: final NOT NULL, model nullable`

### width (1)
- `billing_accounts.email: final varchar(254), model varchar(64)`

### kind (1)
- `billing_accounts.document: final bytes, model varchar`

### enum (2)
- `billing_accounts.payer_type: model has no vocabulary (expected ['INDIVIDUAL', 'COMPANY'])`
- `billing_accounts.provider: model has no vocabulary (expected ['PAGARME', 'STRIPE'])`

### index_missing (3)
- `billing_accounts: (document_hash)`
- `billing_accounts: (user_id)`
- `billing_accounts: UNIQUE (provider, external_id)`

### fk_extra (10)
- `billing_accounts['user_id']->users['id'] [CASCADE]`
- `billing_addresses['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `billing_payment_methods['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `charges['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `coupon_redemptions['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `invoices['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `orders['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `provider_disputes['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `refunds['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `subscriptions['billing_account_id']->billing_accounts['id'] [NO ACTION]`

### fk_ondelete (8)
- `billing_accounts['user_id']->users['id']: final RESTRICT vs model ['CASCADE']`
- `billing_addresses['billing_account_id']->billing_accounts['id']: final CASCADE vs model ['NO ACTION']`
- `billing_payment_methods['billing_account_id']->billing_accounts['id']: final CASCADE vs model ['NO ACTION']`
- `charges['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `invoices['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `orders['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `provider_disputes['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `subscriptions['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`

## `billing_addresses`

### column_missing (8)
- `billing_addresses.country`
- `billing_addresses.district`
- `billing_addresses.external_id`
- `billing_addresses.is_default`
- `billing_addresses.line_1`
- `billing_addresses.line_2`
- `billing_addresses.metadata`
- `billing_addresses.status`

### column_extra (4)
- `billing_addresses.complement`
- `billing_addresses.deleted_at`
- `billing_addresses.neighborhood`
- `billing_addresses.street`

### nullability (4)
- `billing_addresses.city: final NOT NULL, model nullable`
- `billing_addresses.number: final NOT NULL, model nullable`
- `billing_addresses.state: final NOT NULL, model nullable`
- `billing_addresses.zip_code: final NOT NULL, model nullable`

### width (3)
- `billing_addresses.number: final varchar(20), model varchar(16)`
- `billing_addresses.state: final varchar(2), model varchar(16)`
- `billing_addresses.zip_code: final varchar(8), model varchar(16)`

### unique_missing (1)
- `billing_addresses['external_id']`

### index_missing (2)
- `billing_addresses: (billing_account_id)`
- `billing_addresses: UNIQUE (billing_account_id) WHERE is_default and status = 'active'`

### index_name (1)
- `billing_addresses: missing index name uq_billing_addresses_default`

### fk_missing (1)
- `billing_payment_methods['billing_address_id']->billing_addresses['id'] [SET NULL]`

### fk_extra (1)
- `billing_addresses['billing_account_id']->billing_accounts['id'] [NO ACTION]`

### fk_ondelete (1)
- `billing_addresses['billing_account_id']->billing_accounts['id']: final CASCADE vs model ['NO ACTION']`

## `billing_payment_methods`

### column_missing (8)
- `billing_payment_methods.billing_address_id`
- `billing_payment_methods.brand`
- `billing_payment_methods.external_id`
- `billing_payment_methods.external_network_token_id`
- `billing_payment_methods.first_six_digits`
- `billing_payment_methods.metadata`
- `billing_payment_methods.status`
- `billing_payment_methods.type`

### column_extra (5)
- `billing_payment_methods.card_brand`
- `billing_payment_methods.card_status`
- `billing_payment_methods.card_type`
- `billing_payment_methods.deleted_at`
- `billing_payment_methods.provider_card_id`

### index_missing (4)
- `billing_payment_methods: (billing_account_id, is_default)`
- `billing_payment_methods: (billing_address_id) WHERE billing_address_id is not null`
- `billing_payment_methods: UNIQUE (billing_account_id) WHERE is_default and status = 'active'`
- `billing_payment_methods: UNIQUE (billing_account_id, external_id)`

### index_name (2)
- `billing_payment_methods: missing index name idx_m8_billing_payment_methods_billing_address_id`
- `billing_payment_methods: missing index name uq_billing_payment_methods_default`

### fk_missing (3)
- `billing_payment_methods['billing_address_id']->billing_addresses['id'] [SET NULL]`
- `charges['payment_method_id']->billing_payment_methods['id'] [SET NULL]`
- `subscriptions['payment_method_id']->billing_payment_methods['id'] [SET NULL]`

### fk_extra (1)
- `billing_payment_methods['billing_account_id']->billing_accounts['id'] [NO ACTION]`

### fk_ondelete (1)
- `billing_payment_methods['billing_account_id']->billing_accounts['id']: final CASCADE vs model ['NO ACTION']`

## `plans`

### column_missing (13)
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

### column_extra (3)
- `plans.code`
- `plans.description`
- `plans.is_active`

### enum (1)
- `plans.type: model has no vocabulary (expected ['FREE', 'STARTER', 'PRO', 'STUDIO', 'ENTERPRISE'])`

### unique_extra (1)
- `plans['code']`

### index_missing (1)
- `plans: UNIQUE (provider, external_id)`

### fk_missing (2)
- `subscription_history['new_plan_id']->plans['id'] [SET NULL]`
- `subscription_history['old_plan_id']->plans['id'] [SET NULL]`

### fk_extra (3)
- `subscription_history['plan_id']->plans['id'] [NO ACTION]`
- `subscription_history['previous_plan_id']->plans['id'] [NO ACTION]`
- `subscriptions['plan_id']->plans['id'] [NO ACTION]`

### fk_ondelete (1)
- `subscriptions['plan_id']->plans['id']: final RESTRICT vs model ['NO ACTION']`

## `plan_items`

### column_missing (3)
- `plan_items.currency`
- `plan_items.external_id`
- `plan_items.provider`

### column_extra (3)
- `plan_items.deleted_at`
- `plan_items.gateway_id`
- `plan_items.provider_plan_item_id`

### nullability (1)
- `plan_items.status: final NOT NULL, model nullable`

### width (1)
- `plan_items.price_cents: final bigint, model integer`

### enum (2)
- `plan_items.pricing_scheme_type: model has no vocabulary (expected ['FLAT', 'TIERED', 'VOLUME', 'STAIRSTEP'])`
- `plan_items.status: model has no vocabulary (expected ['ACTIVE', 'INACTIVE', 'ARCHIVED'])`

### index_missing (2)
- `plan_items: (plan_id)`
- `plan_items: UNIQUE (provider, external_id)`

### index_name (1)
- `plan_items: missing index name idx_m8_plan_items_plan_id`

## `plan_payment_methods`

### check_extra (1)
- `plan_payment_methods.payment_method_type`

## `subscriptions`

### column_missing (9)
- `subscriptions.billing_interval`
- `subscriptions.contracted_price_cents`
- `subscriptions.currency`
- `subscriptions.current_cycle_id`
- `subscriptions.external_code`
- `subscriptions.external_id`
- `subscriptions.payment_method_id`
- `subscriptions.provider`
- `subscriptions.status_reason`

### column_extra (7)
- `subscriptions.billing_day`
- `subscriptions.deleted_at`
- `subscriptions.interval`
- `subscriptions.provider_card_id`
- `subscriptions.provider_code`
- `subscriptions.provider_subscription_id`
- `subscriptions.start_at`

### nullability (1)
- `subscriptions.installments: final NOT NULL, model nullable`

### width (1)
- `subscriptions.minimum_price_cents: final bigint, model integer`

### enum (4)
- `subscriptions.billing_type: model has no vocabulary (expected ['PREPAID', 'POSTPAID'])`
- `subscriptions.payment_method: model has no vocabulary (expected ['CREDIT_CARD', 'DEBIT_CARD', 'BOLETO', 'PIX'])`
- `subscriptions.provider_status: model has no vocabulary (expected ['ACTIVE', 'CANCELED', 'FUTURE'])`
- `subscriptions.status: model has no vocabulary (expected ['ACTIVE', 'TRIALING', 'PAST_DUE', 'CANCELED', 'EXPIRED'])`

### index_missing (8)
- `subscriptions: (billing_account_id)`
- `subscriptions: (next_billing_at)`
- `subscriptions: (payment_method_id) WHERE payment_method_id is not null`
- `subscriptions: (plan_id)`
- `subscriptions: (workspace_id)`
- `subscriptions: UNIQUE (id, workspace_id)`
- `subscriptions: UNIQUE (provider, external_id)`
- `subscriptions: UNIQUE (workspace_id) WHERE status in ('active', 'trialing', 'past_due')`

### index_name (3)
- `subscriptions: missing index name idx_m8_subscriptions_payment_method_id`
- `subscriptions: missing index name idx_m8_subscriptions_plan_id`
- `subscriptions: missing index name uq_subscriptions_workspace_current`

### fk_missing (2)
- `coupon_redemptions['subscription_id', 'workspace_id']->subscriptions['id', 'workspace_id'] [RESTRICT]`
- `subscriptions['payment_method_id']->billing_payment_methods['id'] [SET NULL]`

### fk_extra (6)
- `coupon_redemptions['subscription_id']->subscriptions['id'] [NO ACTION]`
- `invoices['subscription_id']->subscriptions['id'] [NO ACTION]`
- `subscription_history['subscription_id']->subscriptions['id'] [NO ACTION]`
- `subscriptions['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `subscriptions['plan_id']->plans['id'] [NO ACTION]`
- `subscriptions['workspace_id']->workspaces['id'] [NO ACTION]`

### fk_ondelete (5)
- `invoices['subscription_id']->subscriptions['id']: final RESTRICT vs model ['NO ACTION']`
- `subscription_history['subscription_id']->subscriptions['id']: final CASCADE vs model ['NO ACTION']`
- `subscriptions['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `subscriptions['plan_id']->plans['id']: final RESTRICT vs model ['NO ACTION']`
- `subscriptions['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`

### default_missing (1)
- `subscriptions.installments: final default 1`

## `subscription_history`

### column_missing (9)
- `subscription_history.changed_by`
- `subscription_history.new_plan_id`
- `subscription_history.new_provider_status`
- `subscription_history.new_status`
- `subscription_history.old_plan_id`
- `subscription_history.old_provider_status`
- `subscription_history.old_status`
- `subscription_history.reason_code`
- `subscription_history.reason_text`

### column_extra (7)
- `subscription_history.deleted_at`
- `subscription_history.plan_id`
- `subscription_history.previous_plan_id`
- `subscription_history.previous_status`
- `subscription_history.reason`
- `subscription_history.status`
- `subscription_history.updated_at`

### enum (1)
- `subscription_history.change_type: model has no vocabulary (expected ['CREATE', 'UPGRADE', 'DOWNGRADE', 'CANCEL', 'RENEW'])`

### index_missing (4)
- `subscription_history: (changed_by) WHERE changed_by is not null`
- `subscription_history: (new_plan_id) WHERE new_plan_id is not null`
- `subscription_history: (old_plan_id) WHERE old_plan_id is not null`
- `subscription_history: (subscription_id, created_at)`

### index_name (3)
- `subscription_history: missing index name idx_m8_subscription_history_changed_by`
- `subscription_history: missing index name idx_m8_subscription_history_new_plan_id`
- `subscription_history: missing index name idx_m8_subscription_history_old_plan_id`

### fk_missing (3)
- `subscription_history['changed_by']->users['id'] [SET NULL]`
- `subscription_history['new_plan_id']->plans['id'] [SET NULL]`
- `subscription_history['old_plan_id']->plans['id'] [SET NULL]`

### fk_extra (3)
- `subscription_history['plan_id']->plans['id'] [NO ACTION]`
- `subscription_history['previous_plan_id']->plans['id'] [NO ACTION]`
- `subscription_history['subscription_id']->subscriptions['id'] [NO ACTION]`

### fk_ondelete (1)
- `subscription_history['subscription_id']->subscriptions['id']: final CASCADE vs model ['NO ACTION']`

## `orders`

### column_missing (3)
- `orders.code`
- `orders.external_id`
- `orders.provider`

### column_extra (3)
- `orders.closed`
- `orders.deleted_at`
- `orders.provider_order_id`

### width (3)
- `orders.amount_cents: final bigint, model integer`
- `orders.discount_cents: final bigint, model integer`
- `orders.subtotal_cents: final bigint, model integer`

### enum (1)
- `orders.status: model has no vocabulary (expected ['PENDING', 'PAID', 'CANCELED', 'FAILED'])`

### index_missing (6)
- `orders: (billing_account_id)`
- `orders: (credit_package_id) WHERE credit_package_id is not null`
- `orders: (status)`
- `orders: (workspace_id)`
- `orders: UNIQUE (id, workspace_id)`
- `orders: UNIQUE (provider, external_id)`

### index_name (1)
- `orders: missing index name idx_m8_orders_credit_package_id`

### fk_missing (3)
- `charges['order_id']->orders['id'] [SET NULL]`
- `coupon_redemptions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`
- `workspace_credit_transactions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`

### fk_extra (4)
- `coupon_redemptions['order_id']->orders['id'] [NO ACTION]`
- `orders['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `orders['credit_package_id']->credit_packages['id'] [NO ACTION]`
- `orders['workspace_id']->workspaces['id'] [NO ACTION]`

### fk_ondelete (3)
- `orders['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `orders['credit_package_id']->credit_packages['id']: final SET NULL vs model ['NO ACTION']`
- `orders['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`

### default_missing (1)
- `orders.currency: final default 'BRL'`

## `invoices`

### column_missing (2)
- `invoices.external_id`
- `invoices.provider`

### column_extra (3)
- `invoices.deleted_at`
- `invoices.provider_charge_id`
- `invoices.provider_invoice_id`

### nullability (1)
- `invoices.subscription_id: final NOT NULL, model nullable`

### width (4)
- `invoices.amount_cents: final bigint, model integer`
- `invoices.total_discount_cents: final bigint, model integer`
- `invoices.total_increment_cents: final bigint, model integer`
- `invoices.url: final unbounded varchar, model varchar(2048)`

### enum (2)
- `invoices.payment_method: model has no vocabulary (expected ['CREDIT_CARD', 'DEBIT_CARD', 'BOLETO', 'PIX'])`
- `invoices.status: model has no vocabulary (expected ['PENDING', 'PAID', 'CANCELED', 'SCHEDULED', 'FAILED'])`

### index_missing (4)
- `invoices: (billing_account_id)`
- `invoices: (status, due_at)`
- `invoices: (subscription_id, due_at)`
- `invoices: UNIQUE (provider, external_id)`

### fk_missing (2)
- `coupon_redemptions['invoice_id']->invoices['id'] [SET NULL]`
- `workspace_credit_transactions['invoice_id']->invoices['id'] [RESTRICT]`

### fk_extra (4)
- `charges['invoice_id']->invoices['id'] [NO ACTION]`
- `invoices['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `invoices['subscription_id']->subscriptions['id'] [NO ACTION]`
- `refunds['invoice_id']->invoices['id'] [NO ACTION]`

### fk_ondelete (3)
- `charges['invoice_id']->invoices['id']: final SET NULL vs model ['NO ACTION']`
- `invoices['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `invoices['subscription_id']->subscriptions['id']: final RESTRICT vs model ['NO ACTION']`

### default_missing (1)
- `invoices.currency: final default 'BRL'`

## `charges`

### column_missing (15)
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

### column_extra (3)
- `charges.deleted_at`
- `charges.provider_card_id`
- `charges.provider_charge_id`

### width (2)
- `charges.amount_cents: final bigint, model integer`
- `charges.status: final unbounded varchar, model varchar(20)`

### index_missing (8)
- `charges: (billing_account_id, status)`
- `charges: (code)`
- `charges: (invoice_id)`
- `charges: (order_id)`
- `charges: (paid_at)`
- `charges: (payment_method_id) WHERE payment_method_id is not null`
- `charges: (status)`
- `charges: UNIQUE (provider, external_id)`

### index_name (1)
- `charges: missing index name idx_m8_charges_payment_method_id`

### fk_missing (3)
- `charges['order_id']->orders['id'] [SET NULL]`
- `charges['payment_method_id']->billing_payment_methods['id'] [SET NULL]`
- `refunds['charge_id']->charges['id'] [RESTRICT]`

### fk_extra (3)
- `charges['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `charges['invoice_id']->invoices['id'] [NO ACTION]`
- `provider_disputes['charge_id']->charges['id'] [NO ACTION]`

### fk_ondelete (3)
- `charges['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `charges['invoice_id']->invoices['id']: final SET NULL vs model ['NO ACTION']`
- `provider_disputes['charge_id']->charges['id']: final RESTRICT vs model ['NO ACTION']`

### default_missing (1)
- `charges.currency: final default 'BRL'`

## `charge_transactions`

Sem divergências de schema.

## `refunds`

### column_missing (7)
- `refunds.charge_id`
- `refunds.external_id`
- `refunds.metadata`
- `refunds.processed_at`
- `refunds.provider`
- `refunds.reason_code`
- `refunds.requested_by`

### column_extra (6)
- `refunds.billing_account_id`
- `refunds.deleted_at`
- `refunds.invoice_id`
- `refunds.provider_charge_id`
- `refunds.provider_refund_id`
- `refunds.reason`

### width (1)
- `refunds.amount_cents: final bigint, model integer`

### enum (1)
- `refunds.status: model has no vocabulary (expected ['PENDING', 'SUCCEEDED', 'FAILED'])`

### index_missing (4)
- `refunds: (charge_id)`
- `refunds: (requested_by) WHERE requested_by is not null`
- `refunds: (status)`
- `refunds: UNIQUE (provider, external_id)`

### index_name (1)
- `refunds: missing index name idx_m8_refunds_requested_by`

### fk_missing (2)
- `refunds['charge_id']->charges['id'] [RESTRICT]`
- `refunds['requested_by']->users['id'] [SET NULL]`

### fk_extra (2)
- `refunds['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `refunds['invoice_id']->invoices['id'] [NO ACTION]`

### default_missing (1)
- `refunds.currency: final default 'BRL'`

## `provider_disputes`

### column_missing (6)
- `provider_disputes.amount_cents`
- `provider_disputes.currency`
- `provider_disputes.external_id`
- `provider_disputes.provider`
- `provider_disputes.resolved_at`
- `provider_disputes.result`

### column_extra (3)
- `provider_disputes.code`
- `provider_disputes.deleted_at`
- `provider_disputes.provider_dispute_id`

### enum (1)
- `provider_disputes.status: model has no vocabulary (expected ['OPEN', 'UNDER_REVIEW', 'RESOLVED'])`

### index_missing (4)
- `provider_disputes: (billing_account_id) WHERE billing_account_id is not null`
- `provider_disputes: (charge_id)`
- `provider_disputes: (status, resolved_at)`
- `provider_disputes: UNIQUE (provider, external_id)`

### index_name (1)
- `provider_disputes: missing index name idx_m8_provider_disputes_billing_account_id`

### fk_extra (2)
- `provider_disputes['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `provider_disputes['charge_id']->charges['id'] [NO ACTION]`

### fk_ondelete (2)
- `provider_disputes['billing_account_id']->billing_accounts['id']: final RESTRICT vs model ['NO ACTION']`
- `provider_disputes['charge_id']->charges['id']: final RESTRICT vs model ['NO ACTION']`

## `provider_webhook_events`

### column_missing (1)
- `provider_webhook_events.external_id`

### column_extra (3)
- `provider_webhook_events.created_at`
- `provider_webhook_events.deleted_at`
- `provider_webhook_events.provider_event_id`

### enum (2)
- `provider_webhook_events.provider: model has no vocabulary (expected ['PAGARME', 'STRIPE'])`
- `provider_webhook_events.status: model has no vocabulary (expected ['RECEIVED', 'PROCESSING', 'PROCESSED', 'FAILED', 'IGNORED'])`

### unique_missing (1)
- `provider_webhook_events['dedupe_key']`

### index_missing (4)
- `provider_webhook_events: (event_type)`
- `provider_webhook_events: (resource_id)`
- `provider_webhook_events: (status, received_at)`
- `provider_webhook_events: UNIQUE (provider, external_id)`

## `provider_idempotency_keys`

### column_missing (1)
- `provider_idempotency_keys.expires_at`

### column_extra (1)
- `provider_idempotency_keys.deleted_at`

### enum (2)
- `provider_idempotency_keys.provider: model has no vocabulary (expected ['PAGARME', 'STRIPE'])`
- `provider_idempotency_keys.status: model has no vocabulary (expected ['STARTED', 'COMPLETED', 'FAILED'])`

### index_missing (2)
- `provider_idempotency_keys: (expires_at)`
- `provider_idempotency_keys: UNIQUE (provider, idempotency_key)`

## `fiscal_invoices`

### check_extra (1)
- `fiscal_invoices.fiscal_invoice_status`

## `credit_packages`

### column_missing (2)
- `credit_packages.credits`
- `credit_packages.credits_validity_days`

### column_extra (3)
- `credit_packages.code`
- `credit_packages.credits_amount`
- `credit_packages.deleted_at`

### width (2)
- `credit_packages.name: final unbounded varchar, model varchar(64)`
- `credit_packages.price_cents: final bigint, model integer`

### unique_extra (1)
- `credit_packages['code']`

### fk_extra (1)
- `orders['credit_package_id']->credit_packages['id'] [NO ACTION]`

### fk_ondelete (1)
- `orders['credit_package_id']->credit_packages['id']: final SET NULL vs model ['NO ACTION']`

### default_missing (1)
- `credit_packages.currency: final default 'BRL'`

## `coupons`

### column_missing (3)
- `coupons.credits`
- `coupons.credits_validity_days`
- `coupons.currency`

### column_extra (2)
- `coupons.credits_amount`
- `coupons.redemptions_count`

### width (1)
- `coupons.min_purchase_cents: final bigint, model integer`

### enum (2)
- `coupons.applies_to: model has no vocabulary (expected ['SUBSCRIPTION_AND_CREDITS', 'SUBSCRIPTION_ONLY', 'CREDITS_ONLY'])`
- `coupons.type: model has no vocabulary (expected ['DISCOUNT', 'CREDIT'])`

### unique_extra (1)
- `coupons['code']`

### index_missing (4)
- `coupons: (created_by) WHERE created_by is not null`
- `coupons: (is_active)`
- `coupons: (type)`
- `coupons: UNIQUE (code) WHERE deleted_at is null`

### index_name (2)
- `coupons: missing index name idx_m8_coupons_created_by`
- `coupons: missing index name uq_coupons_code_active`

### fk_extra (2)
- `coupon_redemptions['coupon_id']->coupons['id'] [NO ACTION]`
- `coupons['created_by']->users['id'] [NO ACTION]`

### fk_ondelete (2)
- `coupon_redemptions['coupon_id']->coupons['id']: final RESTRICT vs model ['NO ACTION']`
- `coupons['created_by']->users['id']: final SET NULL vs model ['NO ACTION']`

## `coupon_redemptions`

### column_missing (10)
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

### column_extra (3)
- `coupon_redemptions.billing_account_id`
- `coupon_redemptions.deleted_at`
- `coupon_redemptions.provider_discount_id`

### width (1)
- `coupon_redemptions.discount_amount_cents: final bigint, model integer`

### enum (1)
- `coupon_redemptions.status: model has no vocabulary (expected ['APPLIED', 'CANCELED'])`

### index_missing (9)
- `coupon_redemptions: (coupon_id, workspace_id)`
- `coupon_redemptions: (credit_transaction_id) WHERE credit_transaction_id is not null`
- `coupon_redemptions: (invoice_id) WHERE invoice_id is not null`
- `coupon_redemptions: (order_id, workspace_id)`
- `coupon_redemptions: (subscription_id, workspace_id)`
- `coupon_redemptions: (user_id)`
- `coupon_redemptions: (workspace_id)`
- `coupon_redemptions: UNIQUE (coupon_id, workspace_id) WHERE once_per_workspace and status = 'applied'`
- `coupon_redemptions: UNIQUE (provider, external_id)`

### index_name (3)
- `coupon_redemptions: missing index name idx_m8_coupon_redemptions_credit_transaction_id`
- `coupon_redemptions: missing index name idx_m8_coupon_redemptions_invoice_id`
- `coupon_redemptions: missing index name uq_coupon_redemptions_once_per_workspace`

### fk_missing (5)
- `coupon_redemptions['credit_transaction_id']->workspace_credit_transactions['id'] [SET NULL]`
- `coupon_redemptions['invoice_id']->invoices['id'] [SET NULL]`
- `coupon_redemptions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`
- `coupon_redemptions['subscription_id', 'workspace_id']->subscriptions['id', 'workspace_id'] [RESTRICT]`
- `coupon_redemptions['user_id']->users['id'] [RESTRICT]`

### fk_extra (4)
- `coupon_redemptions['billing_account_id']->billing_accounts['id'] [NO ACTION]`
- `coupon_redemptions['coupon_id']->coupons['id'] [NO ACTION]`
- `coupon_redemptions['order_id']->orders['id'] [NO ACTION]`
- `coupon_redemptions['subscription_id']->subscriptions['id'] [NO ACTION]`

### fk_ondelete (1)
- `coupon_redemptions['coupon_id']->coupons['id']: final RESTRICT vs model ['NO ACTION']`

## `workspace_credit_transactions`

### column_missing (7)
- `workspace_credit_transactions.balance_after`
- `workspace_credit_transactions.created_by`
- `workspace_credit_transactions.generated_image_id`
- `workspace_credit_transactions.image_resize_id`
- `workspace_credit_transactions.invoice_id`
- `workspace_credit_transactions.order_id`
- `workspace_credit_transactions.type`

### column_extra (5)
- `workspace_credit_transactions.deleted_at`
- `workspace_credit_transactions.reference_id`
- `workspace_credit_transactions.reference_type`
- `workspace_credit_transactions.transaction_type`
- `workspace_credit_transactions.updated_at`

### index_missing (6)
- `workspace_credit_transactions: (created_by) WHERE created_by is not null`
- `workspace_credit_transactions: (workspace_id, created_at)`
- `workspace_credit_transactions: UNIQUE (generated_image_id, type)`
- `workspace_credit_transactions: UNIQUE (image_resize_id, type)`
- `workspace_credit_transactions: UNIQUE (invoice_id, type)`
- `workspace_credit_transactions: UNIQUE (order_id, type)`

### index_name (2)
- `workspace_credit_transactions: missing index name idx_m8_workspace_credit_transactions_created_by`
- `workspace_credit_transactions: missing index name uq_credit_tx_image_resize`

### fk_missing (6)
- `coupon_redemptions['credit_transaction_id']->workspace_credit_transactions['id'] [SET NULL]`
- `workspace_credit_transactions['created_by']->users['id'] [SET NULL]`
- `workspace_credit_transactions['generated_image_id']->generated_images['id'] [RESTRICT]`
- `workspace_credit_transactions['image_resize_id']->image_resizes['id'] [RESTRICT]`
- `workspace_credit_transactions['invoice_id']->invoices['id'] [RESTRICT]`
- `workspace_credit_transactions['order_id', 'workspace_id']->orders['id', 'workspace_id'] [RESTRICT]`

### fk_extra (1)
- `workspace_credit_transactions['workspace_id']->workspaces['id'] [NO ACTION]`

### fk_ondelete (1)
- `workspace_credit_transactions['workspace_id']->workspaces['id']: final RESTRICT vs model ['NO ACTION']`

## `workspace_credit_lots`

Sem divergências de schema.

## `workspace_credit_lot_consumptions`

Sem divergências de schema.

