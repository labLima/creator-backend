CREATE EXTENSION IF NOT EXISTS pgcrypto; -- M7: gen_random_uuid()

CREATE TYPE "persona_gender" AS ENUM (
  'MALE',
  'FEMALE',
  'NON_BINARY',
  'OTHER',
  'PREFER_NOT_TO_SAY'
);

CREATE TYPE "age_range" AS ENUM (
  'UP_TO_17',
  'FROM_18_TO_24',
  'FROM_25_TO_34',
  'FROM_35_TO_44',
  'FROM_45_TO_54',
  'FROM_55_TO_64',
  'FROM_65_PLUS'
);

CREATE TYPE "device_platform" AS ENUM (
  'IOS',
  'ANDROID',
  'WEB'
);

CREATE TYPE "card_brand" AS ENUM (
  'VISA',
  'MASTERCARD',
  'AMEX',
  'ELO',
  'HIPERCARD',
  'DINERS',
  'DISCOVER',
  'JCB',
  'AURA',
  'CABAL',
  'OTHER'
);

CREATE TYPE "brand_asset_type" AS ENUM (
  'LOGO',
  'IMAGE',
  'FONT',
  'ICON',
  'DOCUMENT',
  'OTHER'
);

CREATE TYPE "refund_reason" AS ENUM (
  'CUSTOMER_REQUEST',
  'CHARGEBACK',
  'FRAUD_SUSPECT',
  'DUPLICATE',
  'SERVICE_FAILURE',
  'OTHER'
);

CREATE TYPE "address_status" AS ENUM (
  'ACTIVE',
  'INACTIVE',
  'DELETED'
);

CREATE TYPE "catalog_status" AS ENUM (
  'ACTIVE',
  'INACTIVE',
  'ARCHIVED'
);

CREATE TYPE "idempotency_status" AS ENUM (
  'STARTED',
  'COMPLETED',
  'FAILED'
);

CREATE TYPE "dispute_status" AS ENUM (
  'OPEN',
  'UNDER_REVIEW',
  'RESOLVED'
);

CREATE TYPE "dispute_result" AS ENUM (
  'WON',
  'LOST',
  'CANCELED'
);

CREATE TYPE "payment_provider" AS ENUM (
  'PAGARME',
  'STRIPE'
);

CREATE TYPE "billing_type" AS ENUM (
  'PREPAID',
  'POSTPAID'
);

CREATE TYPE "billing_interval" AS ENUM (
  'DAY',
  'WEEK',
  'MONTH',
  'YEAR'
);

CREATE TYPE "subscription_status_reason" AS ENUM (
  'PAYMENT_FAILED',
  'CARD_EXPIRED',
  'CUSTOMER_REQUEST',
  'PLAN_CHANGED',
  'FRAUD_SUSPECT',
  'DUNNING_EXHAUSTED',
  'TRIAL_ENDED'
);

CREATE TYPE "funding_source" AS ENUM (
  'CREDIT',
  'DEBIT'
);

CREATE TYPE "pricing_scheme_type" AS ENUM (
  'FLAT',
  'TIERED',
  'VOLUME',
  'STAIRSTEP'
);

CREATE TYPE "member_status" AS ENUM (
  'ACTIVE',
  'SUSPENDED',
  'REMOVED'
);

CREATE TYPE "notification_resource_type" AS ENUM (
  'WORKSPACE_INVITE',
  'WORKSPACE_MEMBER',
  'POST',
  'GENERATED_IMAGE',
  'SUBSCRIPTION',
  'ORDER',
  'INVOICE',
  'CHARGE',
  'COUPON'
);

CREATE TYPE "fiscal_invoice_status" AS ENUM (
  'PENDING',
  'PROCESSING',
  'ISSUED',
  'CANCELED',
  'FAILED'
);

CREATE TYPE "consent_type" AS ENUM (
  'TERMS_OF_USE',
  'PRIVACY_POLICY',
  'MARKETING_COMMUNICATIONS'
);

CREATE TYPE "workspace_role" AS ENUM (
  'OWNER',
  'MANAGER',
  'EDITOR',
  'VIEWER'
);

CREATE TYPE "invite_type" AS ENUM (
  'EMAIL',
  'LINK'
);

CREATE TYPE "invite_status" AS ENUM (
  'PENDING',
  'ACCEPTED',
  'REVOKED',
  'EXPIRED'
);

CREATE TYPE "notification_type" AS ENUM (
  'CONTENT_GENERATION',
  'CONTENT_APPROVAL',
  'INVITE',
  'BILLING',
  'CREDITS',
  'COUPON',
  'SYSTEM'
);

CREATE TYPE "notification_channel" AS ENUM (
  'EMAIL',
  'IN_APP',
  'PUSH'
);

CREATE TYPE "notification_delivery_status" AS ENUM (
  'PENDING',
  'SENT',
  'FAILED'
);

CREATE TYPE "subscription_status" AS ENUM (
  'ACTIVE',
  'TRIALING',
  'PAST_DUE',
  'CANCELED',
  'EXPIRED'
);

CREATE TYPE "provider_subscription_status" AS ENUM (
  'ACTIVE',
  'CANCELED',
  'FUTURE'
);

CREATE TYPE "subscription_change_type" AS ENUM (
  'CREATE',
  'UPGRADE',
  'DOWNGRADE',
  'CANCEL',
  'RENEW'
);

CREATE TYPE "invoice_status" AS ENUM (
  'PENDING',
  'PAID',
  'CANCELED',
  'SCHEDULED',
  'FAILED'
);

CREATE TYPE "charge_status" AS ENUM (
  'PENDING',
  'PAID',
  'CANCELED',
  'PROCESSING',
  'FAILED',
  'OVERPAID',
  'UNDERPAID',
  'CHARGEDBACK'
);

CREATE TYPE "transaction_status" AS ENUM (
  'AUTHORIZED_PENDING_CAPTURE',
  'NOT_AUTHORIZED',
  'CAPTURED',
  'PARTIAL_CAPTURE',
  'WAITING_CAPTURE',
  'REFUNDED',
  'VOIDED',
  'PARTIAL_REFUNDED',
  'PARTIAL_VOID',
  'ERROR_ON_VOIDING',
  'ERROR_ON_REFUNDING',
  'WAITING_CANCELLATION',
  'WITH_ERROR',
  'FAILED',
  'WAITING_PAYMENT',
  'PENDING_REFUND',
  'GENERATED',
  'VIEWED',
  'PAID',
  'CHARGEDBACK'
);

CREATE TYPE "payment_method_type" AS ENUM (
  'CREDIT_CARD',
  'DEBIT_CARD',
  'BOLETO',
  'PIX'
);

CREATE TYPE "order_status" AS ENUM (
  'PENDING',
  'PAID',
  'CANCELED',
  'FAILED'
);

CREATE TYPE "card_status" AS ENUM (
  'ACTIVE',
  'DELETED',
  'EXPIRED'
);

CREATE TYPE "billing_account_type" AS ENUM (
  'INDIVIDUAL',
  'COMPANY'
);

CREATE TYPE "refund_status" AS ENUM (
  'PENDING',
  'SUCCEEDED',
  'FAILED'
);

CREATE TYPE "webhook_processing_status" AS ENUM (
  'RECEIVED',
  'PROCESSING',
  'PROCESSED',
  'FAILED',
  'IGNORED'
);

CREATE TYPE "coupon_type" AS ENUM (
  'DISCOUNT',
  'CREDIT'
);

CREATE TYPE "coupon_applies_to" AS ENUM (
  'SUBSCRIPTION_AND_CREDITS',
  'SUBSCRIPTION_ONLY',
  'CREDITS_ONLY'
);

CREATE TYPE "coupon_redemption_status" AS ENUM (
  'APPLIED',
  'CANCELED'
);

CREATE TYPE "plan_type" AS ENUM (
  'FREE',
  'STARTER',
  'PRO',
  'STUDIO',
  'ENTERPRISE'
);

CREATE TYPE "credit_transaction_type" AS ENUM (
  'SUBSCRIPTION_CREDIT',
  'TOP_UP',
  'COUPON_CREDIT',
  'GENERATION',
  'EXPIRATION',
  'REFUND',
  'ADJUSTMENT'
);

CREATE TYPE "image_feedback_type" AS ENUM (
  'POSITIVE',
  'NEGATIVE',
  'NOT_USED'
);

CREATE TYPE "campaign_voice" AS ENUM (
  'INSPIRATIONAL',
  'MOTIVATIONAL',
  'PROFESSIONAL',
  'CASUAL',
  'ELEGANT',
  'MODERN',
  'TRADITIONAL',
  'FUN',
  'SERIOUS'
);

-- M2: aprovação independente do ciclo de publicação e da geração de imagens.
CREATE TYPE "approval_status" AS ENUM (
  'PENDING',
  'APPROVED',
  'REJECTED'
);

CREATE TYPE "publication_status" AS ENUM (
  'DRAFT',
  'SCHEDULED',
  'PUBLISHED'
);

CREATE TYPE "content_format" AS ENUM (
  'IMAGE',
  'CAROUSEL',
  'STORIES'
);

CREATE TYPE "art_ratio" AS ENUM (
  'RATIO_4_5',
  'RATIO_1_1',
  'RATIO_9_16',
  'RATIO_16_9'
);

CREATE TYPE "generation_status" AS ENUM (
  'GENERATING',
  'SUCCEEDED',
  'FAILED'
);

CREATE TABLE "users" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "auth_provider_id" varchar,
  "email" varchar(254),
  "display_name" varchar(50) NOT NULL,
  "bio" varchar(350),
  "avatar_url" varchar,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz
);

CREATE TABLE "workspaces" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "name" varchar(50) NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz
);

CREATE TABLE "workspace_members" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "workspace_id" uuid NOT NULL,
  "role" workspace_role NOT NULL,
  "status" member_status NOT NULL DEFAULT 'ACTIVE',
  "invited_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "workspace_invites" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "workspace_id" uuid NOT NULL,
  "type" invite_type NOT NULL,
  "role" workspace_role NOT NULL,
  "email" varchar(254),
  "token_hash" varchar(64) UNIQUE NOT NULL,
  "max_uses" int,
  "status" invite_status NOT NULL DEFAULT 'PENDING',
  "created_by" uuid NOT NULL,
  "expires_at" timestamptz,
  "last_used_at" timestamptz,
  "revoked_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_workspace_invites_email_by_type" CHECK ((type = 'EMAIL') = (email IS NOT NULL)),
  CONSTRAINT "chk_workspace_invites_max_uses_by_type" CHECK ((type = 'LINK') = (max_uses IS NOT NULL)),
  CONSTRAINT "chk_workspace_invites_max_uses_positive" CHECK (max_uses IS NULL OR max_uses >= 1)
);

CREATE TABLE "workspace_invite_usages" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "invite_id" uuid NOT NULL,
  "member_id" uuid NOT NULL,
  "used_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "notifications" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "workspace_id" uuid NOT NULL,
  "type" notification_type NOT NULL,
  "title" varchar(150) NOT NULL,
  "body" varchar(2000),
  "payload" jsonb,
  "resource_type" notification_resource_type,
  "resource_id" uuid,
  "dedupe_key" varchar(128),
  "created_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_notifications_resource_pair" CHECK ((resource_type IS NULL) = (resource_id IS NULL))
);

CREATE TABLE "notification_recipients" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "notification_id" uuid NOT NULL,
  "user_id" uuid NOT NULL,
  "channel" notification_channel NOT NULL,
  "status" notification_delivery_status NOT NULL DEFAULT 'PENDING',
  "external_message_id" varchar(128),
  "error_message" text,
  "attempts" int NOT NULL DEFAULT 0,
  "sent_at" timestamptz,
  "read_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "user_devices" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "platform" device_platform NOT NULL,
  "fcm_token" varchar(255) UNIQUE NOT NULL,
  "is_active" boolean NOT NULL DEFAULT true,
  "last_seen_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "notification_preferences" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "type" notification_type NOT NULL,
  "channel" notification_channel NOT NULL,
  "is_enabled" boolean NOT NULL DEFAULT true,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "billing_accounts" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "payer_type" billing_account_type NOT NULL,
  "name" varchar(64) NOT NULL,
  "email" varchar(254) NOT NULL,
  "phone" varchar(20),
  "document" bytea,
  "document_hash" varchar(64),
  "company_name" varchar(64),
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "external_code" varchar(52),
  "delinquent" boolean NOT NULL DEFAULT false,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_billing_accounts_company_name" CHECK ((payer_type = 'COMPANY') = (company_name IS NOT NULL)),
  CONSTRAINT "chk_billing_accounts_document_pair" CHECK ((document IS NULL) = (document_hash IS NULL))
);

CREATE TABLE "billing_addresses" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid NOT NULL,
  "external_id" varchar(64) UNIQUE,
  "line_1" varchar(256) NOT NULL,
  "number" varchar(20) NOT NULL,
  "line_2" varchar(128),
  "district" varchar(64),
  "zip_code" varchar(8) NOT NULL,
  "city" varchar(64) NOT NULL,
  "state" varchar(2) NOT NULL,
  "country" varchar(2) NOT NULL,
  "status" address_status NOT NULL DEFAULT 'ACTIVE',
  "is_default" boolean NOT NULL DEFAULT false,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_billing_addresses_zip_code" CHECK (country <> 'BR' OR zip_code ~ '^[0-9]{8}$'),
  CONSTRAINT "chk_billing_addresses_state_uf" CHECK (country <> 'BR' OR state ~ '^[A-Z]{2}$')
);

CREATE TABLE "billing_payment_methods" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid NOT NULL,
  "billing_address_id" uuid,
  "external_id" varchar(64),
  "external_network_token_id" varchar(64),
  "first_six_digits" varchar(6),
  "brand" card_brand,
  "card_last_four" varchar(4),
  "holder_name" varchar(64),
  "holder_document" varchar(16),
  "exp_month" int,
  "exp_year" int,
  "type" funding_source,
  "status" card_status NOT NULL DEFAULT 'ACTIVE',
  "is_default" boolean NOT NULL DEFAULT false,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_billing_payment_methods_exp_month" CHECK (exp_month IS NULL OR exp_month BETWEEN 1 AND 12),
  CONSTRAINT "chk_billing_payment_methods_exp_year" CHECK (exp_year IS NULL OR exp_year BETWEEN 2000 AND 2100)
);

CREATE TABLE "plans" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "name" varchar(64) NOT NULL,
  "type" plan_type NOT NULL,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "price_cents" bigint NOT NULL,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "credits_per_month" int NOT NULL,
  "credits_validity_days" int NOT NULL DEFAULT 30,
  "billing_interval" billing_interval NOT NULL DEFAULT 'MONTH',
  "interval_count" int NOT NULL DEFAULT 1,
  "billing_type" billing_type NOT NULL DEFAULT 'PREPAID',
  "minimum_price_cents" bigint,
  "trial_period_days" int,
  "statement_descriptor" varchar(22),
  "status" catalog_status NOT NULL DEFAULT 'ACTIVE',
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz,
  CONSTRAINT "chk_plans_cents_nonnegative" CHECK (price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0)),
  CONSTRAINT "chk_plans_currency_format" CHECK (currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "plan_items" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "plan_id" uuid NOT NULL,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "name" varchar(64),
  "description" varchar,
  "quantity" int NOT NULL DEFAULT 1,
  "cycles" int,
  "pricing_scheme_type" pricing_scheme_type,
  "price_cents" bigint,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "price_brackets" jsonb,
  "status" catalog_status NOT NULL DEFAULT 'ACTIVE',
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_plan_items_price_nonnegative" CHECK (price_cents IS NULL OR price_cents >= 0),
  CONSTRAINT "chk_plan_items_currency_format" CHECK (currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "plan_payment_methods" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "plan_id" uuid NOT NULL,
  "method" payment_method_type NOT NULL,
  "max_installments" int NOT NULL CHECK (max_installments >= 1) DEFAULT 1,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "subscriptions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid NOT NULL,
  "workspace_id" uuid NOT NULL,
  "plan_id" uuid NOT NULL,
  "contracted_price_cents" bigint NOT NULL,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "status" subscription_status NOT NULL,
  "provider_status" provider_subscription_status,
  "status_reason" subscription_status_reason,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "external_code" varchar(52),
  "payment_method" payment_method_type,
  "payment_method_id" uuid,
  "billing_type" billing_type,
  "billing_interval" billing_interval,
  "interval_count" int,
  "installments" int NOT NULL DEFAULT 1,
  "minimum_price_cents" bigint,
  "statement_descriptor" varchar(22),
  "trial_period_days" int,
  "current_cycle_id" varchar(64),
  "current_period_start" timestamptz,
  "current_period_end" timestamptz,
  "next_billing_at" timestamptz,
  "canceled_at" timestamptz,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_subscriptions_installments" CHECK (installments IS NULL OR installments >= 1),
  CONSTRAINT "chk_subscriptions_cents_nonnegative" CHECK (contracted_price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0)),
  CONSTRAINT "chk_subscriptions_currency_format" CHECK (currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "subscription_history" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "subscription_id" uuid NOT NULL,
  "change_type" subscription_change_type NOT NULL,
  "old_plan_id" uuid,
  "new_plan_id" uuid,
  "old_status" subscription_status,
  "new_status" subscription_status,
  "old_provider_status" provider_subscription_status,
  "new_provider_status" provider_subscription_status,
  "changed_by" uuid,
  "reason_code" subscription_status_reason,
  "reason_text" varchar(500),
  "created_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "orders" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid NOT NULL,
  "workspace_id" uuid NOT NULL,
  "credit_package_id" uuid,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "code" varchar(52),
  "subtotal_cents" bigint NOT NULL,
  "discount_cents" bigint NOT NULL DEFAULT 0,
  "amount_cents" bigint NOT NULL,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "status" order_status NOT NULL,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_orders_amount_consistency" CHECK (amount_cents = subtotal_cents - discount_cents),
  CONSTRAINT "chk_orders_cents_nonnegative" CHECK (subtotal_cents >= 0 AND amount_cents >= 0 AND (discount_cents IS NULL OR discount_cents >= 0)),
  CONSTRAINT "chk_orders_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "invoices" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid NOT NULL,
  "subscription_id" uuid NOT NULL,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "url" varchar,
  "amount_cents" bigint NOT NULL,
  "total_discount_cents" bigint,
  "total_increment_cents" bigint,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "status" invoice_status NOT NULL,
  "payment_method" payment_method_type,
  "installments" int,
  "billing_at" timestamptz,
  "seen_at" timestamptz,
  "due_at" timestamptz,
  "period_start" timestamptz,
  "period_end" timestamptz,
  "canceled_at" timestamptz,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_invoices_cents_nonnegative" CHECK (amount_cents >= 0 AND (total_discount_cents IS NULL OR total_discount_cents >= 0) AND (total_increment_cents IS NULL OR total_increment_cents >= 0)),
  CONSTRAINT "chk_invoices_installments" CHECK (installments IS NULL OR installments >= 1),
  CONSTRAINT "chk_invoices_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "charges" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid NOT NULL,
  "invoice_id" uuid,
  "order_id" uuid,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "payment_method" payment_method_type NOT NULL,
  "payment_method_id" uuid,
  "code" varchar(52),
  "amount_cents" bigint NOT NULL,
  "paid_amount_cents" bigint,
  "canceled_amount_cents" bigint,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "installments" int NOT NULL DEFAULT 1,
  "funding_source" funding_source,
  "status" charge_status NOT NULL,
  "gateway_id" varchar(128),
  "metadata" jsonb,
  "provider_payload" jsonb,
  "due_at" timestamptz,
  "paid_at" timestamptz,
  "canceled_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_charges_cents_nonnegative" CHECK (amount_cents >= 0 AND (paid_amount_cents IS NULL OR paid_amount_cents >= 0) AND (canceled_amount_cents IS NULL OR canceled_amount_cents >= 0)),
  CONSTRAINT "chk_charges_installments" CHECK (installments IS NULL OR installments >= 1),
  CONSTRAINT "chk_charges_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "charge_transactions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "charge_id" uuid NOT NULL,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "status" transaction_status NOT NULL,
  "amount_cents" bigint NOT NULL,
  "gateway_response" jsonb,
  "antifraud_response" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_charge_transactions_amount_nonnegative" CHECK (amount_cents >= 0)
);

CREATE TABLE "refunds" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "charge_id" uuid NOT NULL,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "amount_cents" bigint NOT NULL,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "reason_code" refund_reason,
  "status" refund_status NOT NULL,
  "requested_by" uuid,
  "processed_at" timestamptz,
  "metadata" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_refunds_amount_nonnegative" CHECK (amount_cents >= 0),
  CONSTRAINT "chk_refunds_currency_format" CHECK (currency ~ '^[A-Z]{3}$'),
  CONSTRAINT "chk_refunds_processed_by_status" CHECK ((status = 'PENDING') = (processed_at IS NULL))
);

CREATE TABLE "provider_disputes" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid,
  "charge_id" uuid,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "status" dispute_status NOT NULL DEFAULT 'OPEN',
  "result" dispute_result,
  "amount_cents" bigint,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "reason" varchar,
  "opened_at" timestamptz,
  "deadline_at" timestamptz,
  "resolved_at" timestamptz,
  "payload" jsonb,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_provider_disputes_amount_nonnegative" CHECK (amount_cents IS NULL OR amount_cents >= 0),
  CONSTRAINT "chk_provider_disputes_currency_format" CHECK (currency ~ '^[A-Z]{3}$'),
  CONSTRAINT "chk_provider_disputes_result" CHECK ((status = 'RESOLVED') = (result IS NOT NULL)),
  CONSTRAINT "chk_provider_disputes_resolved_at" CHECK ((status = 'RESOLVED') = (resolved_at IS NOT NULL))
);

CREATE TABLE "provider_webhook_events" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64) NOT NULL,
  "dedupe_key" varchar(128) UNIQUE NOT NULL,
  "event_type" varchar(60) NOT NULL,
  "account_id" varchar(64),
  "resource_type" varchar(40),
  "resource_id" varchar(64),
  "payload" jsonb NOT NULL,
  "signature_verified" boolean,
  "status" webhook_processing_status NOT NULL DEFAULT 'RECEIVED',
  "attempts" int NOT NULL DEFAULT 0,
  "last_error" text,
  "received_at" timestamptz NOT NULL DEFAULT (now()),
  "processed_at" timestamptz,
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "provider_idempotency_keys" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "idempotency_key" varchar(100) NOT NULL,
  "request_hash" varchar(64),
  "resource_type" varchar(40),
  "resource_id" varchar(64),
  "status" idempotency_status,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "expires_at" timestamptz,
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "credit_packages" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "name" varchar,
  "credits" int NOT NULL,
  "price_cents" bigint NOT NULL,
  "credits_validity_days" int NOT NULL DEFAULT 30,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "is_active" boolean NOT NULL DEFAULT true,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_credit_packages_price_nonnegative" CHECK (price_cents >= 0),
  CONSTRAINT "chk_credit_packages_currency_format" CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "coupons" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "code" varchar(32) NOT NULL,
  "type" coupon_type NOT NULL,
  "discount_percent" numeric(5,2),
  "credits" int,
  "credits_validity_days" int NOT NULL DEFAULT 30,
  "applies_to" coupon_applies_to NOT NULL DEFAULT 'SUBSCRIPTION_AND_CREDITS',
  "min_purchase_cents" bigint,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "max_redemptions" int,
  "once_per_workspace" boolean NOT NULL DEFAULT false,
  "expires_at" timestamptz,
  "is_active" boolean NOT NULL DEFAULT true,
  "internal_note" varchar(255),
  "created_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz,
  CONSTRAINT "chk_coupons_type_exclusive_fields" CHECK ((type = 'DISCOUNT' AND discount_percent IS NOT NULL AND credits IS NULL) OR (type = 'CREDIT' AND credits IS NOT NULL AND discount_percent IS NULL)),
  CONSTRAINT "chk_coupons_discount_percent" CHECK (discount_percent IS NULL OR (discount_percent > 0 AND discount_percent <= 100)),
  CONSTRAINT "chk_coupons_min_purchase_nonnegative" CHECK (min_purchase_cents IS NULL OR min_purchase_cents >= 0),
  CONSTRAINT "chk_coupons_currency_format" CHECK (currency ~ '^[A-Z]{3}$'),
  CONSTRAINT "chk_coupons_code_upper" CHECK (code = upper(code))
);

CREATE TABLE "coupon_redemptions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "coupon_id" uuid NOT NULL,
  "user_id" uuid NOT NULL,
  "workspace_id" uuid NOT NULL,
  "order_id" uuid,
  "subscription_id" uuid,
  "invoice_id" uuid,
  "credit_transaction_id" uuid,
  "provider" payment_provider NOT NULL DEFAULT 'PAGARME',
  "external_id" varchar(64),
  "discount_percent_applied" numeric(5,2),
  "discount_amount_cents" bigint,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "credits_applied" int,
  "status" coupon_redemption_status NOT NULL DEFAULT 'APPLIED',
  "once_per_workspace" boolean NOT NULL DEFAULT false,
  "redeemed_at" timestamptz NOT NULL DEFAULT (now()),
  "canceled_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_coupon_redemptions_single_target" CHECK (num_nonnulls(order_id, subscription_id) = 1),
  CONSTRAINT "chk_coupon_redemptions_discount_percent" CHECK (discount_percent_applied IS NULL OR (discount_percent_applied > 0 AND discount_percent_applied <= 100)),
  CONSTRAINT "chk_coupon_redemptions_amount_nonnegative" CHECK (discount_amount_cents IS NULL OR discount_amount_cents >= 0),
  CONSTRAINT "chk_coupon_redemptions_currency_format" CHECK (currency ~ '^[A-Z]{3}$')
);

-- M1: ledger append-only: transacoes registram movimento e balance_after;
-- lotes sao a fonte do saldo disponivel e da validade.
CREATE TABLE "workspace_credit_transactions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "workspace_id" uuid NOT NULL,
  "amount" int NOT NULL CHECK (amount <> 0),
  "balance_after" bigint NOT NULL DEFAULT 0,
  "type" credit_transaction_type NOT NULL,
  "order_id" uuid,
  "invoice_id" uuid,
  "generated_image_id" uuid,
  "image_resize_id" uuid,
  "created_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT "chk_credit_tx_single_reference" CHECK (num_nonnulls(order_id, invoice_id, generated_image_id, image_resize_id) <= 1),
  CONSTRAINT "chk_credit_tx_balance_nonnegative" CHECK (balance_after >= 0),
  CONSTRAINT "chk_credit_tx_amount_by_type" CHECK (
    (type IN ('SUBSCRIPTION_CREDIT', 'TOP_UP', 'COUPON_CREDIT', 'REFUND') AND amount > 0)
    OR (type IN ('GENERATION', 'EXPIRATION') AND amount < 0)
    OR type = 'ADJUSTMENT'
  )
);

CREATE TABLE "workspace_credit_lots" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "workspace_id" uuid NOT NULL,
  "grant_transaction_id" uuid UNIQUE NOT NULL,
  "original_amount" int NOT NULL,
  "remaining_amount" int NOT NULL,
  "expires_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT now(),
  "updated_at" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT "chk_credit_lots_amounts" CHECK (original_amount > 0 AND remaining_amount >= 0 AND remaining_amount <= original_amount)
);

CREATE TABLE "workspace_credit_lot_consumptions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "workspace_id" uuid NOT NULL,
  "lot_id" uuid NOT NULL,
  "transaction_id" uuid NOT NULL,
  "amount" int NOT NULL CHECK (amount > 0),
  "created_at" timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE "brands" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "workspace_id" uuid NOT NULL,
  "created_by" uuid,
  "name" varchar(100),
  "segment" varchar(100),
  "promise" varchar(250),
  "goals" varchar(1800),
  "indicators" varchar(250),
  "inspirations" varchar(1500),
  "restrictions" varchar(200),
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz
);

CREATE TABLE "brand_values" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "brand_id" uuid NOT NULL,
  "value" varchar(100) NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "brand_hashtags" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "brand_id" uuid NOT NULL,
  "hashtag" varchar(100) NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "brand_colors" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "brand_id" uuid NOT NULL,
  "name" varchar(50),
  "hex" varchar(7) NOT NULL,
  "position" int,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_brand_colors_hex" CHECK (hex ~ '^#[0-9A-Fa-f]{6}$')
);

CREATE TABLE "brand_assets" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "brand_id" uuid NOT NULL,
  "type" brand_asset_type NOT NULL,
  "storage_bucket" varchar(63) NOT NULL,
  "storage_key" varchar(1024) NOT NULL,
  "file_name" varchar,
  "description" varchar,
  "created_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "brand_business_details" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "brand_id" uuid NOT NULL,
  "campaign_id" uuid NOT NULL,
  "persona_id" uuid NOT NULL,
  "output" jsonb NOT NULL,
  "model" varchar(50),
  "spec_version" varchar(50),
  "created_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "campaigns" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "brand_id" uuid NOT NULL,
  "created_by" uuid,
  "name" varchar(100),
  "description" varchar(500),
  "target_audience" varchar(300),
  "objectives" varchar(400),
  "expected_action" varchar(250),
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz
);

CREATE TABLE "campaign_hashtags" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "campaign_id" uuid NOT NULL,
  "hashtag" varchar(60) NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "campaign_voices" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "campaign_id" uuid NOT NULL,
  "voice" campaign_voice NOT NULL,
  "created_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "personas" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "created_by" uuid,
  "brand_id" uuid NOT NULL,
  "name" varchar(100),
  "age_range" age_range,
  "gender" persona_gender,
  "main_goal" varchar(60),
  "challenge" varchar(50),
  "routine" varchar(300),
  "journey" varchar(250),
  "trigger_event" varchar(200),
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz
);

CREATE TABLE "persona_interests" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "persona_id" uuid NOT NULL,
  "interest" varchar(100) NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "content_plans" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "brand_id" uuid NOT NULL,
  "campaign_id" uuid NOT NULL,
  "persona_id" uuid NOT NULL,
  "created_by" uuid,
  "briefing" varchar(400),
  "start_date" date,
  "end_date" date,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz,
  CONSTRAINT "chk_content_plans_period_order" CHECK (start_date IS NULL OR end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE "content_plan_items" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "content_plan_id" uuid NOT NULL,
  "format" content_format NOT NULL,
  "quantity" int NOT NULL CHECK (quantity >= 0) DEFAULT 0,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "content_plan_special_dates" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "content_plan_id" uuid NOT NULL,
  "special_date" date NOT NULL,
  "label" varchar(50),
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "posts" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "content_plan_id" uuid NOT NULL,
  "created_by" uuid,
  "title" varchar(100),
  "objective" varchar(300),
  "big_idea" varchar(150),
  "main_message" varchar(150),
  "publication_status" publication_status NOT NULL DEFAULT 'DRAFT',
  "approval_status" approval_status NOT NULL DEFAULT 'PENDING',
  "approved_by" uuid,
  "approved_at" timestamptz,
  "rejection_reason" varchar(500),
  "scheduled_at" timestamptz,
  "published_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz,
  CONSTRAINT "chk_posts_approval_pair" CHECK ((approved_at IS NULL) = (approved_by IS NULL)),
  CONSTRAINT "chk_posts_rejected_reason" CHECK (approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL),
  CONSTRAINT "chk_posts_approved_metadata" CHECK (approval_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)),
  CONSTRAINT "chk_posts_scheduled_at" CHECK (publication_status <> 'SCHEDULED' OR scheduled_at IS NOT NULL),
  CONSTRAINT "chk_posts_published_at" CHECK (publication_status <> 'PUBLISHED' OR published_at IS NOT NULL),
  CONSTRAINT "chk_posts_publish_requires_approval" CHECK (publication_status = 'DRAFT' OR approval_status = 'APPROVED')
);

CREATE TABLE "captions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "post_id" uuid NOT NULL,
  "created_by" uuid,
  "body" varchar(2000) NOT NULL,
  "version" int NOT NULL CHECK (version >= 1) DEFAULT 1,
  "is_current" boolean NOT NULL DEFAULT true,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "post_designs" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "post_id" uuid NOT NULL,
  "format" content_format NOT NULL,
  "ratio" art_ratio NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_post_designs_stories_ratio" CHECK (format <> 'STORIES' OR ratio = 'RATIO_9_16')
);

CREATE TABLE "design_slides" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "post_design_id" uuid NOT NULL,
  "position" int NOT NULL CHECK (position >= 0),
  "headline" varchar(50),
  "subtitle" varchar(40),
  "cta" varchar(30),
  "art_direction" varchar(1000) NOT NULL,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "generated_images" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "design_slide_id" uuid NOT NULL,
  "storage_bucket" varchar(63),
  "storage_key" varchar(1024),
  "mime_type" varchar(127) NOT NULL DEFAULT 'image/png',
  "size_bytes" bigint,
  "width" int,
  "height" int,
  "model" varchar(50),
  "prompt" varchar,
  "created_by" uuid,
  "error_message" varchar,
  "generation_status" generation_status NOT NULL DEFAULT 'GENERATING',
  "is_current" boolean NOT NULL DEFAULT false,
  "approval_status" approval_status NOT NULL DEFAULT 'PENDING',
  "approved_by" uuid,
  "approved_at" timestamptz,
  "rejection_reason" varchar(500),
  "feedback_type" image_feedback_type,
  "feedback_text" varchar(1000),
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  "deleted_at" timestamptz,
  CONSTRAINT "chk_generated_images_current_complete" CHECK (NOT is_current OR (generation_status = 'SUCCEEDED' AND deleted_at IS NULL)),
  CONSTRAINT "chk_generated_images_size_bytes" CHECK (size_bytes >= 0),
  CONSTRAINT "chk_generated_images_dimensions" CHECK (width > 0 AND height > 0),
  CONSTRAINT "chk_generated_images_approval_pair" CHECK ((approved_at IS NULL) = (approved_by IS NULL)),
  CONSTRAINT "chk_generated_images_rejected_reason" CHECK (approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL),
  CONSTRAINT "chk_generated_images_approved_metadata" CHECK (approval_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)),
  CONSTRAINT "chk_generated_images_approval_after_generation" CHECK (approval_status = 'PENDING' OR generation_status = 'SUCCEEDED'),
  CONSTRAINT "chk_generated_images_file_by_status" CHECK (
    generation_status <> 'SUCCEEDED'
    OR (storage_bucket IS NOT NULL AND storage_key IS NOT NULL
        AND size_bytes IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL)
  ),
  CONSTRAINT "chk_generated_images_failed_message" CHECK (
    generation_status <> 'FAILED' OR error_message IS NOT NULL
  )
);

-- M4: variantes de imagem ligadas a imagem original, com status independente.
CREATE TYPE "resize_status" AS ENUM ('PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED');

CREATE TABLE "image_resizes" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "source_image_id" uuid NOT NULL,
  "ratio" art_ratio NOT NULL,
  "status" resize_status NOT NULL DEFAULT 'PENDING',
  "storage_bucket" varchar(63),
  "storage_key" varchar(1024),
  "mime_type" varchar(127),
  "size_bytes" bigint,
  "width" int,
  "height" int,
  "error_message" varchar,
  "created_by" uuid,
  "created_at" timestamptz NOT NULL DEFAULT now(),
  "updated_at" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT "uq_image_resizes_source_ratio" UNIQUE (source_image_id, ratio),
  CONSTRAINT "chk_image_resizes_file" CHECK (
    status <> 'SUCCEEDED' OR
    (storage_bucket IS NOT NULL AND storage_key IS NOT NULL AND size_bytes IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL)
  ),
  CONSTRAINT "chk_image_resizes_failed" CHECK (status <> 'FAILED' OR error_message IS NOT NULL),
  CONSTRAINT "chk_image_resizes_size" CHECK (size_bytes IS NULL OR size_bytes > 0),
  CONSTRAINT "chk_image_resizes_dimensions" CHECK ((width IS NULL OR width > 0) AND (height IS NULL OR height > 0))
);

CREATE TABLE "audit_logs" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "actor_id" uuid,
  "workspace_id" uuid,
  "action" varchar(64) NOT NULL,
  "entity_type" varchar(60) NOT NULL,
  "entity_id" uuid NOT NULL,
  "before" jsonb,
  "after" jsonb,
  "ip_address" varchar(45),
  "user_agent" varchar(255),
  "created_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE TABLE "fiscal_invoices" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "billing_account_id" uuid NOT NULL,
  "order_id" uuid,
  "invoice_id" uuid,
  "subscription_id" uuid,
  "number" varchar(30),
  "series" varchar(10),
  "access_key" varchar(50),
  "service_code" varchar(20),
  "amount_cents" bigint NOT NULL,
  "currency" varchar(3) NOT NULL DEFAULT 'BRL',
  "status" fiscal_invoice_status NOT NULL DEFAULT 'PENDING',
  "pdf_storage_bucket" varchar(63),
  "pdf_storage_key" varchar(1024),
  "xml_storage_bucket" varchar(63),
  "xml_storage_key" varchar(1024),
  "error_message" varchar,
  "issued_at" timestamptz,
  "canceled_at" timestamptz,
  "created_at" timestamptz NOT NULL DEFAULT (now()),
  "updated_at" timestamptz NOT NULL DEFAULT (now()),
  CONSTRAINT "chk_fiscal_invoices_one_origin" CHECK (num_nonnulls(order_id, invoice_id, subscription_id) = 1),
  CONSTRAINT "chk_fiscal_invoices_amount_nonnegative" CHECK (amount_cents >= 0),
  CONSTRAINT "chk_fiscal_invoices_currency_format" CHECK (currency ~ '^[A-Z]{3}$')
);

CREATE TABLE "user_consents" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "type" consent_type NOT NULL,
  "document_version" varchar(20) NOT NULL,
  "granted" boolean NOT NULL DEFAULT true,
  "granted_at" timestamptz,
  "revoked_at" timestamptz,
  "ip_address" varchar(45),
  "user_agent" varchar(255),
  "created_at" timestamptz NOT NULL DEFAULT (now())
);

CREATE UNIQUE INDEX "uq_workspace_members_workspace_user" ON "workspace_members" ("workspace_id", "user_id");

CREATE UNIQUE INDEX "uq_users_email_active" ON "users" ("email") WHERE "deleted_at" IS NULL;

CREATE INDEX ON "workspace_members" ("user_id");

CREATE INDEX ON "workspace_members" ("workspace_id", "role");

CREATE INDEX ON "workspace_members" ("invited_by");

CREATE INDEX ON "workspace_invites" ("workspace_id");

CREATE INDEX ON "workspace_invites" ("email");

CREATE INDEX ON "workspace_invites" ("status");

CREATE INDEX ON "workspace_invite_usages" ("member_id");

CREATE UNIQUE INDEX ON "workspace_invite_usages" ("invite_id", "member_id");

CREATE UNIQUE INDEX ON "notifications" ("workspace_id", "dedupe_key");

CREATE INDEX ON "notifications" ("type");

CREATE INDEX ON "notifications" ("created_at");

CREATE INDEX ON "notification_recipients" ("user_id", "channel");

CREATE INDEX ON "notification_recipients" ("user_id", "read_at");

CREATE INDEX ON "notification_recipients" ("user_id", "created_at");

CREATE UNIQUE INDEX ON "notification_recipients" ("notification_id", "user_id", "channel");

CREATE INDEX ON "user_devices" ("user_id");

CREATE UNIQUE INDEX ON "notification_preferences" ("user_id", "type", "channel");

CREATE INDEX ON "billing_accounts" ("user_id");

CREATE INDEX ON "billing_accounts" ("document_hash");

CREATE UNIQUE INDEX ON "billing_accounts" ("provider", "external_id");

CREATE INDEX ON "billing_addresses" ("billing_account_id");

CREATE UNIQUE INDEX "uq_billing_addresses_default" ON "billing_addresses" ("billing_account_id") WHERE "is_default" AND "status" = 'ACTIVE';

CREATE UNIQUE INDEX ON "billing_payment_methods" ("billing_account_id", "external_id");

CREATE INDEX ON "billing_payment_methods" ("billing_account_id", "is_default");

CREATE UNIQUE INDEX "uq_billing_payment_methods_default" ON "billing_payment_methods" ("billing_account_id") WHERE "is_default" AND "status" = 'ACTIVE';

CREATE UNIQUE INDEX ON "plans" ("provider", "external_id");

CREATE UNIQUE INDEX ON "plan_items" ("provider", "external_id");

CREATE UNIQUE INDEX ON "plan_payment_methods" ("plan_id", "method");

CREATE UNIQUE INDEX ON "subscriptions" ("provider", "external_id");

CREATE UNIQUE INDEX ON "subscriptions" ("id", "workspace_id");

CREATE INDEX ON "subscriptions" ("billing_account_id");

CREATE INDEX ON "subscriptions" ("next_billing_at");

CREATE INDEX ON "subscriptions" ("workspace_id");

CREATE UNIQUE INDEX "uq_subscriptions_workspace_current" ON "subscriptions" ("workspace_id") WHERE "status" IN ('ACTIVE', 'TRIALING', 'PAST_DUE');

CREATE INDEX ON "subscription_history" ("subscription_id", "created_at");

CREATE UNIQUE INDEX ON "orders" ("provider", "external_id");

CREATE UNIQUE INDEX ON "orders" ("id", "workspace_id");

CREATE INDEX ON "orders" ("billing_account_id");

CREATE INDEX ON "orders" ("workspace_id");

CREATE INDEX ON "orders" ("status");

CREATE UNIQUE INDEX ON "invoices" ("provider", "external_id");

CREATE INDEX ON "invoices" ("billing_account_id");

CREATE INDEX ON "invoices" ("subscription_id", "due_at");

CREATE INDEX ON "invoices" ("status", "due_at");

CREATE UNIQUE INDEX ON "charges" ("provider", "external_id");

CREATE INDEX ON "charges" ("billing_account_id", "status");

CREATE INDEX ON "charges" ("invoice_id");

CREATE INDEX ON "charges" ("order_id");

CREATE INDEX ON "charges" ("status");

CREATE INDEX ON "charges" ("code");

CREATE INDEX ON "charges" ("paid_at");

CREATE INDEX ON "charge_transactions" ("status");

CREATE INDEX ON "charge_transactions" ("created_at");

CREATE UNIQUE INDEX ON "charge_transactions" ("charge_id", "provider", "external_id");

-- M3: favorece consulta da transacao mais recente por cobranca.
CREATE INDEX "idx_charge_transactions_latest" ON "charge_transactions" ("charge_id", "created_at" DESC NULLS LAST, "id" DESC);

CREATE INDEX ON "refunds" ("charge_id");

CREATE INDEX ON "refunds" ("status");

CREATE UNIQUE INDEX ON "refunds" ("provider", "external_id");

CREATE UNIQUE INDEX ON "provider_disputes" ("provider", "external_id");

CREATE INDEX ON "provider_disputes" ("charge_id");

CREATE INDEX ON "provider_disputes" ("status", "resolved_at");

CREATE INDEX ON "provider_webhook_events" ("event_type");

CREATE INDEX ON "provider_webhook_events" ("resource_id");

CREATE INDEX ON "provider_webhook_events" ("status", "received_at");

CREATE UNIQUE INDEX ON "provider_webhook_events" ("provider", "external_id");

CREATE UNIQUE INDEX ON "provider_idempotency_keys" ("provider", "idempotency_key");

CREATE INDEX ON "provider_idempotency_keys" ("expires_at");

CREATE UNIQUE INDEX "uq_coupons_code_active" ON "coupons" ("code") WHERE "deleted_at" IS NULL;

CREATE INDEX ON "coupons" ("type");

CREATE INDEX ON "coupons" ("is_active");

-- B4: captura a regra do cupom no momento do resgate.
CREATE FUNCTION "coupon_redemptions_set_once"() RETURNS trigger AS $$
BEGIN
  SELECT COALESCE(c."once_per_workspace", false)
    INTO NEW."once_per_workspace"
  FROM "coupons" c
  WHERE c."id" = NEW."coupon_id";
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER "trg_coupon_redemptions_set_once"
  BEFORE INSERT ON "coupon_redemptions"
  FOR EACH ROW EXECUTE FUNCTION "coupon_redemptions_set_once"();

CREATE INDEX ON "coupon_redemptions" ("coupon_id", "workspace_id");

CREATE INDEX ON "coupon_redemptions" ("user_id");

CREATE INDEX ON "coupon_redemptions" ("workspace_id");

CREATE INDEX ON "coupon_redemptions" ("order_id", "workspace_id");

CREATE INDEX ON "coupon_redemptions" ("subscription_id", "workspace_id");

CREATE UNIQUE INDEX ON "coupon_redemptions" ("provider", "external_id");

CREATE UNIQUE INDEX "uq_coupon_redemptions_once_per_workspace" ON "coupon_redemptions" ("coupon_id", "workspace_id") WHERE "once_per_workspace" AND "status" = 'APPLIED';

CREATE INDEX ON "workspace_credit_transactions" ("workspace_id", "created_at");

CREATE UNIQUE INDEX ON "workspace_credit_transactions" ("order_id", "type");

CREATE UNIQUE INDEX ON "workspace_credit_transactions" ("invoice_id", "type");

CREATE UNIQUE INDEX ON "workspace_credit_transactions" ("generated_image_id", "type");

CREATE INDEX ON "workspace_credit_lots" ("workspace_id", "expires_at");

CREATE INDEX ON "workspace_credit_lot_consumptions" ("transaction_id");

CREATE UNIQUE INDEX "uq_credit_tx_id_workspace" ON "workspace_credit_transactions" ("id", "workspace_id");

CREATE UNIQUE INDEX "uq_credit_lots_id_workspace" ON "workspace_credit_lots" ("id", "workspace_id");

CREATE UNIQUE INDEX ON "workspace_credit_lot_consumptions" ("lot_id", "transaction_id");

CREATE INDEX ON "brands" ("workspace_id");

CREATE UNIQUE INDEX ON "brand_values" ("brand_id", "value");

CREATE UNIQUE INDEX ON "brand_hashtags" ("brand_id", "hashtag");

CREATE INDEX ON "brand_colors" ("brand_id");

CREATE INDEX ON "brand_assets" ("brand_id");

CREATE INDEX ON "brand_assets" ("created_by");

CREATE UNIQUE INDEX ON "brand_assets" ("storage_bucket", "storage_key");

CREATE INDEX ON "brand_business_details" ("brand_id", "campaign_id", "persona_id");

CREATE INDEX ON "brand_business_details" ("created_at");

CREATE UNIQUE INDEX ON "campaigns" ("id", "brand_id");

CREATE INDEX ON "campaigns" ("brand_id");

CREATE UNIQUE INDEX ON "campaign_hashtags" ("campaign_id", "hashtag");

CREATE UNIQUE INDEX ON "campaign_voices" ("campaign_id", "voice");

CREATE UNIQUE INDEX ON "personas" ("id", "brand_id");

CREATE INDEX ON "personas" ("brand_id");

CREATE UNIQUE INDEX ON "persona_interests" ("persona_id", "interest");

CREATE INDEX ON "content_plans" ("brand_id");

CREATE INDEX ON "content_plans" ("campaign_id");

CREATE INDEX ON "content_plans" ("persona_id");

CREATE UNIQUE INDEX ON "content_plan_items" ("content_plan_id", "format");

CREATE UNIQUE INDEX ON "content_plan_special_dates" ("content_plan_id", "special_date", "label");

CREATE INDEX ON "posts" ("content_plan_id", "publication_status");

CREATE INDEX ON "posts" ("content_plan_id", "created_at");

CREATE INDEX ON "posts" ("publication_status");

CREATE INDEX ON "posts" ("approval_status");

CREATE INDEX ON "posts" ("scheduled_at");

CREATE INDEX ON "posts" ("approved_by");

CREATE UNIQUE INDEX ON "captions" ("post_id", "version");

CREATE UNIQUE INDEX "uq_captions_current" ON "captions" ("post_id") WHERE "is_current" AND "deleted_at" IS NULL;

CREATE INDEX ON "post_designs" ("post_id");

CREATE UNIQUE INDEX ON "design_slides" ("post_design_id", "position");

CREATE UNIQUE INDEX "uq_generated_images_current_per_slide" ON "generated_images" ("design_slide_id") WHERE "is_current" AND "deleted_at" IS NULL;
CREATE INDEX "idx_image_resizes_source_image" ON "image_resizes" ("source_image_id");
CREATE UNIQUE INDEX "uq_image_resizes_storage" ON "image_resizes" ("storage_bucket", "storage_key");
CREATE UNIQUE INDEX "uq_credit_tx_image_resize" ON "workspace_credit_transactions" ("image_resize_id", "type");

CREATE INDEX ON "generated_images" ("design_slide_id");

CREATE INDEX ON "generated_images" ("generation_status");

CREATE INDEX ON "generated_images" ("approval_status");

CREATE INDEX ON "generated_images" ("approved_by");

CREATE UNIQUE INDEX ON "generated_images" ("storage_bucket", "storage_key");

CREATE INDEX ON "audit_logs" ("entity_type", "entity_id", "created_at");

CREATE INDEX ON "audit_logs" ("actor_id", "created_at");

CREATE INDEX ON "audit_logs" ("workspace_id", "created_at");

CREATE INDEX ON "audit_logs" ("action", "created_at");

CREATE UNIQUE INDEX "uq_fiscal_invoices_access_key" ON "fiscal_invoices" ("access_key") WHERE "access_key" IS NOT NULL;
CREATE UNIQUE INDEX "uq_fiscal_invoices_number_series_account" ON "fiscal_invoices" ("billing_account_id", "series", "number") WHERE "series" IS NOT NULL AND "number" IS NOT NULL;

CREATE INDEX ON "fiscal_invoices" ("billing_account_id");

CREATE INDEX ON "fiscal_invoices" ("status");

CREATE INDEX ON "fiscal_invoices" ("order_id");

CREATE INDEX ON "fiscal_invoices" ("invoice_id");

CREATE INDEX ON "fiscal_invoices" ("subscription_id");

CREATE UNIQUE INDEX ON "user_consents" ("user_id", "type", "document_version");

COMMENT ON TABLE "users" IS 'LGPD: ao excluir a conta, anonimizar dados pessoais (email, display_name, bio, avatar_url), retendo apenas o necessário para obrigações legais.';

COMMENT ON COLUMN "users"."email" IS 'UNIQUE parcial em produção: WHERE deleted_at IS NULL (DBML não suporta índice parcial)';

COMMENT ON TABLE "workspace_members" IS 'R4: ao menos um OWNER ativo por workspace deve ser garantido em transacao/servico (nao expressavel em CHECK multi-linha). Remocao de membro = status REMOVED, preservando workspace_invite_usages.';

COMMENT ON TABLE "workspace_invites" IS 'N11: estado unico em status (EXPIRED incluido) + timestamps de evento (expires_at/last_used_at/revoked_at); usos = COUNT(workspace_invite_usages). Aceite atomico: lock da invite + count + insert da usage + criacao do member na mesma transacao.';

COMMENT ON COLUMN "workspace_invites"."token_hash" IS 'T8: SHA-256 hex do token; plaintext nunca persistido';

COMMENT ON TABLE "workspace_invite_usages" IS 'N9: user_id e workspace_id derivados do member (workspace_members); usos contados aqui (N11).';

COMMENT ON TABLE "notifications" IS 'Retenção: particionar por created_at (RANGE mensal); retenção sugerida ~180 dias com purge por DROP/DETACH; reter dedupe_key pelo horizonte de deduplicação.';

COMMENT ON TABLE "notification_recipients" IS 'N9: workspace_member_id removido; member derivavel por (user_id, notifications.workspace_id) em workspace_members.';

COMMENT ON TABLE "billing_accounts" IS 'LGPD: documento em ciphertext + hash; tipo derivado de payer_type (INDIVIDUAL=CPF, COMPANY=CNPJ). name/email/phone são contato fiscal do billing account (snapshot do provedor), não duplicatas de users. Anonimizar na exclusão da conta. N12: delinquent é atualizado exclusivamente pelo sync de webhook do provedor. T10: metadata com chaves esperadas {provider_customer_snapshot, fiscal_contact, external_refs}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON COLUMN "billing_accounts"."document" IS 'CPF/CNPJ cifrado (pgcrypto/KMS). Plaintext nunca persistido.';

COMMENT ON COLUMN "billing_accounts"."document_hash" IS 'SHA-256 hex do documento normalizado, usado para busca';

COMMENT ON TABLE "billing_addresses" IS 'T10: metadata com chaves esperadas {provider_address_snapshot}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "billing_payment_methods" IS 'N11: estado do cartao em status (ACTIVE/DELETED/EXPIRED); deleted_at removido como estado duplicado. T10: metadata com chaves esperadas {provider_card_snapshot, network_token_meta}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "plans" IS 'N10: price_cents substitui monthly_price_cents (nome alinhado ao intervalo); metodos permitidos em plan_payment_methods. T10: metadata com chaves esperadas {provider_plan_snapshot, feature_flags}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "plan_payment_methods" IS 'N10: métodos de pagamento permitidos por plano; max_installments por método.';

COMMENT ON TABLE "subscriptions" IS 'N6: snapshot intencional dos termos do plano na contratação (contracted_price_cents, billing_interval, interval_count, billing_type, installments, minimum_price_cents, statement_descriptor, trial_period_days) — mudanças no plano não afetam assinaturas vigentes. Ciclo: current_period_start/end e next_billing_at; billing_day derivado (EXTRACT(DAY FROM next_billing_at)); billing_at/start_at removidos por redundância. T10: metadata com chaves esperadas {provider_subscription_snapshot, cancel_reason}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "subscription_history" IS 'R6: registra mudanca de plano e de status (interno e do provedor) com autor e motivo; append-only.';

COMMENT ON TABLE "orders" IS 'N11: estado unico em status (PENDING/PAID/CANCELED/FAILED); closed removido. Desnormalizacao intencional: subtotal_cents/discount_cents/amount_cents congelados na contratacao (CHECK amount_cents = subtotal_cents - discount_cents). T10: metadata com chaves esperadas {provider_order_snapshot, utm}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "invoices" IS 'T10: metadata com chaves esperadas {provider_invoice_snapshot, pix_qr}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "charges" IS 'Estado consolidado da cobrança. external_id de orders/invoices derivado via order_id/invoice_id; gateway_response/antifraud_response ficam em charge_transactions; provider_payload sujeito a política de retenção. T10: metadata com chaves esperadas {provider_charge_snapshot, antifraud_summary}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "charge_transactions" IS 'Histórico de tentativas, captura e antifraude por cobrança. Definir política de retenção para payloads brutos.';

COMMENT ON TABLE "refunds" IS 'R6: inclui ID do reembolso no provedor e processed_at. T10: metadata com chaves esperadas {provider_refund_snapshot, reason_text}; nao usar jsonb para campos filtrados; GIN apenas se houver consulta.';

COMMENT ON TABLE "provider_webhook_events" IS 'Retenção: particionar por received_at (RANGE mensal) e purgar via DROP/DETACH PARTITION; payload bruto por até 90 dias e depois anonimizar (payload/last_error) preservando IDs/status/received_at; se particionar, incluir received_at no dedupe; (status, received_at) atende a fila RECEIVED/FAILED.';

COMMENT ON TABLE "provider_idempotency_keys" IS 'Retenção: purge diário WHERE expires_at < now(); índice (expires_at) viabiliza; particionar por expires_at se o volume for alto.';

COMMENT ON TABLE "coupons" IS 'N12: contagem de redencoes por COUNT(coupon_redemptions); max_redemptions aplicado atomicamente (lock da linha do cupom + count + insert na mesma transacao).';

COMMENT ON TABLE "coupon_redemptions" IS 'N8: alvo único (order XOR subscription); workspace_id e user_id mantidos para auditoria, workspace validado por FK composta com orders/subscriptions.';

COMMENT ON TABLE "workspace_credit_transactions" IS 'M1: fonte unica do saldo = SUM(amount) por workspace. Tabela append-only; saldo nao e persistido por transacao.';
COMMENT ON TABLE "workspace_credit_lots" IS 'M1: lotes controlam remaining_amount e expires_at; consumo diminui saldo por trigger.';
COMMENT ON TABLE "workspace_credit_lot_consumptions" IS 'M1: alocacoes imutaveis de debitos a lotes, com validacao de workspace e limite por trigger.';

COMMENT ON TABLE "brands" IS 'Raiz da hierarquia de conteúdo. RLS: policy direta por workspace_id. Valores e hashtags em brand_values/brand_hashtags (N2).';

COMMENT ON TABLE "brand_values" IS 'N2: valores da marca, um item por linha.';

COMMENT ON TABLE "brand_hashtags" IS 'N2: hashtags principais da marca, uma por linha.';

COMMENT ON TABLE "brand_assets" IS 'T9: URL nao persistida; storage_bucket/storage_key e URL assinada gerada na leitura. R3: created_by = uploader.';

COMMENT ON TABLE "brand_business_details" IS 'Detalhes da marca (Business) por combinação marca+campanha+persona. FKs compostas garantem campanha e persona da mesma marca.';

COMMENT ON TABLE "campaigns" IS 'UNIQUE (id, brand_id) habilita as FKs compostas de content_plans/brand_business_details. Hashtags em campaign_hashtags (N2).';

COMMENT ON TABLE "campaign_hashtags" IS 'N2: hashtags da campanha, uma por linha.';

COMMENT ON TABLE "personas" IS 'Persona sempre pertence a uma marca em brands (brand_id NOT NULL). UNIQUE (id, brand_id) habilita as FKs compostas. Interesses em persona_interests (N2).';

COMMENT ON TABLE "persona_interests" IS 'N2: interesses da persona, um por linha.';

COMMENT ON TABLE "content_plans" IS 'FKs compostas garantem campanha e persona da mesma marca. Quantidades por formato em content_plan_items (N1); datas especiais em content_plan_special_dates (N2). RLS via brands.workspace_id.';

COMMENT ON TABLE "content_plan_items" IS 'N1: quantidades por formato (IMAGE, CAROUSEL, STORIES). Novo formato = nova linha, sem ALTER TABLE.';

COMMENT ON TABLE "content_plan_special_dates" IS 'N2: datas especiais tipadas (date) + rótulo; vários rótulos por data permitidos.';

COMMENT ON TABLE "posts" IS 'M2: publication_status separado de approval_status (enum compartilhado com imagens). R7: trilha de aprovacao (approved_by/at, rejection_reason) e agendamento/publicacao. 3FN/RLS: sem workspace_id; workspace derivado via content_plans → brands.';

COMMENT ON TABLE "captions" IS 'N4: versionada; no máximo uma versão vigente por post (UNIQUE parcial (post_id) WHERE is_current no SQL).';

COMMENT ON TABLE "post_designs" IS '3FN: resolution derivada de ratio (não persistida): RATIO_1_1 = 1080x1080; RATIO_4_5 = 1080x1350; RATIO_9_16 = 1080x1920; RATIO_16_9 = 1920x1080. Regra: format STORIES implica RATIO_9_16 (CHECK). N4: headline/subtitle/cta/art_direction por slide em design_slides. RLS via posts → content_plans → brands.';

COMMENT ON TABLE "design_slides" IS 'N4: slides do design (IMAGE/STORIES = 1; CAROUSEL = N; cardinalidade validada na aplicação).';

COMMENT ON TABLE "generated_images" IS 'M2: generation_status separado de approval_status; COMPLETED exige arquivo. N4: vinculada ao slide (design_slide_id). T9: sem URL persistida — storage_bucket/storage_key e URL assinada gerada na leitura; custo em creditos derivado do ledger (workspace_credit_transactions.generated_image_id).';

COMMENT ON TABLE "audit_logs" IS 'R3: append-only; sem updated_at/deleted_at. Acoes sensiveis: ROLE_CHANGED, CONTENT_APPROVED, CONTENT_REJECTED, COUPON_REDEEMED, REFUND_REQUESTED, REFUND_PROCESSED, SUBSCRIPTION_CANCELED, ACCOUNT_DELETION_REQUESTED. before/after em jsonb; nao usar para filtros relacionais.';

COMMENT ON TABLE "fiscal_invoices" IS 'R9: documento fiscal (NFS-e) separado da fatura do gateway; emissao/cancelamento assincronos via status; PDF/XML em bucket/key.';

COMMENT ON TABLE "user_consents" IS 'R9/LGPD: prova de aceite/revogacao versionada por documento; imutavel exceto revoked_at; nao apagar em exclusao de conta (retencao legal).';

ALTER TABLE "workspace_members" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_members" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_invites" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_invites" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_invite_usages" ADD FOREIGN KEY ("invite_id") REFERENCES "workspace_invites" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_invite_usages" ADD FOREIGN KEY ("member_id") REFERENCES "workspace_members" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "notifications" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "notifications" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "notification_recipients" ADD FOREIGN KEY ("notification_id") REFERENCES "notifications" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "notification_recipients" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "user_devices" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "notification_preferences" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "billing_accounts" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "billing_addresses" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "billing_payment_methods" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "billing_payment_methods" ADD FOREIGN KEY ("billing_address_id") REFERENCES "billing_addresses" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "plan_items" ADD FOREIGN KEY ("plan_id") REFERENCES "plans" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "plan_payment_methods" ADD FOREIGN KEY ("plan_id") REFERENCES "plans" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscriptions" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscriptions" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscriptions" ADD FOREIGN KEY ("plan_id") REFERENCES "plans" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscriptions" ADD FOREIGN KEY ("payment_method_id") REFERENCES "billing_payment_methods" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscription_history" ADD FOREIGN KEY ("subscription_id") REFERENCES "subscriptions" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscription_history" ADD FOREIGN KEY ("old_plan_id") REFERENCES "plans" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscription_history" ADD FOREIGN KEY ("new_plan_id") REFERENCES "plans" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "orders" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "orders" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "orders" ADD FOREIGN KEY ("credit_package_id") REFERENCES "credit_packages" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "invoices" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "invoices" ADD FOREIGN KEY ("subscription_id") REFERENCES "subscriptions" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "charges" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "charges" ADD FOREIGN KEY ("invoice_id") REFERENCES "invoices" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "charges" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "charges" ADD FOREIGN KEY ("payment_method_id") REFERENCES "billing_payment_methods" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "charge_transactions" ADD FOREIGN KEY ("charge_id") REFERENCES "charges" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "refunds" ADD FOREIGN KEY ("charge_id") REFERENCES "charges" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "refunds" ADD FOREIGN KEY ("requested_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "provider_disputes" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "provider_disputes" ADD FOREIGN KEY ("charge_id") REFERENCES "charges" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "coupons" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "coupon_redemptions" ADD FOREIGN KEY ("coupon_id") REFERENCES "coupons" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "coupon_redemptions" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "coupon_redemptions" ADD FOREIGN KEY ("order_id", "workspace_id") REFERENCES "orders" ("id", "workspace_id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "coupon_redemptions" ADD FOREIGN KEY ("subscription_id", "workspace_id") REFERENCES "subscriptions" ("id", "workspace_id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "coupon_redemptions" ADD FOREIGN KEY ("invoice_id") REFERENCES "invoices" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "coupon_redemptions" ADD FOREIGN KEY ("credit_transaction_id") REFERENCES "workspace_credit_transactions" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_transactions" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_transactions" ADD FOREIGN KEY ("order_id", "workspace_id") REFERENCES "orders" ("id", "workspace_id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_transactions" ADD FOREIGN KEY ("invoice_id") REFERENCES "invoices" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_transactions" ADD FOREIGN KEY ("generated_image_id") REFERENCES "generated_images" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_transactions" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_lots" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_lots" ADD FOREIGN KEY ("grant_transaction_id", "workspace_id") REFERENCES "workspace_credit_transactions" ("id", "workspace_id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_lot_consumptions" ADD FOREIGN KEY ("lot_id", "workspace_id") REFERENCES "workspace_credit_lots" ("id", "workspace_id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_credit_lot_consumptions" ADD FOREIGN KEY ("transaction_id", "workspace_id") REFERENCES "workspace_credit_transactions" ("id", "workspace_id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

-- M1: os lotes mantem o saldo disponivel e a validade; o ledger e append-only.
-- Transacoes recebem saldo derivado sob lock do workspace. Operacoes de concessao,
-- consumo e expiracao precisam ocorrer atomicamente com seus lotes/consumos.
CREATE FUNCTION "workspace_credit_balance"(p_workspace_id uuid) RETURNS bigint
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(SUM(remaining_amount), 0)::bigint
  FROM workspace_credit_lots
  WHERE workspace_id = p_workspace_id AND (expires_at IS NULL OR expires_at > now());
$$;

CREATE FUNCTION "workspace_credit_lot_available"(p_lot_id uuid) RETURNS bigint
LANGUAGE sql STABLE AS $$
  SELECT CASE WHEN expires_at IS NOT NULL AND expires_at <= now() THEN 0
              ELSE remaining_amount END::bigint
  FROM workspace_credit_lots WHERE id = p_lot_id;
$$;

CREATE FUNCTION "m1_validate_credit_transaction"() RETURNS trigger AS $$
DECLARE v_balance bigint;
BEGIN
  PERFORM 1 FROM workspaces WHERE id = NEW.workspace_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'workspace inexistente: %', NEW.workspace_id; END IF;
  SELECT COALESCE(SUM(amount), 0) INTO v_balance
  FROM workspace_credit_transactions WHERE workspace_id = NEW.workspace_id;
  NEW.balance_after := v_balance + NEW.amount;
  IF NEW.balance_after < 0 THEN
    RAISE EXCEPTION 'credito insuficiente no workspace %', NEW.workspace_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER "trg_m1_credit_tx_validate" BEFORE INSERT ON "workspace_credit_transactions"
FOR EACH ROW EXECUTE FUNCTION "m1_validate_credit_transaction"();

-- Valida a procedencia da imagem no mesmo workspace (cadeia ate brands).
CREATE FUNCTION "check_credit_tx_image_workspace"() RETURNS trigger AS $$
DECLARE img_ws uuid;
BEGIN
  IF NEW.generated_image_id IS NULL AND NEW.image_resize_id IS NULL THEN RETURN NEW; END IF;
  SELECT b.workspace_id INTO img_ws
  FROM generated_images gi
  JOIN design_slides ds ON ds.id = gi.design_slide_id
  JOIN post_designs pd ON pd.id = ds.post_design_id
  JOIN posts p ON p.id = pd.post_id
  JOIN content_plans cp ON cp.id = p.content_plan_id
  JOIN brands b ON b.id = cp.brand_id
  WHERE gi.id = COALESCE(NEW.generated_image_id, (SELECT ir.source_image_id FROM image_resizes ir WHERE ir.id = NEW.image_resize_id));
  IF img_ws IS DISTINCT FROM NEW.workspace_id THEN
    RAISE EXCEPTION 'image/resize does not belong to workspace % (image %, resize %)', NEW.workspace_id, NEW.generated_image_id, NEW.image_resize_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER "trg_credit_tx_image_workspace"
  BEFORE INSERT ON "workspace_credit_transactions"
  FOR EACH ROW EXECUTE FUNCTION "check_credit_tx_image_workspace"();

CREATE FUNCTION "m1_validate_credit_lot"() RETURNS trigger AS $$
DECLARE v_grant int;
BEGIN
  PERFORM 1 FROM workspaces WHERE id = NEW.workspace_id FOR UPDATE;
  SELECT amount INTO v_grant FROM workspace_credit_transactions
    WHERE id = NEW.grant_transaction_id AND workspace_id = NEW.workspace_id;
  IF v_grant IS NULL OR v_grant <= 0 OR NEW.original_amount <> v_grant
       OR NEW.remaining_amount <> NEW.original_amount THEN
    RAISE EXCEPTION 'lote exige concessao positiva integral do mesmo workspace';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER "trg_m1_credit_lot_validate" BEFORE INSERT ON "workspace_credit_lots"
FOR EACH ROW EXECUTE FUNCTION "m1_validate_credit_lot"();

CREATE FUNCTION "m1_validate_credit_consumption"() RETURNS trigger AS $$
DECLARE v_debit int; v_allocated bigint; v_exp timestamptz;
BEGIN
  PERFORM 1 FROM workspaces WHERE id = NEW.workspace_id FOR UPDATE;
  SELECT expires_at INTO v_exp FROM workspace_credit_lots
  WHERE id = NEW.lot_id AND workspace_id = NEW.workspace_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'lote nao pertence ao workspace'; END IF;
  IF v_exp IS NOT NULL AND v_exp <= now() THEN
    RAISE EXCEPTION 'lote expirado %', NEW.lot_id;
  END IF;
  SELECT amount INTO v_debit FROM workspace_credit_transactions
  WHERE id = NEW.transaction_id AND workspace_id = NEW.workspace_id FOR UPDATE;
  IF v_debit IS NULL OR v_debit >= 0 THEN
    RAISE EXCEPTION 'consumo exige transacao negativa do mesmo workspace';
  END IF;
  SELECT COALESCE(SUM(amount), 0) INTO v_allocated
  FROM workspace_credit_lot_consumptions WHERE transaction_id = NEW.transaction_id;
  IF v_allocated + NEW.amount > -(v_debit::bigint) THEN
    RAISE EXCEPTION 'consumos excedem debito %', NEW.transaction_id;
  END IF;
  UPDATE workspace_credit_lots
     SET remaining_amount = remaining_amount - NEW.amount,
         updated_at = now()
   WHERE id = NEW.lot_id AND remaining_amount >= NEW.amount;
  IF NOT FOUND THEN RAISE EXCEPTION 'consumo excede credito disponivel do lote %', NEW.lot_id; END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER "trg_m1_credit_consumption_validate" BEFORE INSERT ON "workspace_credit_lot_consumptions"
FOR EACH ROW EXECUTE FUNCTION "m1_validate_credit_consumption"();

CREATE FUNCTION "m1_reject_credit_mutation"() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'ledger append-only: operacao % nao permitida em %', TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER "trg_m1_tx_immutable" BEFORE UPDATE OR DELETE ON "workspace_credit_transactions"
FOR EACH ROW EXECUTE FUNCTION "m1_reject_credit_mutation"();
CREATE TRIGGER "trg_m1_consumption_immutable" BEFORE UPDATE OR DELETE ON "workspace_credit_lot_consumptions"
FOR EACH ROW EXECUTE FUNCTION "m1_reject_credit_mutation"();

-- Lotes sao mutaveis APENAS no saldo e updated_at, sob consumo controlado.
CREATE FUNCTION "m1_guard_credit_lot_update"() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'nao e permitido excluir lote de credito';
  END IF;
  IF pg_trigger_depth() < 2 OR
     (to_jsonb(OLD) - 'remaining_amount' - 'updated_at') IS DISTINCT FROM
     (to_jsonb(NEW) - 'remaining_amount' - 'updated_at') OR
     NEW.remaining_amount > OLD.remaining_amount THEN
    RAISE EXCEPTION 'alteracao direta de lote proibida';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER "trg_m1_lot_guard" BEFORE UPDATE OR DELETE ON "workspace_credit_lots"
FOR EACH ROW EXECUTE FUNCTION "m1_guard_credit_lot_update"();

ALTER TABLE "brands" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brands" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_values" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_hashtags" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_colors" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_assets" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_business_details" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_business_details" ADD FOREIGN KEY ("campaign_id", "brand_id") REFERENCES "campaigns" ("id", "brand_id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_business_details" ADD FOREIGN KEY ("persona_id", "brand_id") REFERENCES "personas" ("id", "brand_id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_business_details" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaigns" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaigns" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaign_hashtags" ADD FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "campaign_voices" ADD FOREIGN KEY ("campaign_id") REFERENCES "campaigns" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "personas" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "personas" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "persona_interests" ADD FOREIGN KEY ("persona_id") REFERENCES "personas" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_plans" ADD FOREIGN KEY ("brand_id") REFERENCES "brands" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_plans" ADD FOREIGN KEY ("campaign_id", "brand_id") REFERENCES "campaigns" ("id", "brand_id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_plans" ADD FOREIGN KEY ("persona_id", "brand_id") REFERENCES "personas" ("id", "brand_id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_plans" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_plan_items" ADD FOREIGN KEY ("content_plan_id") REFERENCES "content_plans" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "content_plan_special_dates" ADD FOREIGN KEY ("content_plan_id") REFERENCES "content_plans" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "posts" ADD FOREIGN KEY ("content_plan_id") REFERENCES "content_plans" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "posts" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "captions" ADD FOREIGN KEY ("post_id") REFERENCES "posts" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "captions" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "post_designs" ADD FOREIGN KEY ("post_id") REFERENCES "posts" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "design_slides" ADD FOREIGN KEY ("post_design_id") REFERENCES "post_designs" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "generated_images" ADD FOREIGN KEY ("design_slide_id") REFERENCES "design_slides" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "workspace_members" ADD FOREIGN KEY ("invited_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "brand_assets" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "generated_images" ADD FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "subscription_history" ADD FOREIGN KEY ("changed_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "posts" ADD FOREIGN KEY ("approved_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "generated_images" ADD FOREIGN KEY ("approved_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "audit_logs" ADD FOREIGN KEY ("actor_id") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "audit_logs" ADD FOREIGN KEY ("workspace_id") REFERENCES "workspaces" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "fiscal_invoices" ADD FOREIGN KEY ("billing_account_id") REFERENCES "billing_accounts" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "fiscal_invoices" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "fiscal_invoices" ADD FOREIGN KEY ("invoice_id") REFERENCES "invoices" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "fiscal_invoices" ADD FOREIGN KEY ("subscription_id") REFERENCES "subscriptions" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "user_consents" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;

-- M3: projecao da cobranca com sua ultima transacao, sem duplicar estado em charges.
-- A ordenacao utiliza created_at e id como desempate deterministico.
-- Caso nao haja transacoes, os campos last_transaction_* retornam NULL.
CREATE VIEW "charges_with_last_transaction" AS
SELECT
  c.*,
  latest."external_id" AS "last_transaction_id",
  latest."status" AS "last_transaction_status"
FROM "charges" c
LEFT JOIN LATERAL (
  SELECT ct."external_id", ct."status"
  FROM "charge_transactions" ct
  WHERE ct."charge_id" = c."id"
  ORDER BY ct."created_at" DESC NULLS LAST, ct."id" DESC
  LIMIT 1
) latest ON true;


-- M7: historico de assinaturas e append-only; retificacoes devem gerar novo evento.
CREATE FUNCTION "m7_reject_subscription_history_mutation"() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'subscription_history is append-only: % not allowed', TG_OP;
END;
$$;
CREATE TRIGGER "trg_subscription_history_append_only" BEFORE UPDATE OR DELETE ON "subscription_history"
FOR EACH ROW EXECUTE FUNCTION "m7_reject_subscription_history_mutation"();

-- M7: atualizacao automatica apenas em tabelas mutaveis.
CREATE FUNCTION "set_updated_at"() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;
CREATE TRIGGER "trg_updated_at_workspace_credit_lots" BEFORE UPDATE ON "workspace_credit_lots" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_users" BEFORE UPDATE ON "users" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_workspaces" BEFORE UPDATE ON "workspaces" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_workspace_members" BEFORE UPDATE ON "workspace_members" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_workspace_invites" BEFORE UPDATE ON "workspace_invites" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_workspace_invite_usages" BEFORE UPDATE ON "workspace_invite_usages" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_notifications" BEFORE UPDATE ON "notifications" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_notification_recipients" BEFORE UPDATE ON "notification_recipients" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_user_devices" BEFORE UPDATE ON "user_devices" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_notification_preferences" BEFORE UPDATE ON "notification_preferences" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_billing_accounts" BEFORE UPDATE ON "billing_accounts" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_billing_addresses" BEFORE UPDATE ON "billing_addresses" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_billing_payment_methods" BEFORE UPDATE ON "billing_payment_methods" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_plans" BEFORE UPDATE ON "plans" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_plan_items" BEFORE UPDATE ON "plan_items" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_plan_payment_methods" BEFORE UPDATE ON "plan_payment_methods" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_subscriptions" BEFORE UPDATE ON "subscriptions" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_orders" BEFORE UPDATE ON "orders" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_invoices" BEFORE UPDATE ON "invoices" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_charges" BEFORE UPDATE ON "charges" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_charge_transactions" BEFORE UPDATE ON "charge_transactions" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_refunds" BEFORE UPDATE ON "refunds" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_provider_disputes" BEFORE UPDATE ON "provider_disputes" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_provider_webhook_events" BEFORE UPDATE ON "provider_webhook_events" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_provider_idempotency_keys" BEFORE UPDATE ON "provider_idempotency_keys" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_credit_packages" BEFORE UPDATE ON "credit_packages" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_coupons" BEFORE UPDATE ON "coupons" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_coupon_redemptions" BEFORE UPDATE ON "coupon_redemptions" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_brands" BEFORE UPDATE ON "brands" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_brand_values" BEFORE UPDATE ON "brand_values" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_brand_hashtags" BEFORE UPDATE ON "brand_hashtags" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_brand_colors" BEFORE UPDATE ON "brand_colors" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_brand_assets" BEFORE UPDATE ON "brand_assets" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_brand_business_details" BEFORE UPDATE ON "brand_business_details" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_campaigns" BEFORE UPDATE ON "campaigns" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_campaign_hashtags" BEFORE UPDATE ON "campaign_hashtags" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_campaign_voices" BEFORE UPDATE ON "campaign_voices" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_personas" BEFORE UPDATE ON "personas" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_persona_interests" BEFORE UPDATE ON "persona_interests" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_content_plans" BEFORE UPDATE ON "content_plans" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_content_plan_items" BEFORE UPDATE ON "content_plan_items" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_content_plan_special_dates" BEFORE UPDATE ON "content_plan_special_dates" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_posts" BEFORE UPDATE ON "posts" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_captions" BEFORE UPDATE ON "captions" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_post_designs" BEFORE UPDATE ON "post_designs" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_design_slides" BEFORE UPDATE ON "design_slides" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_generated_images" BEFORE UPDATE ON "generated_images" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();
CREATE TRIGGER "trg_updated_at_fiscal_invoices" BEFORE UPDATE ON "fiscal_invoices" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();

ALTER TABLE "image_resizes" ADD CONSTRAINT "fk_image_resizes_source_image" FOREIGN KEY ("source_image_id") REFERENCES "generated_images" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY IMMEDIATE;
ALTER TABLE "image_resizes" ADD CONSTRAINT "fk_image_resizes_created_by" FOREIGN KEY ("created_by") REFERENCES "users" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY IMMEDIATE;
ALTER TABLE "workspace_credit_transactions" ADD CONSTRAINT "fk_credit_tx_image_resize" FOREIGN KEY ("image_resize_id") REFERENCES "image_resizes" ("id") ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;
CREATE INDEX "idx_image_resizes_created_by" ON "image_resizes" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE TRIGGER "trg_updated_at_image_resizes" BEFORE UPDATE ON "image_resizes" FOR EACH ROW EXECUTE FUNCTION "set_updated_at"();

-- M8: indices de suporte para chaves estrangeiras nao cobertas por prefixo de indice existente.
CREATE INDEX "idx_m8_workspace_invites_created_by" ON "workspace_invites" ("created_by");
CREATE INDEX "idx_m8_notifications_created_by" ON "notifications" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_billing_payment_methods_billing_address_id" ON "billing_payment_methods" ("billing_address_id") WHERE "billing_address_id" IS NOT NULL;
CREATE INDEX "idx_m8_plan_items_plan_id" ON "plan_items" ("plan_id");
CREATE INDEX "idx_m8_subscriptions_plan_id" ON "subscriptions" ("plan_id");
CREATE INDEX "idx_m8_subscriptions_payment_method_id" ON "subscriptions" ("payment_method_id") WHERE "payment_method_id" IS NOT NULL;
CREATE INDEX "idx_m8_subscription_history_old_plan_id" ON "subscription_history" ("old_plan_id") WHERE "old_plan_id" IS NOT NULL;
CREATE INDEX "idx_m8_subscription_history_new_plan_id" ON "subscription_history" ("new_plan_id") WHERE "new_plan_id" IS NOT NULL;
CREATE INDEX "idx_m8_orders_credit_package_id" ON "orders" ("credit_package_id") WHERE "credit_package_id" IS NOT NULL;
CREATE INDEX "idx_m8_charges_payment_method_id" ON "charges" ("payment_method_id") WHERE "payment_method_id" IS NOT NULL;
CREATE INDEX "idx_m8_refunds_requested_by" ON "refunds" ("requested_by") WHERE "requested_by" IS NOT NULL;
CREATE INDEX "idx_m8_provider_disputes_billing_account_id" ON "provider_disputes" ("billing_account_id") WHERE "billing_account_id" IS NOT NULL;
CREATE INDEX "idx_m8_coupons_created_by" ON "coupons" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_coupon_redemptions_invoice_id" ON "coupon_redemptions" ("invoice_id") WHERE "invoice_id" IS NOT NULL;
CREATE INDEX "idx_m8_coupon_redemptions_credit_transaction_id" ON "coupon_redemptions" ("credit_transaction_id") WHERE "credit_transaction_id" IS NOT NULL;
CREATE INDEX "idx_m8_workspace_credit_transactions_created_by" ON "workspace_credit_transactions" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_workspace_credit_lots_grant_transaction_id_workspace_id" ON "workspace_credit_lots" ("grant_transaction_id", "workspace_id");
CREATE INDEX "idx_m8_workspace_credit_lot_consumptions_lot_id_workspace_id" ON "workspace_credit_lot_consumptions" ("lot_id", "workspace_id");
CREATE INDEX "idx_m8_lot_consumptions_transaction_workspace" ON "workspace_credit_lot_consumptions" ("transaction_id", "workspace_id");
CREATE INDEX "idx_m8_brands_created_by" ON "brands" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_brand_business_details_campaign_id_brand_id" ON "brand_business_details" ("campaign_id", "brand_id");
CREATE INDEX "idx_m8_brand_business_details_persona_id_brand_id" ON "brand_business_details" ("persona_id", "brand_id");
CREATE INDEX "idx_m8_brand_business_details_created_by" ON "brand_business_details" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_campaigns_created_by" ON "campaigns" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_personas_created_by" ON "personas" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_content_plans_campaign_id_brand_id" ON "content_plans" ("campaign_id", "brand_id");
CREATE INDEX "idx_m8_content_plans_persona_id_brand_id" ON "content_plans" ("persona_id", "brand_id");
CREATE INDEX "idx_m8_content_plans_created_by" ON "content_plans" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_posts_created_by" ON "posts" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_captions_created_by" ON "captions" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_generated_images_created_by" ON "generated_images" ("created_by") WHERE "created_by" IS NOT NULL;
CREATE INDEX "idx_m8_subscription_history_changed_by" ON "subscription_history" ("changed_by") WHERE "changed_by" IS NOT NULL;

COMMENT ON TABLE "image_resizes" IS 'M4: variantes por ratio com status independente; credito de resize referenciado no ledger.';
