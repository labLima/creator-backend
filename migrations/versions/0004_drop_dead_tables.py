"""Drop persistence artifacts that no route, repository or service can reach.

The credit ledger in `credits.py` was superseded by `workspace_credit_transactions`
(ADR-0019); the brand knowledge tables predate the retrieval adapter (ADR-0012)
and were never wired to a repository. Both were only imported by
`models/__init__.py` and asserted in `tests/test_models.py`.

`downgrade()` re-creates the original DDL verbatim, so a rollback preserves the
shape of any rows an exploratory environment may still hold.

Revision ID: 0004_drop_dead_tables
Revises: 0003_auth_session_rotation
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_drop_dead_tables"
down_revision = "0003_auth_session_rotation"
branch_labels = None
depends_on = None

# Children first: chunks reference documents.
DROP_ORDER = (
    "brand_knowledge_chunks",
    "brand_knowledge_documents",
    "credit_transactions",
    "credit_prices",
    "credit_wallets",
)

RECREATE_SQL = (
    """CREATE TABLE brand_knowledge_documents (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	title VARCHAR(255) NOT NULL,
	source VARCHAR(2000) NOT NULL,
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_bk_documents_scope UNIQUE (id, workspace_id, brand_id),
	CONSTRAINT fk_bk_documents_brand_workspace FOREIGN KEY(brand_id, workspace_id)
		REFERENCES brands (id, workspace_id) ON DELETE CASCADE,
	CONSTRAINT ck_bk_documents_deleted_after_created
		CHECK (deleted_at IS NULL OR deleted_at >= created_at),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)""",
    """CREATE TABLE brand_knowledge_chunks (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	brand_id CHAR(32) NOT NULL,
	document_id CHAR(32) NOT NULL,
	content TEXT NOT NULL,
	embedding JSON NOT NULL,
	chunk_index INTEGER NOT NULL,
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_bk_chunks_document_scope FOREIGN KEY(document_id, workspace_id, brand_id)
		REFERENCES brand_knowledge_documents (id, workspace_id, brand_id) ON DELETE CASCADE,
	CONSTRAINT uq_bk_chunks_document_index UNIQUE (document_id, chunk_index),
	CONSTRAINT ck_bk_chunks_index_nonnegative CHECK (chunk_index >= 0),
	CONSTRAINT ck_bk_chunks_embedding_array CHECK (json_type(embedding) = 'array'),
	CONSTRAINT ck_bk_chunks_metadata_object CHECK (json_type(metadata) = 'object'),
	CONSTRAINT ck_bk_chunks_content_length CHECK (length(content) BETWEEN 1 AND 100000),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)""",
    """CREATE TABLE credit_wallets (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	balance INTEGER DEFAULT '0' NOT NULL,
	monthly_allowance INTEGER DEFAULT '0' NOT NULL,
	purchased_credits INTEGER DEFAULT '0' NOT NULL,
	total_spent INTEGER DEFAULT '0' NOT NULL,
	cycle_started_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_credit_wallets_workspace_id UNIQUE (workspace_id),
	CONSTRAINT ck_credit_wallets_balance_nonnegative CHECK (balance >= 0),
	CONSTRAINT ck_credit_wallets_allowance_nonnegative CHECK (monthly_allowance >= 0),
	CONSTRAINT ck_credit_wallets_purchased_nonnegative CHECK (purchased_credits >= 0),
	CONSTRAINT ck_credit_wallets_spent_nonnegative CHECK (total_spent >= 0),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
)""",
    """CREATE TABLE credit_prices (
	id CHAR(32) NOT NULL,
	action_key VARCHAR(100) NOT NULL,
	category VARCHAR(50) NOT NULL,
	credits INTEGER NOT NULL,
	description VARCHAR(500),
	active BOOLEAN DEFAULT 'true' NOT NULL,
	metadata JSON DEFAULT '{}' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_credit_prices_action_key UNIQUE (action_key),
	CONSTRAINT ck_credit_prices_credits_positive CHECK (credits > 0)
)""",
    """CREATE TABLE credit_transactions (
	id CHAR(32) NOT NULL,
	workspace_id CHAR(32) NOT NULL,
	user_id CHAR(32),
	action_key VARCHAR(100) NOT NULL,
	credits INTEGER NOT NULL,
	quantity INTEGER DEFAULT '1' NOT NULL,
	balance_after INTEGER NOT NULL,
	idempotency_key VARCHAR(255),
	metadata JSON DEFAULT '{}' NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_credit_transactions_workspace_idempotency
		UNIQUE (workspace_id, idempotency_key),
	CONSTRAINT ck_credit_transactions_credits_nonzero CHECK (credits <> 0),
	CONSTRAINT ck_credit_transactions_quantity_positive CHECK (quantity > 0),
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
)""",
)


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()
    for table in DROP_ORDER:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    existing = _existing_tables()
    for statement in RECREATE_SQL:
        table = statement.split("(", 1)[0].split()[-1]
        if table not in existing:
            op.execute(statement)
