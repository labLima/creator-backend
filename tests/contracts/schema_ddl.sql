CREATE TABLE activity_events (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	user_id CHAR(32),
	brand_id CHAR(32),
	entity_type VARCHAR(50) NOT NULL,
	entity_id CHAR(32),
	event_type VARCHAR(100) NOT NULL,
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_activity_events_entity_type CHECK (entity_type = 'brand'),
	CONSTRAINT ck_activity_events_event_type CHECK (event_type IN ('brand.created', 'brand.updated', 'brand.deleted')),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE RESTRICT
)

CREATE TABLE agent_workflow_runs (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	content_id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	requested_by_user_id CHAR(32),
	idempotency_key VARCHAR(128) NOT NULL,
	request_fingerprint VARCHAR(64) NOT NULL,
	status VARCHAR(24) DEFAULT 'PENDING' NOT NULL,
	human_review VARCHAR(8) DEFAULT 'AUTO' NOT NULL,
	max_refinements INTEGER DEFAULT 3 NOT NULL,
	refinement_count INTEGER DEFAULT 0 NOT NULL,
	current_step VARCHAR(64),
	input JSON DEFAULT '{}' NOT NULL,
	final_image_ids JSON DEFAULT '[]' NOT NULL,
	failure_code VARCHAR(100),
	failure_message TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	completed_at DATETIME,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_agent_workflow_runs_id_workspace UNIQUE (id, workspace_id),
	CONSTRAINT uq_agent_workflow_runs_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key),
	CONSTRAINT fk_agent_workflow_runs_workspace FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	CONSTRAINT fk_agent_workflow_runs_content_workspace FOREIGN KEY(content_id, workspace_id) REFERENCES contents (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_agent_workflow_runs_brand_workspace FOREIGN KEY(brand_id, workspace_id) REFERENCES brands (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT ck_agent_workflow_runs_max_refinements CHECK (max_refinements BETWEEN 0 AND 10),
	CONSTRAINT ck_agent_workflow_runs_refinement_count CHECK (refinement_count >= 0),
	FOREIGN KEY(requested_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
	CONSTRAINT agent_workflow_status CHECK (status IN ('PENDING', 'RUNNING', 'WAITING_FOR_HUMAN_REVIEW', 'REFINING', 'COMPLETED', 'REJECTED', 'FAILED')),
	CONSTRAINT human_review_mode CHECK (human_review IN ('AUTO', 'OPTIONAL'))
)

CREATE TABLE agent_workflow_steps (
	id CHAR(32) NOT NULL,
	run_id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	sequence_number INTEGER NOT NULL,
	role VARCHAR(8) NOT NULL,
	status VARCHAR(9) DEFAULT 'PENDING' NOT NULL,
	attempt INTEGER DEFAULT 1 NOT NULL,
	input JSON DEFAULT '{}' NOT NULL,
	output JSON DEFAULT '{}' NOT NULL,
	prompt TEXT,
	prompt_template_id VARCHAR(255),
	prompt_template_version VARCHAR(32),
	input_hash VARCHAR(64),
	output_hash VARCHAR(64),
	schema_name VARCHAR(100),
	schema_version VARCHAR(32),
	predecessor_step_id CHAR(32),
	correlation_id CHAR(32),
	source_event_id CHAR(32),
	stage_item INTEGER DEFAULT 0 NOT NULL,
	provider VARCHAR(100),
	model VARCHAR(255),
	decision VARCHAR(32),
	error_code VARCHAR(100),
	error_message TEXT,
	started_at DATETIME,
	completed_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_agent_workflow_steps_attempt UNIQUE (run_id, sequence_number, attempt),
	CONSTRAINT fk_agent_workflow_steps_run_workspace FOREIGN KEY(run_id, workspace_id) REFERENCES agent_workflow_runs (id, workspace_id) ON DELETE CASCADE,
	CONSTRAINT agent_workflow_step_role CHECK (role IN ('BUSINESS', 'PLANNER', 'WRITER', 'ARTIST', 'REVIEWER', 'DELIVERY')),
	CONSTRAINT agent_workflow_step_status CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED'))
)

CREATE TABLE assets (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	brand_id CHAR(32),
	project_id CHAR(32),
	content_id CHAR(32),
	uploaded_by_user_id CHAR(32),
	asset_type VARCHAR(100) NOT NULL,
	storage_path VARCHAR(1024) NOT NULL,
	public_url VARCHAR(2048),
	mime_type VARCHAR(100) NOT NULL,
	byte_size INTEGER NOT NULL,
	checksum VARCHAR(255),
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_assets_storage_path UNIQUE (storage_path),
	CONSTRAINT fk_assets_brand_workspace FOREIGN KEY(brand_id, workspace_id) REFERENCES brands (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_assets_project_workspace FOREIGN KEY(project_id, workspace_id) REFERENCES projects (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_assets_content_workspace FOREIGN KEY(content_id, workspace_id) REFERENCES contents (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT ck_assets_byte_size_non_negative CHECK (byte_size >= 0),
	CONSTRAINT ck_assets_deleted_after_created CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	FOREIGN KEY(uploaded_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE audit_logs (
	id CHAR(32) NOT NULL,
	actor_id CHAR(32),
	workspace_id CHAR(32),
	action VARCHAR(64) NOT NULL,
	entity_type VARCHAR(60) NOT NULL,
	entity_id CHAR(32) NOT NULL,
	"before" JSON,
	"after" JSON,
	ip_address VARCHAR(45),
	user_agent VARCHAR(255),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE SET NULL
)

CREATE TABLE auth_sessions (
	id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	family_id CHAR(32) NOT NULL,
	refresh_token_hash VARCHAR(64) NOT NULL,
	previous_refresh_token_hash VARCHAR(64),
	expires_at DATETIME NOT NULL,
	absolute_expires_at DATETIME NOT NULL,
	revoked_at DATETIME,
	replaced_by_id CHAR(32),
	rotated_at DATETIME,
	user_agent VARCHAR(500),
	ip_address VARCHAR(45),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	last_used_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_auth_sessions_refresh_token_hash UNIQUE (refresh_token_hash),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

CREATE TABLE billing_accounts (
	id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	payer_type VARCHAR(10) NOT NULL,
	name VARCHAR(64) NOT NULL,
	email VARCHAR(254) NOT NULL,
	phone VARCHAR(20),
	document BLOB,
	document_hash VARCHAR(64),
	company_name VARCHAR(64),
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	external_code VARCHAR(52),
	delinquent BOOLEAN DEFAULT false NOT NULL,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_billing_accounts_company_name CHECK ((payer_type = 'COMPANY') = (company_name IS NOT NULL)),
	CONSTRAINT chk_billing_accounts_document_pair CHECK ((document IS NULL) = (document_hash IS NULL)),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
)

CREATE TABLE billing_addresses (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	external_id VARCHAR(64),
	line_1 VARCHAR(256) NOT NULL,
	number VARCHAR(20) NOT NULL,
	line_2 VARCHAR(128),
	district VARCHAR(64),
	zip_code VARCHAR(8) NOT NULL,
	city VARCHAR(64) NOT NULL,
	state VARCHAR(2) NOT NULL,
	country VARCHAR(2) NOT NULL,
	status VARCHAR(8) DEFAULT 'ACTIVE' NOT NULL,
	is_default BOOLEAN DEFAULT false NOT NULL,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_billing_addresses_external_id UNIQUE (external_id),
	CONSTRAINT chk_billing_addresses_zip_code CHECK (country <> 'BR' OR zip_code GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
	CONSTRAINT chk_billing_addresses_state_uf CHECK (country <> 'BR' OR state GLOB '[A-Z][A-Z]'),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE CASCADE
)

CREATE TABLE billing_payment_methods (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	billing_address_id CHAR(32),
	external_id VARCHAR(64),
	external_network_token_id VARCHAR(64),
	first_six_digits VARCHAR(6),
	brand VARCHAR(10),
	card_last_four VARCHAR(4),
	holder_name VARCHAR(64),
	holder_document VARCHAR(16),
	exp_month INTEGER,
	exp_year INTEGER,
	type VARCHAR(6),
	status VARCHAR(7) DEFAULT 'ACTIVE' NOT NULL,
	is_default BOOLEAN DEFAULT false NOT NULL,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_billing_payment_methods_exp_month CHECK (exp_month IS NULL OR exp_month BETWEEN 1 AND 12),
	CONSTRAINT chk_billing_payment_methods_exp_year CHECK (exp_year IS NULL OR exp_year BETWEEN 2000 AND 2100),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE CASCADE,
	FOREIGN KEY(billing_address_id) REFERENCES billing_addresses (id) ON DELETE SET NULL
)

CREATE TABLE brand_assets (
	id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	type VARCHAR(8) NOT NULL,
	storage_bucket VARCHAR(63) NOT NULL,
	storage_key VARCHAR(1024) NOT NULL,
	file_name VARCHAR,
	description VARCHAR,
	created_by CHAR(32),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE,
	CONSTRAINT brand_asset_type CHECK (type IN ('LOGO', 'IMAGE', 'FONT', 'ICON', 'DOCUMENT', 'OTHER')),
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE brand_business_details (
	id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	campaign_id CHAR(32) NOT NULL,
	persona_id CHAR(32) NOT NULL,
	output JSON NOT NULL,
	model VARCHAR(50),
	spec_version VARCHAR(50),
	created_by CHAR(32),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_brand_business_details_campaign FOREIGN KEY(campaign_id, brand_id) REFERENCES campaigns (id, brand_id) ON DELETE CASCADE,
	CONSTRAINT fk_brand_business_details_persona FOREIGN KEY(persona_id, brand_id) REFERENCES personas (id, brand_id) ON DELETE CASCADE,
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE brand_colors (
	id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	name VARCHAR(50),
	hex VARCHAR(7) NOT NULL,
	position INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_brand_colors_hex CHECK (hex GLOB '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]'),
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE
)

CREATE TABLE brand_hashtags (
	id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	hashtag VARCHAR(100) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE
)

CREATE TABLE brand_settings (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	voice_settings JSON DEFAULT '{}' NOT NULL,
	visual_settings JSON DEFAULT '{}' NOT NULL,
	generation_defaults JSON DEFAULT '{}' NOT NULL,
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_brand_settings_brand_id UNIQUE (brand_id),
	CONSTRAINT fk_brand_settings_brand FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE,
	CONSTRAINT ck_brand_settings_deleted_after_created CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT
)

CREATE TABLE brand_values (
	id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	value VARCHAR(100) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE
)

CREATE TABLE brands (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	created_by CHAR(32),
	name VARCHAR(100) NOT NULL,
	segment VARCHAR(100),
	promise VARCHAR(250),
	goals VARCHAR(1800),
	indicators VARCHAR(250),
	inspirations VARCHAR(1500),
	restrictions VARCHAR(200),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_brands_id_workspace_id UNIQUE (id, workspace_id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE campaign_hashtags (
	id CHAR(32) NOT NULL,
	campaign_id CHAR(32) NOT NULL,
	hashtag VARCHAR(60) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
)

CREATE TABLE campaign_voices (
	id CHAR(32) NOT NULL,
	campaign_id CHAR(32) NOT NULL,
	voice VARCHAR(13) NOT NULL,
	created_by CHAR(32),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
	CONSTRAINT campaign_voice CHECK (voice IN ('INSPIRATIONAL', 'MOTIVATIONAL', 'PROFESSIONAL', 'CASUAL', 'ELEGANT', 'MODERN', 'TRADITIONAL', 'FUN', 'SERIOUS'))
)

CREATE TABLE campaigns (
	id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	created_by CHAR(32),
	name VARCHAR(100) NOT NULL,
	description VARCHAR(500),
	target_audience VARCHAR(300),
	objectives VARCHAR(400),
	expected_action VARCHAR(250),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE captions (
	id CHAR(32) NOT NULL,
	post_id CHAR(32) NOT NULL,
	created_by CHAR(32),
	body VARCHAR(2000) NOT NULL,
	version INTEGER DEFAULT 1 NOT NULL,
	is_current BOOLEAN DEFAULT true NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_captions_version CHECK (version >= 1),
	FOREIGN KEY(post_id) REFERENCES posts (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE charge_transactions (
	id CHAR(32) NOT NULL,
	charge_id CHAR(32) NOT NULL,
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	status VARCHAR(26) NOT NULL,
	amount_cents BIGINT NOT NULL,
	gateway_response JSON,
	antifraud_response JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_charge_transactions_amount_nonnegative CHECK (amount_cents >= 0),
	FOREIGN KEY(charge_id) REFERENCES charges (id) ON DELETE CASCADE
)

CREATE TABLE charges (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	invoice_id CHAR(32),
	order_id CHAR(32),
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	payment_method VARCHAR(11) NOT NULL,
	payment_method_id CHAR(32),
	code VARCHAR(52),
	amount_cents BIGINT NOT NULL,
	paid_amount_cents BIGINT,
	canceled_amount_cents BIGINT,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	installments INTEGER DEFAULT 1 NOT NULL,
	funding_source VARCHAR(6),
	status VARCHAR(11) NOT NULL,
	gateway_id VARCHAR(128),
	metadata JSON,
	provider_payload JSON,
	due_at DATETIME,
	paid_at DATETIME,
	canceled_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_charges_cents_nonnegative CHECK (amount_cents >= 0 AND (paid_amount_cents IS NULL OR paid_amount_cents >= 0) AND (canceled_amount_cents IS NULL OR canceled_amount_cents >= 0)),
	CONSTRAINT chk_charges_installments CHECK (installments IS NULL OR installments >= 1),
	CONSTRAINT chk_charges_currency_format CHECK (currency IS NULL OR currency GLOB '[A-Z][A-Z][A-Z]'),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE RESTRICT,
	FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE SET NULL,
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE SET NULL,
	FOREIGN KEY(payment_method_id) REFERENCES billing_payment_methods (id) ON DELETE SET NULL
)

CREATE TABLE content_plan_items (
	id CHAR(32) NOT NULL,
	content_plan_id CHAR(32) NOT NULL,
	format VARCHAR(8) NOT NULL,
	quantity INTEGER DEFAULT 0 NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_content_plan_items_quantity CHECK (quantity >= 0),
	FOREIGN KEY(content_plan_id) REFERENCES content_plans (id) ON DELETE CASCADE,
	CONSTRAINT content_format CHECK (format IN ('IMAGE', 'CAROUSEL', 'STORIES'))
)

CREATE TABLE content_plan_special_dates (
	id CHAR(32) NOT NULL,
	content_plan_id CHAR(32) NOT NULL,
	special_date DATE NOT NULL,
	label VARCHAR(50),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(content_plan_id) REFERENCES content_plans (id) ON DELETE CASCADE
)

CREATE TABLE content_plans (
	id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	campaign_id CHAR(32) NOT NULL,
	persona_id CHAR(32) NOT NULL,
	created_by CHAR(32),
	briefing VARCHAR(400),
	start_date DATE,
	end_date DATE,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT fk_content_plans_campaign FOREIGN KEY(campaign_id, brand_id) REFERENCES campaigns (id, brand_id) ON DELETE CASCADE,
	CONSTRAINT fk_content_plans_persona FOREIGN KEY(persona_id, brand_id) REFERENCES personas (id, brand_id) ON DELETE CASCADE,
	CONSTRAINT chk_content_plans_period_order CHECK (start_date IS NULL OR end_date IS NULL OR end_date >= start_date),
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE content_text_versions (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	content_id CHAR(32) NOT NULL,
	generation_id CHAR(32) NOT NULL,
	artifact_type VARCHAR(16) NOT NULL,
	version_number INTEGER NOT NULL,
	text TEXT NOT NULL,
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_content_text_versions_content_workspace FOREIGN KEY(content_id, workspace_id) REFERENCES contents (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT uq_content_text_versions_number UNIQUE (content_id, version_number),
	CONSTRAINT uq_content_text_versions_generation UNIQUE (generation_id),
	CONSTRAINT ck_content_text_versions_positive CHECK (version_number > 0),
	CONSTRAINT ck_content_text_versions_artifact_type CHECK (artifact_type IN ('COPY', 'CAPTION')),
	CONSTRAINT ck_content_text_versions_text CHECK (length(text) BETWEEN 1 AND 20000),
	FOREIGN KEY(generation_id) REFERENCES generations (id) ON DELETE RESTRICT
)

CREATE TABLE contents (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	created_by_user_id CHAR(32),
	brand_id CHAR(32),
	project_id CHAR(32),
	type VARCHAR(5) DEFAULT 'IMAGE' NOT NULL,
	title VARCHAR(255),
	payload JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_contents_id_workspace_id UNIQUE (id, workspace_id),
	CONSTRAINT fk_contents_brand_workspace FOREIGN KEY(brand_id, workspace_id) REFERENCES brands (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_contents_project_workspace FOREIGN KEY(project_id, workspace_id) REFERENCES projects (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT ck_contents_deleted_after_created CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
	CONSTRAINT content_type CHECK (type IN ('IMAGE', 'TEXT'))
)

CREATE TABLE coupon_redemptions (
	coupon_id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	order_id CHAR(32),
	subscription_id CHAR(32),
	provider_discount_id VARCHAR(64),
	discount_percent_applied NUMERIC(5, 2),
	discount_amount_cents INTEGER,
	credits_applied INTEGER,
	status VARCHAR(20) NOT NULL,
	id CHAR(32) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(coupon_id) REFERENCES coupons (id),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id),
	FOREIGN KEY(order_id) REFERENCES orders (id),
	FOREIGN KEY(subscription_id) REFERENCES subscriptions (id)
)

CREATE TABLE coupons (
	id CHAR(32) NOT NULL,
	code VARCHAR(32) NOT NULL,
	type VARCHAR(8) NOT NULL,
	discount_percent NUMERIC(5, 2),
	credits INTEGER,
	credits_validity_days INTEGER DEFAULT 30 NOT NULL,
	applies_to VARCHAR(24) DEFAULT 'SUBSCRIPTION_AND_CREDITS' NOT NULL,
	min_purchase_cents BIGINT,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	max_redemptions INTEGER,
	once_per_workspace BOOLEAN DEFAULT false NOT NULL,
	expires_at DATETIME,
	is_active BOOLEAN DEFAULT true NOT NULL,
	internal_note VARCHAR(255),
	created_by CHAR(32),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT chk_coupons_type_exclusive_fields CHECK ((type = 'DISCOUNT' AND discount_percent IS NOT NULL AND credits IS NULL) OR (type = 'CREDIT' AND credits IS NOT NULL AND discount_percent IS NULL)),
	CONSTRAINT chk_coupons_discount_percent CHECK (discount_percent IS NULL OR (discount_percent > 0 AND discount_percent <= 100)),
	CONSTRAINT chk_coupons_min_purchase_nonnegative CHECK (min_purchase_cents IS NULL OR min_purchase_cents >= 0),
	CONSTRAINT chk_coupons_currency_format CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
	CONSTRAINT chk_coupons_code_upper CHECK (code = upper(code)),
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE credit_packages (
	id CHAR(32) NOT NULL,
	name VARCHAR,
	credits INTEGER NOT NULL,
	price_cents BIGINT NOT NULL,
	credits_validity_days INTEGER DEFAULT 30 NOT NULL,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_credit_packages_price_nonnegative CHECK (price_cents >= 0),
	CONSTRAINT chk_credit_packages_currency_format CHECK (currency IS NULL OR currency GLOB '[A-Z][A-Z][A-Z]')
)

CREATE TABLE design_slides (
	id CHAR(32) NOT NULL,
	post_design_id CHAR(32) NOT NULL,
	position INTEGER NOT NULL,
	headline VARCHAR(50),
	subtitle VARCHAR(40),
	cta VARCHAR(30),
	art_direction VARCHAR(1000) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_design_slides_position CHECK (position >= 0),
	FOREIGN KEY(post_design_id) REFERENCES post_designs (id) ON DELETE CASCADE
)

CREATE TABLE fiscal_invoices (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	order_id CHAR(32),
	invoice_id CHAR(32),
	subscription_id CHAR(32),
	number VARCHAR(30),
	series VARCHAR(10),
	access_key VARCHAR(50),
	service_code VARCHAR(20),
	amount_cents BIGINT NOT NULL,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	status VARCHAR(10) DEFAULT 'PENDING' NOT NULL,
	pdf_storage_bucket VARCHAR(63),
	pdf_storage_key VARCHAR(1024),
	xml_storage_bucket VARCHAR(63),
	xml_storage_key VARCHAR(1024),
	error_message VARCHAR,
	issued_at DATETIME,
	canceled_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_fiscal_invoices_one_origin CHECK ((CASE WHEN order_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN invoice_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN subscription_id IS NOT NULL THEN 1 ELSE 0 END) = 1),
	CONSTRAINT chk_fiscal_invoices_amount_nonnegative CHECK (amount_cents >= 0),
	CONSTRAINT chk_fiscal_invoices_currency_format CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE RESTRICT,
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT,
	FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE RESTRICT,
	FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE RESTRICT,
	CONSTRAINT fiscal_invoice_status CHECK (status IN ('PENDING', 'PROCESSING', 'ISSUED', 'CANCELED', 'FAILED'))
)

CREATE TABLE generated_images (
	id CHAR(32) NOT NULL,
	design_slide_id CHAR(32) NOT NULL,
	storage_bucket VARCHAR(63),
	storage_key VARCHAR(1024),
	mime_type VARCHAR(127) DEFAULT 'image/png' NOT NULL,
	size_bytes BIGINT,
	width INTEGER,
	height INTEGER,
	model VARCHAR(50),
	prompt VARCHAR,
	created_by CHAR(32),
	error_message VARCHAR,
	generation_status VARCHAR(10) DEFAULT 'GENERATING' NOT NULL,
	is_current BOOLEAN DEFAULT false NOT NULL,
	approval_status VARCHAR(8) DEFAULT 'PENDING' NOT NULL,
	approved_by CHAR(32),
	approved_at DATETIME,
	rejection_reason VARCHAR(500),
	feedback_type VARCHAR(8),
	feedback_text VARCHAR(1000),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT chk_generated_images_current_complete CHECK (NOT is_current OR (generation_status = 'SUCCEEDED' AND deleted_at IS NULL)),
	CONSTRAINT chk_generated_images_size_bytes CHECK (size_bytes IS NULL OR size_bytes >= 0),
	CONSTRAINT chk_generated_images_dimensions CHECK (width IS NULL OR height IS NULL OR (width > 0 AND height > 0)),
	CONSTRAINT chk_generated_images_approval_pair CHECK ((approved_at IS NULL) = (approved_by IS NULL)),
	CONSTRAINT chk_generated_images_rejected_reason CHECK (approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL),
	CONSTRAINT chk_generated_images_approved_metadata CHECK (approval_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)),
	CONSTRAINT chk_generated_images_approval_after_generation CHECK (approval_status = 'PENDING' OR generation_status = 'SUCCEEDED'),
	CONSTRAINT chk_generated_images_file_by_status CHECK (generation_status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL AND storage_key IS NOT NULL AND size_bytes IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL)),
	CONSTRAINT chk_generated_images_failed_message CHECK (generation_status <> 'FAILED' OR error_message IS NOT NULL),
	FOREIGN KEY(design_slide_id) REFERENCES design_slides (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL,
	CONSTRAINT generation_status CHECK (generation_status IN ('GENERATING', 'SUCCEEDED', 'FAILED')),
	CONSTRAINT approval_status CHECK (approval_status IN ('PENDING', 'APPROVED', 'REJECTED')),
	FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE SET NULL,
	CONSTRAINT image_feedback_type CHECK (feedback_type IN ('POSITIVE', 'NEGATIVE', 'NOT_USED'))
)

CREATE TABLE generation_job_status_events (
	id CHAR(32) NOT NULL,
	generation_job_id CHAR(32) NOT NULL,
	previous_status VARCHAR(10),
	status VARCHAR(10) NOT NULL,
	artifact_type VARCHAR(7) DEFAULT 'IMAGE' NOT NULL,
	version INTEGER DEFAULT 1 NOT NULL,
	correlation_id VARCHAR(255) DEFAULT '' NOT NULL,
	sanitized_result JSON,
	request_id CHAR(32),
	occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_generation_job_status_events_status_changed CHECK (previous_status IS NULL OR previous_status <> status),
	FOREIGN KEY(generation_job_id) REFERENCES generation_jobs (id) ON DELETE CASCADE,
	CONSTRAINT generation_job_status CHECK (previous_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
	CONSTRAINT generation_job_status CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
	CONSTRAINT generation_type CHECK (artifact_type IN ('IMAGE', 'TEXT', 'COPY', 'CAPTION'))
)

CREATE TABLE generation_jobs (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	generation_id CHAR(32) NOT NULL,
	artifact_type VARCHAR(7) DEFAULT 'IMAGE' NOT NULL,
	operation VARCHAR(20) DEFAULT 'CREATE' NOT NULL,
	status VARCHAR(10) DEFAULT 'PENDING' NOT NULL,
	external_id VARCHAR(255),
	attempt_count INTEGER DEFAULT 0 NOT NULL,
	max_attempts INTEGER DEFAULT 1 NOT NULL,
	timeout_seconds INTEGER DEFAULT 300 NOT NULL,
	idempotency_key VARCHAR(255),
	failure_policy VARCHAR(20) DEFAULT 'FAIL' NOT NULL,
	request_id CHAR(32),
	failure_code VARCHAR(100),
	failure_message TEXT,
	queued_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	started_at DATETIME,
	completed_at DATETIME,
	failed_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT fk_generation_jobs_generation_workspace FOREIGN KEY(generation_id, workspace_id) REFERENCES generations (id, workspace_id) ON DELETE CASCADE,
	CONSTRAINT ck_generation_jobs_attempt_count_non_negative CHECK (attempt_count >= 0),
	CONSTRAINT ck_generation_jobs_max_attempts_positive CHECK (max_attempts > 0),
	CONSTRAINT ck_generation_jobs_deleted_after_created CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	CONSTRAINT generation_type CHECK (artifact_type IN ('IMAGE', 'TEXT', 'COPY', 'CAPTION')),
	CONSTRAINT generation_job_status CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'))
)

CREATE TABLE generations (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	content_id CHAR(32) NOT NULL,
	requested_by_user_id CHAR(32),
	brand_id CHAR(32),
	project_id CHAR(32),
	type VARCHAR(7) DEFAULT 'IMAGE' NOT NULL,
	model VARCHAR(255) NOT NULL,
	prompt TEXT NOT NULL,
	parameters JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_generations_id_workspace_id UNIQUE (id, workspace_id),
	CONSTRAINT uq_generations_id_workspace_content_id UNIQUE (id, workspace_id, content_id),
	CONSTRAINT fk_generations_content_workspace FOREIGN KEY(content_id, workspace_id) REFERENCES contents (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_generations_brand_workspace FOREIGN KEY(brand_id, workspace_id) REFERENCES brands (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_generations_project_workspace FOREIGN KEY(project_id, workspace_id) REFERENCES projects (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT ck_generations_prompt_length CHECK (length(prompt) BETWEEN 1 AND 20000),
	CONSTRAINT ck_generations_deleted_after_created CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	FOREIGN KEY(requested_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
	CONSTRAINT generation_type CHECK (type IN ('IMAGE', 'TEXT', 'COPY', 'CAPTION'))
)

CREATE TABLE image_resizes (
	id CHAR(32) NOT NULL,
	source_image_id CHAR(32) NOT NULL,
	ratio VARCHAR(10) NOT NULL,
	status VARCHAR(10) DEFAULT 'PENDING' NOT NULL,
	storage_bucket VARCHAR(63),
	storage_key VARCHAR(1024),
	mime_type VARCHAR(127),
	size_bytes BIGINT,
	width INTEGER,
	height INTEGER,
	error_message VARCHAR,
	created_by CHAR(32),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_image_resizes_file CHECK (status <> 'SUCCEEDED' OR (storage_bucket IS NOT NULL AND storage_key IS NOT NULL AND size_bytes IS NOT NULL AND width IS NOT NULL AND height IS NOT NULL)),
	CONSTRAINT chk_image_resizes_failed CHECK (status <> 'FAILED' OR error_message IS NOT NULL),
	CONSTRAINT chk_image_resizes_size CHECK (size_bytes IS NULL OR size_bytes > 0),
	CONSTRAINT chk_image_resizes_dimensions CHECK ((width IS NULL OR width > 0) AND (height IS NULL OR height > 0)),
	FOREIGN KEY(source_image_id) REFERENCES generated_images (id) ON DELETE CASCADE,
	CONSTRAINT art_ratio CHECK (ratio IN ('RATIO_4_5', 'RATIO_1_1', 'RATIO_9_16', 'RATIO_16_9')),
	CONSTRAINT resize_status CHECK (status IN ('PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED')),
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE images (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	content_id CHAR(32) NOT NULL,
	generation_id CHAR(32),
	version_number INTEGER NOT NULL,
	storage_path VARCHAR(1024) NOT NULL,
	public_url VARCHAR(2048) NOT NULL,
	mime_type VARCHAR(100) NOT NULL,
	width INTEGER NOT NULL,
	height INTEGER NOT NULL,
	model VARCHAR(255),
	prompt TEXT,
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_images_generation_id UNIQUE (generation_id),
	CONSTRAINT uq_images_storage_path UNIQUE (storage_path),
	CONSTRAINT fk_images_content_workspace FOREIGN KEY(content_id, workspace_id) REFERENCES contents (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_images_generation_workspace_content FOREIGN KEY(generation_id, workspace_id, content_id) REFERENCES generations (id, workspace_id, content_id) ON DELETE RESTRICT,
	CONSTRAINT ck_images_version_number_positive CHECK (version_number > 0),
	CONSTRAINT ck_images_mime_type_supported CHECK (mime_type IN ('image/png', 'image/jpeg', 'image/webp')),
	CONSTRAINT ck_images_width_positive CHECK (width > 0),
	CONSTRAINT ck_images_height_positive CHECK (height > 0),
	CONSTRAINT ck_images_prompt_length CHECK (length(prompt) BETWEEN 1 AND 20000),
	CONSTRAINT ck_images_deleted_after_created CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT
)

CREATE TABLE invoices (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	subscription_id CHAR(32) NOT NULL,
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	url VARCHAR,
	amount_cents BIGINT NOT NULL,
	total_discount_cents BIGINT,
	total_increment_cents BIGINT,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	status VARCHAR(9) NOT NULL,
	payment_method VARCHAR(11),
	installments INTEGER,
	billing_at DATETIME,
	seen_at DATETIME,
	due_at DATETIME,
	period_start DATETIME,
	period_end DATETIME,
	canceled_at DATETIME,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_invoices_cents_nonnegative CHECK (amount_cents >= 0 AND (total_discount_cents IS NULL OR total_discount_cents >= 0) AND (total_increment_cents IS NULL OR total_increment_cents >= 0)),
	CONSTRAINT chk_invoices_installments CHECK (installments IS NULL OR installments >= 1),
	CONSTRAINT chk_invoices_currency_format CHECK (currency IS NULL OR currency GLOB '[A-Z][A-Z][A-Z]'),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE RESTRICT,
	FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE RESTRICT
)

CREATE TABLE notification_preferences (
	id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	type VARCHAR(18) NOT NULL,
	channel VARCHAR(6) NOT NULL,
	is_enabled BOOLEAN DEFAULT true NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	CONSTRAINT notification_type CHECK (type IN ('CONTENT_GENERATION', 'CONTENT_APPROVAL', 'INVITE', 'BILLING', 'CREDITS', 'COUPON', 'SYSTEM')),
	CONSTRAINT notification_channel CHECK (channel IN ('EMAIL', 'IN_APP', 'PUSH'))
)

CREATE TABLE notification_recipients (
	id CHAR(32) NOT NULL,
	notification_id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	channel VARCHAR(6) NOT NULL,
	status VARCHAR(7) DEFAULT 'PENDING' NOT NULL,
	external_message_id VARCHAR(128),
	error_message TEXT,
	attempts INTEGER DEFAULT 0 NOT NULL,
	sent_at DATETIME,
	read_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(notification_id) REFERENCES notifications (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	CONSTRAINT notification_channel CHECK (channel IN ('EMAIL', 'IN_APP', 'PUSH')),
	CONSTRAINT notification_delivery_status CHECK (status IN ('PENDING', 'SENT', 'FAILED'))
)

CREATE TABLE notifications (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	type VARCHAR(18) NOT NULL,
	title VARCHAR(150) NOT NULL,
	body VARCHAR(2000),
	payload JSON,
	resource_type VARCHAR(16),
	resource_id CHAR(32),
	dedupe_key VARCHAR(128),
	created_by CHAR(32),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_notifications_resource_pair CHECK ((resource_type IS NULL) = (resource_id IS NULL)),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE,
	CONSTRAINT notification_type CHECK (type IN ('CONTENT_GENERATION', 'CONTENT_APPROVAL', 'INVITE', 'BILLING', 'CREDITS', 'COUPON', 'SYSTEM')),
	CONSTRAINT notification_resource_type CHECK (resource_type IN ('WORKSPACE_INVITE', 'WORKSPACE_MEMBER', 'POST', 'GENERATED_IMAGE', 'SUBSCRIPTION', 'ORDER', 'INVOICE', 'CHARGE', 'COUPON')),
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE orders (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	credit_package_id CHAR(32),
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	code VARCHAR(52),
	subtotal_cents BIGINT NOT NULL,
	discount_cents BIGINT,
	amount_cents BIGINT NOT NULL,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	status VARCHAR(8) NOT NULL,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_orders_amount_consistency CHECK (amount_cents = subtotal_cents - discount_cents),
	CONSTRAINT chk_orders_cents_nonnegative CHECK (subtotal_cents >= 0 AND amount_cents >= 0 AND (discount_cents IS NULL OR discount_cents >= 0)),
	CONSTRAINT chk_orders_currency_format CHECK (currency IS NULL OR currency GLOB '[A-Z][A-Z][A-Z]'),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE RESTRICT,
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	FOREIGN KEY(credit_package_id) REFERENCES credit_packages (id) ON DELETE SET NULL
)

CREATE TABLE outbox_events (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	aggregate_id CHAR(32) NOT NULL,
	event_type VARCHAR(100) NOT NULL,
	event_version VARCHAR(32) NOT NULL,
	payload JSON NOT NULL,
	attempts INTEGER DEFAULT 0 NOT NULL,
	available_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	claimed_at DATETIME,
	claimed_by VARCHAR(64),
	published_at DATETIME,
	last_error TEXT,
	consumer_attempts INTEGER DEFAULT 0 NOT NULL,
	consumer_available_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	consumer_claimed_at DATETIME,
	consumer_claimed_by VARCHAR(64),
	consumed_at DATETIME,
	last_consumer_error TEXT,
	dead_lettered_at DATETIME,
	dead_letter_phase VARCHAR(32),
	dead_letter_reason TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)

CREATE TABLE persona_interests (
	id CHAR(32) NOT NULL,
	persona_id CHAR(32) NOT NULL,
	interest VARCHAR(100) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(persona_id) REFERENCES personas (id) ON DELETE CASCADE
)

CREATE TABLE personas (
	id CHAR(32) NOT NULL,
	created_by CHAR(32),
	brand_id CHAR(32) NOT NULL,
	name VARCHAR(100) NOT NULL,
	age_range VARCHAR(13),
	gender VARCHAR(17),
	main_goal VARCHAR(60),
	challenge VARCHAR(50),
	routine VARCHAR(300),
	journey VARCHAR(250),
	trigger_event VARCHAR(200),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(brand_id) REFERENCES brands (id) ON DELETE CASCADE,
	CONSTRAINT age_range CHECK (age_range IN ('UP_TO_17', 'FROM_18_TO_24', 'FROM_25_TO_34', 'FROM_35_TO_44', 'FROM_45_TO_54', 'FROM_55_TO_64', 'FROM_65_PLUS')),
	CONSTRAINT persona_gender CHECK (gender IN ('MALE', 'FEMALE', 'NON_BINARY', 'OTHER', 'PREFER_NOT_TO_SAY'))
)

CREATE TABLE plan_items (
	id CHAR(32) NOT NULL,
	plan_id CHAR(32) NOT NULL,
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	name VARCHAR(64) NOT NULL,
	description VARCHAR,
	quantity INTEGER DEFAULT 1 NOT NULL,
	cycles INTEGER,
	pricing_scheme_type VARCHAR(9),
	price_cents BIGINT NOT NULL,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	price_brackets JSON,
	status VARCHAR(8) DEFAULT 'ACTIVE' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_plan_items_price_nonnegative CHECK (price_cents IS NULL OR price_cents >= 0),
	CONSTRAINT chk_plan_items_currency_format CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
	FOREIGN KEY(plan_id) REFERENCES plans (id) ON DELETE CASCADE
)

CREATE TABLE plan_payment_methods (
	id CHAR(32) NOT NULL,
	plan_id CHAR(32) NOT NULL,
	method VARCHAR(11) NOT NULL,
	max_installments INTEGER DEFAULT 1 NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_plan_payment_methods_max_installments CHECK (max_installments >= 1),
	FOREIGN KEY(plan_id) REFERENCES plans (id) ON DELETE CASCADE,
	CONSTRAINT payment_method_type CHECK (method IN ('CREDIT_CARD', 'DEBIT_CARD', 'BOLETO', 'PIX'))
)

CREATE TABLE plans (
	id CHAR(32) NOT NULL,
	name VARCHAR(64) NOT NULL,
	type VARCHAR(10) NOT NULL,
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	price_cents BIGINT NOT NULL,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	credits_per_month INTEGER NOT NULL,
	credits_validity_days INTEGER DEFAULT 30 NOT NULL,
	billing_interval VARCHAR(5) DEFAULT 'MONTH' NOT NULL,
	interval_count INTEGER DEFAULT 1 NOT NULL,
	billing_type VARCHAR(8) DEFAULT 'PREPAID' NOT NULL,
	minimum_price_cents BIGINT,
	trial_period_days INTEGER,
	statement_descriptor VARCHAR(22),
	status VARCHAR(8) DEFAULT 'ACTIVE' NOT NULL,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT chk_plans_cents_nonnegative CHECK (price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0)),
	CONSTRAINT chk_plans_currency_format CHECK (currency GLOB '[A-Z][A-Z][A-Z]')
)

CREATE TABLE post_designs (
	id CHAR(32) NOT NULL,
	post_id CHAR(32) NOT NULL,
	format VARCHAR(8) NOT NULL,
	ratio VARCHAR(10) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_post_designs_stories_ratio CHECK (format <> 'STORIES' OR ratio = 'RATIO_9_16'),
	FOREIGN KEY(post_id) REFERENCES posts (id) ON DELETE CASCADE,
	CONSTRAINT content_format CHECK (format IN ('IMAGE', 'CAROUSEL', 'STORIES')),
	CONSTRAINT art_ratio CHECK (ratio IN ('RATIO_4_5', 'RATIO_1_1', 'RATIO_9_16', 'RATIO_16_9'))
)

CREATE TABLE posts (
	id CHAR(32) NOT NULL,
	content_plan_id CHAR(32) NOT NULL,
	created_by CHAR(32),
	title VARCHAR(100),
	objective VARCHAR(300),
	big_idea VARCHAR(150),
	main_message VARCHAR(150),
	publication_status VARCHAR(9) DEFAULT 'DRAFT' NOT NULL,
	approval_status VARCHAR(8) DEFAULT 'PENDING' NOT NULL,
	approved_by CHAR(32),
	approved_at DATETIME,
	rejection_reason VARCHAR(500),
	scheduled_at DATETIME,
	published_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT chk_posts_approval_pair CHECK ((approved_at IS NULL) = (approved_by IS NULL)),
	CONSTRAINT chk_posts_rejected_reason CHECK (approval_status <> 'REJECTED' OR rejection_reason IS NOT NULL),
	CONSTRAINT chk_posts_approved_metadata CHECK (approval_status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)),
	CONSTRAINT chk_posts_scheduled_at CHECK (publication_status <> 'SCHEDULED' OR scheduled_at IS NOT NULL),
	CONSTRAINT chk_posts_published_at CHECK (publication_status <> 'PUBLISHED' OR published_at IS NOT NULL),
	CONSTRAINT chk_posts_publish_requires_approval CHECK (publication_status = 'DRAFT' OR approval_status = 'APPROVED'),
	FOREIGN KEY(content_plan_id) REFERENCES content_plans (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL,
	CONSTRAINT publication_status CHECK (publication_status IN ('DRAFT', 'SCHEDULED', 'PUBLISHED')),
	CONSTRAINT approval_status CHECK (approval_status IN ('PENDING', 'APPROVED', 'REJECTED')),
	FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE projects (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	brand_id CHAR(32),
	created_by_user_id CHAR(32),
	name VARCHAR(255) NOT NULL,
	description TEXT,
	status VARCHAR(32) DEFAULT 'ACTIVE' NOT NULL,
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_projects_id_workspace_id UNIQUE (id, workspace_id),
	CONSTRAINT fk_projects_brand_workspace FOREIGN KEY(brand_id, workspace_id) REFERENCES brands (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT ck_projects_deleted_after_created CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE provider_customers (
	billing_account_id CHAR(32) NOT NULL,
	provider VARCHAR(20) NOT NULL,
	provider_customer_id VARCHAR(64) NOT NULL,
	provider_code VARCHAR(52),
	metadata JSON DEFAULT '{}' NOT NULL,
	id CHAR(32) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id)
)

CREATE TABLE provider_disputes (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32),
	charge_id CHAR(32),
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	status VARCHAR(12) DEFAULT 'OPEN' NOT NULL,
	result VARCHAR(8),
	amount_cents BIGINT,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	reason VARCHAR,
	opened_at DATETIME,
	deadline_at DATETIME,
	resolved_at DATETIME,
	payload JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_provider_disputes_amount_nonnegative CHECK (amount_cents IS NULL OR amount_cents >= 0),
	CONSTRAINT chk_provider_disputes_currency_format CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
	CONSTRAINT chk_provider_disputes_result CHECK ((status = 'RESOLVED') = (result IS NOT NULL)),
	CONSTRAINT chk_provider_disputes_resolved_at CHECK ((status = 'RESOLVED') = (resolved_at IS NOT NULL)),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE RESTRICT,
	FOREIGN KEY(charge_id) REFERENCES charges (id) ON DELETE RESTRICT
)

CREATE TABLE provider_idempotency_keys (
	id CHAR(32) NOT NULL,
	provider VARCHAR(7) NOT NULL,
	idempotency_key VARCHAR(100) NOT NULL,
	request_hash VARCHAR(64),
	resource_type VARCHAR(40),
	resource_id VARCHAR(64),
	status VARCHAR(9) NOT NULL,
	expires_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id)
)

CREATE TABLE provider_subscriptions (
	subscription_id CHAR(32) NOT NULL,
	provider VARCHAR(20) NOT NULL,
	provider_subscription_id VARCHAR(64) NOT NULL,
	provider_status VARCHAR(20),
	payload JSON DEFAULT '{}' NOT NULL,
	id CHAR(32) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(subscription_id) REFERENCES subscriptions (id)
)

CREATE TABLE provider_webhook_events (
	id CHAR(32) NOT NULL,
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64) NOT NULL,
	dedupe_key VARCHAR(128) NOT NULL,
	event_type VARCHAR(60) NOT NULL,
	account_id VARCHAR(64),
	resource_type VARCHAR(40),
	resource_id VARCHAR(64),
	payload JSON NOT NULL,
	signature_verified BOOLEAN DEFAULT false NOT NULL,
	status VARCHAR(10) NOT NULL,
	attempts INTEGER DEFAULT 0 NOT NULL,
	last_error TEXT,
	received_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	processed_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_provider_webhook_events_dedupe_key UNIQUE (dedupe_key)
)

CREATE TABLE refunds (
	id CHAR(32) NOT NULL,
	charge_id CHAR(32) NOT NULL,
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	amount_cents BIGINT NOT NULL,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	reason_code VARCHAR(16),
	status VARCHAR(9) NOT NULL,
	requested_by CHAR(32),
	processed_at DATETIME,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_refunds_amount_nonnegative CHECK (amount_cents >= 0),
	CONSTRAINT chk_refunds_currency_format CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
	CONSTRAINT chk_refunds_processed_by_status CHECK ((status = 'PENDING') = (processed_at IS NULL)),
	FOREIGN KEY(charge_id) REFERENCES charges (id) ON DELETE RESTRICT,
	FOREIGN KEY(requested_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE settings (
	id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	brand_name VARCHAR(255),
	segment VARCHAR(255),
	tone VARCHAR(32) DEFAULT 'professional' NOT NULL,
	voice TEXT DEFAULT 'Clear and useful' NOT NULL,
	visual_style VARCHAR(32) DEFAULT 'photographic' NOT NULL,
	default_preferences JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_settings_user_id UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

CREATE TABLE subscription_history (
	id CHAR(32) NOT NULL,
	subscription_id CHAR(32) NOT NULL,
	change_type VARCHAR(9) NOT NULL,
	old_plan_id CHAR(32),
	new_plan_id CHAR(32),
	old_status VARCHAR(8),
	new_status VARCHAR(8),
	old_provider_status VARCHAR(8),
	new_provider_status VARCHAR(8),
	changed_by CHAR(32),
	reason_code VARCHAR(17),
	reason_text VARCHAR(500),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE,
	FOREIGN KEY(old_plan_id) REFERENCES plans (id) ON DELETE SET NULL,
	FOREIGN KEY(new_plan_id) REFERENCES plans (id) ON DELETE SET NULL,
	FOREIGN KEY(changed_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE subscriptions (
	id CHAR(32) NOT NULL,
	billing_account_id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	plan_id CHAR(32) NOT NULL,
	contracted_price_cents BIGINT NOT NULL,
	currency VARCHAR(3) DEFAULT 'BRL' NOT NULL,
	status VARCHAR(8) NOT NULL,
	provider_status VARCHAR(8),
	status_reason VARCHAR(17),
	provider VARCHAR(7) DEFAULT 'PAGARME' NOT NULL,
	external_id VARCHAR(64),
	external_code VARCHAR(52),
	payment_method VARCHAR(11),
	payment_method_id CHAR(32),
	billing_type VARCHAR(8),
	billing_interval VARCHAR(5),
	interval_count INTEGER,
	installments INTEGER DEFAULT 1 NOT NULL,
	minimum_price_cents BIGINT,
	statement_descriptor VARCHAR(22),
	trial_period_days INTEGER,
	current_cycle_id VARCHAR(64),
	current_period_start DATETIME,
	current_period_end DATETIME,
	next_billing_at DATETIME,
	canceled_at DATETIME,
	metadata JSON,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT chk_subscriptions_installments CHECK (installments IS NULL OR installments >= 1),
	CONSTRAINT chk_subscriptions_cents_nonnegative CHECK (contracted_price_cents >= 0 AND (minimum_price_cents IS NULL OR minimum_price_cents >= 0)),
	CONSTRAINT chk_subscriptions_currency_format CHECK (currency GLOB '[A-Z][A-Z][A-Z]'),
	FOREIGN KEY(billing_account_id) REFERENCES billing_accounts (id) ON DELETE RESTRICT,
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	FOREIGN KEY(plan_id) REFERENCES plans (id) ON DELETE RESTRICT,
	FOREIGN KEY(payment_method_id) REFERENCES billing_payment_methods (id) ON DELETE SET NULL
)

CREATE TABLE user_consents (
	id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	type VARCHAR(24) NOT NULL,
	document_version VARCHAR(20) NOT NULL,
	granted BOOLEAN DEFAULT true NOT NULL,
	granted_at DATETIME,
	revoked_at DATETIME,
	ip_address VARCHAR(45),
	user_agent VARCHAR(255),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT consent_type CHECK (type IN ('TERMS_OF_USE', 'PRIVACY_POLICY', 'MARKETING_COMMUNICATIONS'))
)

CREATE TABLE user_devices (
	id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	platform VARCHAR(7) NOT NULL,
	fcm_token VARCHAR(255) NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	last_seen_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_user_devices_fcm_token UNIQUE (fcm_token),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	CONSTRAINT device_platform CHECK (platform IN ('IOS', 'ANDROID', 'WEB'))
)

CREATE TABLE users (
	id CHAR(32) NOT NULL,
	auth_provider_id VARCHAR,
	email VARCHAR(254),
	password_hash VARCHAR(255),
	display_name VARCHAR(50) NOT NULL,
	bio VARCHAR(350),
	avatar_url VARCHAR,
	global_role VARCHAR(6) DEFAULT 'membro' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT global_role CHECK (global_role IN ('admin', 'gestor', 'membro'))
)

CREATE TABLE workspace_credit_lot_consumptions (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	lot_id CHAR(32) NOT NULL,
	transaction_id CHAR(32) NOT NULL,
	amount INTEGER NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_lot_consumptions_lot FOREIGN KEY(lot_id, workspace_id) REFERENCES workspace_credit_lots (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT fk_lot_consumptions_transaction FOREIGN KEY(transaction_id, workspace_id) REFERENCES workspace_credit_transactions (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT chk_lot_consumptions_amount CHECK (amount > 0)
)

CREATE TABLE workspace_credit_lots (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	grant_transaction_id CHAR(32) NOT NULL,
	original_amount INTEGER NOT NULL,
	remaining_amount INTEGER NOT NULL,
	expires_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_credit_lots_grant_transaction FOREIGN KEY(grant_transaction_id, workspace_id) REFERENCES workspace_credit_transactions (id, workspace_id) ON DELETE RESTRICT,
	CONSTRAINT chk_credit_lots_amounts CHECK (original_amount > 0 AND remaining_amount >= 0 AND remaining_amount <= original_amount),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT,
	UNIQUE (grant_transaction_id)
)

CREATE TABLE workspace_credit_transactions (
	workspace_id CHAR(32) NOT NULL,
	amount INTEGER NOT NULL,
	transaction_type VARCHAR(30) NOT NULL,
	reference_type VARCHAR(40),
	reference_id CHAR(32),
	id CHAR(32) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
)

CREATE TABLE workspace_invite_usages (
	id CHAR(32) NOT NULL,
	invite_id CHAR(32) NOT NULL,
	member_id CHAR(32) NOT NULL,
	used_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(invite_id) REFERENCES workspace_invites (id) ON DELETE CASCADE,
	FOREIGN KEY(member_id) REFERENCES workspace_members (id) ON DELETE CASCADE
)

CREATE TABLE workspace_invites (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	type VARCHAR(5) NOT NULL,
	role VARCHAR(7) NOT NULL,
	email VARCHAR(254),
	token_hash VARCHAR(64) NOT NULL,
	max_uses INTEGER,
	status VARCHAR(8) DEFAULT 'PENDING' NOT NULL,
	created_by CHAR(32) NOT NULL,
	expires_at DATETIME,
	last_used_at DATETIME,
	revoked_at DATETIME,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_workspace_invites_token_hash UNIQUE (token_hash),
	CONSTRAINT chk_workspace_invites_email_by_type CHECK ((type = 'EMAIL') = (email IS NOT NULL)),
	CONSTRAINT chk_workspace_invites_max_uses_by_type CHECK ((type = 'LINK') = (max_uses IS NOT NULL)),
	CONSTRAINT chk_workspace_invites_max_uses_positive CHECK (max_uses IS NULL OR max_uses >= 1),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE,
	CONSTRAINT invite_type CHECK (type IN ('EMAIL', 'LINK')),
	CONSTRAINT workspace_role CHECK (role IN ('OWNER', 'MANAGER', 'EDITOR', 'VIEWER')),
	CONSTRAINT invite_status CHECK (status IN ('PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED')),
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
)

CREATE TABLE workspace_members (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	user_id CHAR(32) NOT NULL,
	role VARCHAR(7) NOT NULL,
	status VARCHAR(9) DEFAULT 'ACTIVE' NOT NULL,
	invited_by CHAR(32),
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
	CONSTRAINT workspace_role CHECK (role IN ('OWNER', 'MANAGER', 'EDITOR', 'VIEWER')),
	CONSTRAINT member_status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REMOVED')),
	FOREIGN KEY(invited_by) REFERENCES users (id) ON DELETE SET NULL
)

CREATE TABLE workspaces (
	id CHAR(32) NOT NULL,
	name VARCHAR(50) NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id)
)

CREATE INDEX ix_activity_events_brand ON activity_events (brand_id)

CREATE INDEX ix_activity_events_entity ON activity_events (entity_type, entity_id)

CREATE INDEX ix_activity_events_user ON activity_events (user_id)

CREATE INDEX ix_activity_events_workspace_created ON activity_events (workspace_id, created_at, id)

CREATE INDEX ix_agent_workflow_runs_workspace_status_created ON agent_workflow_runs (workspace_id, status, created_at)

CREATE INDEX ix_agent_workflow_steps_run_sequence ON agent_workflow_steps (run_id, sequence_number)

CREATE INDEX ix_agent_workflow_steps_source_event ON agent_workflow_steps (source_event_id)

CREATE UNIQUE INDEX uq_agent_workflow_steps_completed_source_role_item ON agent_workflow_steps (source_event_id, role, stage_item) WHERE status = 'COMPLETED' AND source_event_id IS NOT NULL

CREATE INDEX ix_assets_brand_id ON assets (brand_id)

CREATE INDEX ix_assets_content_id ON assets (content_id)

CREATE INDEX ix_assets_project_id ON assets (project_id)

CREATE INDEX ix_assets_workspace_filter ON assets (workspace_id, deleted_at, created_at)

CREATE INDEX ix_audit_logs_action_created_at ON audit_logs (action, created_at)

CREATE INDEX ix_audit_logs_actor_id_created_at ON audit_logs (actor_id, created_at)

CREATE INDEX ix_audit_logs_entity_type_entity_id_created_at ON audit_logs (entity_type, entity_id, created_at)

CREATE INDEX ix_audit_logs_workspace_id_created_at ON audit_logs (workspace_id, created_at)

CREATE INDEX ix_auth_sessions_absolute_expires_at ON auth_sessions (absolute_expires_at)

CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at)

CREATE INDEX ix_auth_sessions_family_id ON auth_sessions (family_id)

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id)

CREATE INDEX ix_billing_accounts_document_hash ON billing_accounts (document_hash)

CREATE INDEX ix_billing_accounts_user_id ON billing_accounts (user_id)

CREATE UNIQUE INDEX uq_billing_accounts_provider_external_id ON billing_accounts (provider, external_id)

CREATE INDEX ix_billing_addresses_billing_account_id ON billing_addresses (billing_account_id)

CREATE UNIQUE INDEX uq_billing_addresses_default ON billing_addresses (billing_account_id) WHERE is_default AND status = 'ACTIVE'

CREATE INDEX idx_m8_billing_payment_methods_billing_address_id ON billing_payment_methods (billing_address_id) WHERE billing_address_id IS NOT NULL

CREATE INDEX ix_billing_payment_methods_account_default ON billing_payment_methods (billing_account_id, is_default)

CREATE UNIQUE INDEX uq_billing_payment_methods_account_external_id ON billing_payment_methods (billing_account_id, external_id)

CREATE UNIQUE INDEX uq_billing_payment_methods_default ON billing_payment_methods (billing_account_id) WHERE is_default AND status = 'ACTIVE'

CREATE INDEX ix_brand_assets_brand_id ON brand_assets (brand_id)

CREATE INDEX ix_brand_assets_created_by ON brand_assets (created_by)

CREATE UNIQUE INDEX uq_brand_assets_storage_bucket_storage_key ON brand_assets (storage_bucket, storage_key)

CREATE INDEX idx_m8_brand_business_details_campaign_id_brand_id ON brand_business_details (campaign_id, brand_id)

CREATE INDEX idx_m8_brand_business_details_created_by ON brand_business_details (created_by) WHERE created_by IS NOT NULL

CREATE INDEX idx_m8_brand_business_details_persona_id_brand_id ON brand_business_details (persona_id, brand_id)

CREATE INDEX ix_brand_business_details_brand_id_campaign_id_persona_id ON brand_business_details (brand_id, campaign_id, persona_id)

CREATE INDEX ix_brand_business_details_created_at ON brand_business_details (created_at)

CREATE INDEX ix_brand_colors_brand_id ON brand_colors (brand_id)

CREATE UNIQUE INDEX uq_brand_hashtags_brand_id_hashtag ON brand_hashtags (brand_id, hashtag)

CREATE INDEX ix_brand_settings_workspace_id ON brand_settings (workspace_id)

CREATE UNIQUE INDEX uq_brand_values_brand_id_value ON brand_values (brand_id, value)

CREATE INDEX idx_m8_brands_created_by ON brands (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_brands_workspace_id ON brands (workspace_id)

CREATE UNIQUE INDEX uq_campaign_hashtags_campaign_id_hashtag ON campaign_hashtags (campaign_id, hashtag)

CREATE UNIQUE INDEX uq_campaign_voices_campaign_id_voice ON campaign_voices (campaign_id, voice)

CREATE INDEX idx_m8_campaigns_created_by ON campaigns (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_campaigns_brand_id ON campaigns (brand_id)

CREATE UNIQUE INDEX uq_campaigns_id_brand_id ON campaigns (id, brand_id)

CREATE INDEX idx_m8_captions_created_by ON captions (created_by) WHERE created_by IS NOT NULL

CREATE UNIQUE INDEX uq_captions_current ON captions (post_id) WHERE is_current

CREATE UNIQUE INDEX uq_captions_post_id_version ON captions (post_id, version)

CREATE INDEX idx_charge_transactions_latest ON charge_transactions (charge_id, created_at, id)

CREATE INDEX ix_charge_transactions_created_at ON charge_transactions (created_at)

CREATE INDEX ix_charge_transactions_status ON charge_transactions (status)

CREATE UNIQUE INDEX uq_charge_transactions_charge_provider_external ON charge_transactions (charge_id, provider, external_id)

CREATE INDEX idx_m8_charges_payment_method_id ON charges (payment_method_id) WHERE payment_method_id IS NOT NULL

CREATE INDEX ix_charges_billing_account_status ON charges (billing_account_id, status)

CREATE INDEX ix_charges_code ON charges (code)

CREATE INDEX ix_charges_invoice_id ON charges (invoice_id)

CREATE INDEX ix_charges_order_id ON charges (order_id)

CREATE INDEX ix_charges_paid_at ON charges (paid_at)

CREATE INDEX ix_charges_status ON charges (status)

CREATE UNIQUE INDEX uq_charges_provider_external_id ON charges (provider, external_id)

CREATE UNIQUE INDEX uq_content_plan_items_content_plan_id_format ON content_plan_items (content_plan_id, format)

CREATE UNIQUE INDEX uq_content_plan_special_dates_plan_date_label ON content_plan_special_dates (content_plan_id, special_date, label)

CREATE INDEX idx_m8_content_plans_campaign_id_brand_id ON content_plans (campaign_id, brand_id)

CREATE INDEX idx_m8_content_plans_created_by ON content_plans (created_by) WHERE created_by IS NOT NULL

CREATE INDEX idx_m8_content_plans_persona_id_brand_id ON content_plans (persona_id, brand_id)

CREATE INDEX ix_content_plans_brand_id ON content_plans (brand_id)

CREATE INDEX ix_content_plans_campaign_id ON content_plans (campaign_id)

CREATE INDEX ix_content_plans_persona_id ON content_plans (persona_id)

CREATE INDEX ix_content_text_versions_content_version ON content_text_versions (content_id, version_number)

CREATE INDEX ix_contents_created_by_user_id ON contents (created_by_user_id)

CREATE INDEX ix_contents_workspace_created_id ON contents (workspace_id, deleted_at, created_at, id)

CREATE INDEX ix_contents_workspace_filter ON contents (workspace_id, type, deleted_at, created_at)

CREATE INDEX idx_m8_coupons_created_by ON coupons (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_coupons_is_active ON coupons (is_active)

CREATE INDEX ix_coupons_type ON coupons (type)

CREATE UNIQUE INDEX uq_coupons_code_active ON coupons (code) WHERE deleted_at IS NULL

CREATE UNIQUE INDEX uq_design_slides_post_design_id_position ON design_slides (post_design_id, position)

CREATE INDEX ix_fiscal_invoices_billing_account_id ON fiscal_invoices (billing_account_id)

CREATE INDEX ix_fiscal_invoices_invoice_id ON fiscal_invoices (invoice_id)

CREATE INDEX ix_fiscal_invoices_order_id ON fiscal_invoices (order_id)

CREATE INDEX ix_fiscal_invoices_status ON fiscal_invoices (status)

CREATE INDEX ix_fiscal_invoices_subscription_id ON fiscal_invoices (subscription_id)

CREATE UNIQUE INDEX uq_fiscal_invoices_access_key ON fiscal_invoices (access_key) WHERE access_key IS NOT NULL

CREATE UNIQUE INDEX uq_fiscal_invoices_number_series_account ON fiscal_invoices (billing_account_id, series, number) WHERE series IS NOT NULL AND number IS NOT NULL

CREATE INDEX idx_m8_generated_images_created_by ON generated_images (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_generated_images_approval_status ON generated_images (approval_status)

CREATE INDEX ix_generated_images_approved_by ON generated_images (approved_by)

CREATE INDEX ix_generated_images_design_slide_id ON generated_images (design_slide_id)

CREATE INDEX ix_generated_images_generation_status ON generated_images (generation_status)

CREATE UNIQUE INDEX uq_generated_images_current_per_slide ON generated_images (design_slide_id) WHERE is_current AND deleted_at IS NULL

CREATE UNIQUE INDEX uq_generated_images_storage_bucket_storage_key ON generated_images (storage_bucket, storage_key)

CREATE INDEX ix_generation_job_status_events_job_occurred_at ON generation_job_status_events (generation_job_id, occurred_at)

CREATE INDEX ix_generation_jobs_generation_id ON generation_jobs (generation_id)

CREATE INDEX ix_generation_jobs_status_created_at ON generation_jobs (status, created_at)

CREATE INDEX ix_generation_jobs_workspace_status_created_at ON generation_jobs (workspace_id, status, created_at)

CREATE UNIQUE INDEX uq_generation_jobs_external_id ON generation_jobs (external_id) WHERE external_id IS NOT NULL

CREATE INDEX ix_generations_requested_by_user_id ON generations (requested_by_user_id)

CREATE INDEX ix_generations_workspace_filter ON generations (workspace_id, type, deleted_at, created_at)

CREATE INDEX idx_image_resizes_created_by ON image_resizes (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_image_resizes_source_image_id ON image_resizes (source_image_id)

CREATE UNIQUE INDEX uq_image_resizes_storage_bucket_storage_key ON image_resizes (storage_bucket, storage_key)

CREATE INDEX ix_images_content_version ON images (content_id, version_number)

CREATE INDEX ix_images_workspace_filter ON images (workspace_id, deleted_at, created_at)

CREATE UNIQUE INDEX uq_images_active_content_version ON images (content_id, version_number) WHERE deleted_at IS NULL

CREATE INDEX ix_invoices_billing_account_id ON invoices (billing_account_id)

CREATE INDEX ix_invoices_status_due_at ON invoices (status, due_at)

CREATE INDEX ix_invoices_subscription_id_due_at ON invoices (subscription_id, due_at)

CREATE UNIQUE INDEX uq_invoices_provider_external_id ON invoices (provider, external_id)

CREATE UNIQUE INDEX uq_notification_preferences_user_type_channel ON notification_preferences (user_id, type, channel)

CREATE INDEX ix_notification_recipients_user_channel ON notification_recipients (user_id, channel)

CREATE INDEX ix_notification_recipients_user_created_at ON notification_recipients (user_id, created_at)

CREATE INDEX ix_notification_recipients_user_read_at ON notification_recipients (user_id, read_at)

CREATE UNIQUE INDEX uq_notification_recipients_notification_user_channel ON notification_recipients (notification_id, user_id, channel)

CREATE INDEX idx_m8_notifications_created_by ON notifications (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_notifications_created_at ON notifications (created_at)

CREATE INDEX ix_notifications_type ON notifications (type)

CREATE UNIQUE INDEX uq_notifications_workspace_dedupe ON notifications (workspace_id, dedupe_key)

CREATE INDEX idx_m8_orders_credit_package_id ON orders (credit_package_id) WHERE credit_package_id IS NOT NULL

CREATE INDEX ix_orders_billing_account_id ON orders (billing_account_id)

CREATE INDEX ix_orders_status ON orders (status)

CREATE INDEX ix_orders_workspace_id ON orders (workspace_id)

CREATE UNIQUE INDEX uq_orders_id_workspace_id ON orders (id, workspace_id)

CREATE UNIQUE INDEX uq_orders_provider_external_id ON orders (provider, external_id)

CREATE INDEX ix_outbox_events_consume ON outbox_events (consumed_at, consumer_available_at, dead_lettered_at)

CREATE INDEX ix_outbox_events_dispatch ON outbox_events (published_at, available_at)

CREATE INDEX ix_outbox_events_workspace ON outbox_events (workspace_id, created_at)

CREATE UNIQUE INDEX uq_persona_interests_persona_id_interest ON persona_interests (persona_id, interest)

CREATE INDEX idx_m8_personas_created_by ON personas (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_personas_brand_id ON personas (brand_id)

CREATE UNIQUE INDEX uq_personas_id_brand_id ON personas (id, brand_id)

CREATE INDEX idx_m8_plan_items_plan_id ON plan_items (plan_id)

CREATE UNIQUE INDEX uq_plan_items_provider_external_id ON plan_items (provider, external_id)

CREATE UNIQUE INDEX uq_plan_payment_methods_plan_id_method ON plan_payment_methods (plan_id, method)

CREATE UNIQUE INDEX uq_plans_provider_external_id ON plans (provider, external_id)

CREATE INDEX ix_post_designs_post_id ON post_designs (post_id)

CREATE INDEX idx_m8_posts_created_by ON posts (created_by) WHERE created_by IS NOT NULL

CREATE INDEX ix_posts_approval_status ON posts (approval_status)

CREATE INDEX ix_posts_approved_by ON posts (approved_by)

CREATE INDEX ix_posts_content_plan_id_created_at ON posts (content_plan_id, created_at)

CREATE INDEX ix_posts_content_plan_id_publication_status ON posts (content_plan_id, publication_status)

CREATE INDEX ix_posts_publication_status ON posts (publication_status)

CREATE INDEX ix_posts_scheduled_at ON posts (scheduled_at)

CREATE INDEX ix_projects_brand_id ON projects (brand_id)

CREATE INDEX ix_projects_created_by_user_id ON projects (created_by_user_id)

CREATE INDEX ix_projects_workspace_filter ON projects (workspace_id, deleted_at, created_at)

CREATE INDEX idx_m8_provider_disputes_billing_account_id ON provider_disputes (billing_account_id) WHERE billing_account_id IS NOT NULL

CREATE INDEX ix_provider_disputes_charge_id ON provider_disputes (charge_id)

CREATE INDEX ix_provider_disputes_status_resolved_at ON provider_disputes (status, resolved_at)

CREATE UNIQUE INDEX uq_provider_disputes_provider_external_id ON provider_disputes (provider, external_id)

CREATE INDEX ix_provider_idempotency_keys_expires_at ON provider_idempotency_keys (expires_at)

CREATE UNIQUE INDEX uq_provider_idempotency_keys_provider_key ON provider_idempotency_keys (provider, idempotency_key)

CREATE INDEX ix_provider_webhook_events_event_type ON provider_webhook_events (event_type)

CREATE INDEX ix_provider_webhook_events_resource_id ON provider_webhook_events (resource_id)

CREATE INDEX ix_provider_webhook_events_status_received_at ON provider_webhook_events (status, received_at)

CREATE UNIQUE INDEX uq_provider_webhook_events_provider_external_id ON provider_webhook_events (provider, external_id)

CREATE INDEX idx_m8_refunds_requested_by ON refunds (requested_by) WHERE requested_by IS NOT NULL

CREATE INDEX ix_refunds_charge_id ON refunds (charge_id)

CREATE INDEX ix_refunds_status ON refunds (status)

CREATE UNIQUE INDEX uq_refunds_provider_external_id ON refunds (provider, external_id)

CREATE INDEX ix_settings_user_id ON settings (user_id)

CREATE INDEX idx_m8_subscription_history_changed_by ON subscription_history (changed_by) WHERE changed_by IS NOT NULL

CREATE INDEX idx_m8_subscription_history_new_plan_id ON subscription_history (new_plan_id) WHERE new_plan_id IS NOT NULL

CREATE INDEX idx_m8_subscription_history_old_plan_id ON subscription_history (old_plan_id) WHERE old_plan_id IS NOT NULL

CREATE INDEX ix_subscription_history_subscription_created ON subscription_history (subscription_id, created_at)

CREATE INDEX idx_m8_subscriptions_payment_method_id ON subscriptions (payment_method_id) WHERE payment_method_id IS NOT NULL

CREATE INDEX idx_m8_subscriptions_plan_id ON subscriptions (plan_id)

CREATE INDEX ix_subscriptions_billing_account_id ON subscriptions (billing_account_id)

CREATE INDEX ix_subscriptions_next_billing_at ON subscriptions (next_billing_at)

CREATE INDEX ix_subscriptions_workspace_id ON subscriptions (workspace_id)

CREATE UNIQUE INDEX uq_subscriptions_id_workspace_id ON subscriptions (id, workspace_id)

CREATE UNIQUE INDEX uq_subscriptions_provider_external_id ON subscriptions (provider, external_id)

CREATE UNIQUE INDEX uq_subscriptions_workspace_current ON subscriptions (workspace_id) WHERE status IN ('ACTIVE', 'TRIALING', 'PAST_DUE')

CREATE UNIQUE INDEX uq_user_consents_user_id_type_document_version ON user_consents (user_id, type, document_version)

CREATE INDEX ix_user_devices_user_id ON user_devices (user_id)

CREATE UNIQUE INDEX uq_users_email_active ON users (email) WHERE deleted_at IS NULL

CREATE INDEX idx_m8_lot_consumptions_transaction_workspace ON workspace_credit_lot_consumptions (transaction_id, workspace_id)

CREATE INDEX idx_m8_workspace_credit_lot_consumptions_lot_id_workspace_id ON workspace_credit_lot_consumptions (lot_id, workspace_id)

CREATE INDEX ix_workspace_credit_lot_consumptions_transaction_id ON workspace_credit_lot_consumptions (transaction_id)

CREATE UNIQUE INDEX uq_workspace_credit_lot_consumptions_lot_id_transaction_id ON workspace_credit_lot_consumptions (lot_id, transaction_id)

CREATE INDEX idx_m8_workspace_credit_lots_grant_transaction_id_workspace_id ON workspace_credit_lots (grant_transaction_id, workspace_id)

CREATE INDEX ix_workspace_credit_lots_workspace_id_expires_at ON workspace_credit_lots (workspace_id, expires_at)

CREATE UNIQUE INDEX uq_credit_lots_id_workspace ON workspace_credit_lots (id, workspace_id)

CREATE UNIQUE INDEX uq_credit_tx_id_workspace ON workspace_credit_transactions (id, workspace_id)

CREATE INDEX ix_workspace_invite_usages_member_id ON workspace_invite_usages (member_id)

CREATE UNIQUE INDEX uq_workspace_invite_usages_invite_member ON workspace_invite_usages (invite_id, member_id)

CREATE INDEX idx_m8_workspace_invites_created_by ON workspace_invites (created_by)

CREATE INDEX ix_workspace_invites_email ON workspace_invites (email)

CREATE INDEX ix_workspace_invites_status ON workspace_invites (status)

CREATE INDEX ix_workspace_invites_workspace_id ON workspace_invites (workspace_id)

CREATE INDEX ix_workspace_members_invited_by ON workspace_members (invited_by)

CREATE INDEX ix_workspace_members_user_id ON workspace_members (user_id)

CREATE INDEX ix_workspace_members_workspace_id_role ON workspace_members (workspace_id, role)

CREATE UNIQUE INDEX uq_workspace_members_workspace_user ON workspace_members (workspace_id, user_id)

CREATE INDEX ix_workspaces_deleted_at ON workspaces (deleted_at)
