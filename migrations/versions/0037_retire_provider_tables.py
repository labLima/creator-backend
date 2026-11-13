"""Retire the provider cache tables (T16, issue #164, ADR-031).

`provider_customers` and `provider_subscriptions` were the only two tables the
metadata carried without a target in ``Creator_DB_final.sql``. ADR-031 removes
them: the final modeling stores the provider identifier on the business entity
itself (``billing_accounts.external_id``/``external_code`` and
``subscriptions.external_id``/``external_code``) and keeps only the auditables
provider facts — ``provider_webhook_events``, ``provider_idempotency_keys`` and
``provider_disputes``, which this revision does not touch.

This is a *contract* step (ADR-030, decision 3). The upgrade drops the two tables
and nothing else; no other table declares a foreign key to either of them, so the
schema stays reference-clean (``PRAGMA foreign_key_check`` empty).

The downgrade recreates the previous shape **empty**: same columns in the same
order, same nullability, ``metadata JSON DEFAULT '{}'``, ``payload JSON DEFAULT
'{}'``, ``deleted_at``, ``CHAR(32)`` primary key and the previous foreign keys
with the default ``ON DELETE NO ACTION``. The dropped rows do **not** come back —
the loss of the provider cache is documented in ADR-031 and recovery depends on a
backup, never on the downgrade.

Both directions are guarded by an inspector so re-running against a partly built
database cannot fail on a missing (or already present) table.
"""

from typing import Final

import sqlalchemy as sa
from alembic import op

revision = "0037_retire_provider_tables"
down_revision = "0036_storage_objects"
branch_labels = None
depends_on = None

PROVIDER_CUSTOMERS = "provider_customers"
PROVIDER_SUBSCRIPTIONS = "provider_subscriptions"
RETIRED_TABLES: Final[tuple[str, ...]] = (PROVIDER_CUSTOMERS, PROVIDER_SUBSCRIPTIONS)

# Parent tables each recreated table needs. The downgrade only runs after this
# revision's own upgrade, so the parents exist; the guard is for a partly built
# database, where creating an orphan foreign key would be worse than a no-op.
_PARENTS: Final[dict[str, tuple[str, ...]]] = {
    PROVIDER_CUSTOMERS: ("billing_accounts",),
    PROVIDER_SUBSCRIPTIONS: ("subscriptions",),
}

# Exact DDL of the two tables at `0036_storage_objects`, read back from a database
# upgraded to that revision (`PRAGMA table_info` and `sqlite_master.sql`). Column
# order, defaults, the primary key and the foreign keys are part of the shape the
# downgrade restores, so the statements are literal: migrations are frozen
# history, and importing the live model would rewrite the past.
_CREATE_DDL: Final[dict[str, str]] = {
    PROVIDER_CUSTOMERS: """
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
    """,
    PROVIDER_SUBSCRIPTIONS: """
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
    """,
}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    for table in RETIRED_TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    existing = _tables()
    for table in RETIRED_TABLES:
        if table in existing:
            continue
        if not set(_PARENTS[table]) <= existing:
            continue
        op.execute(_CREATE_DDL[table])
