"""Port the storage objects of the final modeling to SQLite (T20, issue #163).

The final modeling keeps part of the business rules in the database. ADR-030
decision 12 requires every function, trigger and view to be classified object by
object in ``docs/migration/storage-objects-matrix.md``: ported as a SQLite
trigger, moved to the application with an equivalent test, or declared out of
scope with a written risk. This revision carries the ported ones.

Ported as SQLite triggers (the invariants that may not depend on discipline):

- the append-only Credit Transaction ledger (ADR-019): ``UPDATE`` and ``DELETE``
  are both refused. A correction is a new movement;
- the immutable Credit Lot consumption: an allocation ties a debit to a lot, so
  rewriting it would break the audit trail;
- the Credit Lot itself: it may be deleted never and updated only in
  ``remaining_amount``/``updated_at``, and ``remaining_amount`` may only shrink.
  The PostgreSQL function compares the whole row with ``to_jsonb(OLD)``; SQLite
  has no row subtraction, so the immutable columns are compared one by one. A
  column added to ``workspace_credit_lots`` later has to be added here too, which
  is recorded as the residual risk of the object;
- the birth of a Credit Lot (``m1_validate_credit_lot``): a ``BEFORE INSERT``
  trigger requires the grant transaction to exist in the same Workspace, to be
  positive, and to match ``original_amount``, with ``remaining_amount`` equal to
  ``original_amount``. Without it a lot could be created with no grant at all, or
  claiming an amount its transaction never granted;
- the append-only ``subscription_history``: a plan or status change is a new
  event, never a rewrite;
- the ``coupon_redemptions`` snapshot. The PostgreSQL function *assigns*
  ``NEW.once_per_workspace`` from the coupon; SQLite cannot assign ``NEW`` inside
  a trigger, so the port refuses a row whose snapshot disagrees with
  ``coupons.once_per_workspace`` instead of silently rewriting it. Refusing is
  the fail-closed choice: a caller that forgets the column gets an error naming
  it, not a wrong snapshot.

The ``charges_with_last_transaction`` view mirrors the dump's ``LEFT JOIN
LATERAL`` with two correlated scalar subqueries (SQLite has no ``LATERAL``),
ordered by ``created_at DESC, id DESC`` — SQLite already sorts NULLs last on a
descending key, so ``NULLS LAST`` is redundant — with ``LIMIT 1``. A charge with
no transaction reads as ``NULL``/``NULL`` instead of disappearing.

The 49 ``trg_updated_at_*`` triggers and the ``set_updated_at`` function are not
ported as database objects: the metadata already declares ``onupdate`` per table,
so the rule is carried by the ORM — an ``(b) application guard`` with the
equivalent test ``test_orm_onupdate_advances_updated_at``. Duplicating the rule
in the database would make a value written by the ORM and a value written by raw
SQL disagree. That classification and its residual risk are recorded in the
inventory matrix.

The migration is defensive about the fresh-database path: ``Base.metadata`` is
created by the baseline and no earlier revision touches these objects, but the
DDL uses ``IF NOT EXISTS`` and every trigger is only created when its table
exists, so re-running against a partially built database cannot fail on a
missing parent.

The downgrade drops the objects it created and nothing else; the tables, their
rows and the revision chain stay intact.
"""

from typing import Final

import sqlalchemy as sa
from alembic import op

revision = "0036_storage_objects"
down_revision = "0035_credit_ledger_alignment"
branch_labels = None
depends_on = None

CREDIT_TRANSACTIONS = "workspace_credit_transactions"
LOT_CONSUMPTIONS = "workspace_credit_lot_consumptions"
CREDIT_LOTS = "workspace_credit_lots"
SUBSCRIPTION_HISTORY = "subscription_history"
COUPON_REDEMPTIONS = "coupon_redemptions"
COUPONS = "coupons"
CHARGES = "charges"
CHARGE_TRANSACTIONS = "charge_transactions"

# (trigger name, tables the statement needs, DDL). The name is repeated inside the
# DDL because SQLite has no way to create an unnamed trigger; the tuple is the
# single source for the downgrade.
_TRIGGERS: Final[tuple[tuple[str, tuple[str, ...], str], ...]] = (
    (
        "trg_credit_tx_immutable_update",
        (CREDIT_TRANSACTIONS,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_credit_tx_immutable_update
        BEFORE UPDATE ON workspace_credit_transactions
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT,
                'workspace_credit_transactions: UPDATE is not allowed (ledger append-only)');
        END
        """,
    ),
    (
        "trg_credit_tx_immutable_delete",
        (CREDIT_TRANSACTIONS,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_credit_tx_immutable_delete
        BEFORE DELETE ON workspace_credit_transactions
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT,
                'workspace_credit_transactions: DELETE is not allowed (ledger append-only)');
        END
        """,
    ),
    (
        "trg_credit_consumption_immutable_update",
        (LOT_CONSUMPTIONS,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_credit_consumption_immutable_update
        BEFORE UPDATE ON workspace_credit_lot_consumptions
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT,
                'workspace_credit_lot_consumptions: UPDATE is not allowed (immutable consumption)');
        END
        """,
    ),
    (
        "trg_credit_consumption_immutable_delete",
        (LOT_CONSUMPTIONS,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_credit_consumption_immutable_delete
        BEFORE DELETE ON workspace_credit_lot_consumptions
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT,
                'workspace_credit_lot_consumptions: DELETE is not allowed (immutable consumption)');
        END
        """,
    ),
    (
        "trg_subscription_history_append_only_update",
        (SUBSCRIPTION_HISTORY,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_subscription_history_append_only_update
        BEFORE UPDATE ON subscription_history
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'subscription_history is append-only: UPDATE not allowed');
        END
        """,
    ),
    (
        "trg_subscription_history_append_only_delete",
        (SUBSCRIPTION_HISTORY,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_subscription_history_append_only_delete
        BEFORE DELETE ON subscription_history
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'subscription_history is append-only: DELETE not allowed');
        END
        """,
    ),
    (
        "trg_credit_lot_no_delete",
        (CREDIT_LOTS,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_credit_lot_no_delete
        BEFORE DELETE ON workspace_credit_lots
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT, 'workspace_credit_lots: deleting a credit lot is not allowed');
        END
        """,
    ),
    (
        "trg_credit_lot_guard_update",
        (CREDIT_LOTS,),
        """
        CREATE TRIGGER IF NOT EXISTS trg_credit_lot_guard_update
        BEFORE UPDATE ON workspace_credit_lots
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT,
                'workspace_credit_lots: only remaining_amount may decrease (credit lot guard)')
            WHERE NEW.id IS NOT OLD.id
                OR NEW.workspace_id IS NOT OLD.workspace_id
                OR NEW.grant_transaction_id IS NOT OLD.grant_transaction_id
                OR NEW.original_amount IS NOT OLD.original_amount
                OR NEW.expires_at IS NOT OLD.expires_at
                OR NEW.created_at IS NOT OLD.created_at
                OR NEW.remaining_amount > OLD.remaining_amount;
        END
        """,
    ),
    (
        "trg_credit_lot_validate_insert",
        (CREDIT_LOTS, CREDIT_TRANSACTIONS),
        """
        CREATE TRIGGER IF NOT EXISTS trg_credit_lot_validate_insert
        BEFORE INSERT ON workspace_credit_lots
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT,
                'workspace_credit_lots: lot needs a positive grant in its workspace')
            WHERE NEW.grant_transaction_id IS NULL
                OR NOT EXISTS (
                    SELECT 1 FROM workspace_credit_transactions AS t
                    WHERE t.id = NEW.grant_transaction_id
                        AND t.workspace_id = NEW.workspace_id
                        AND t.amount > 0
                );
            SELECT RAISE(ABORT,
                'workspace_credit_lots.original_amount must equal the grant amount')
            WHERE NOT EXISTS (
                SELECT 1 FROM workspace_credit_transactions AS t
                WHERE t.id = NEW.grant_transaction_id
                    AND t.workspace_id = NEW.workspace_id
                    AND t.amount = NEW.original_amount
            );
            SELECT RAISE(ABORT,
                'workspace_credit_lots.remaining_amount must equal original_amount')
            WHERE NEW.remaining_amount IS NOT NEW.original_amount;
        END
        """,
    ),
    (
        "trg_coupon_redemption_once_snapshot",
        (COUPON_REDEMPTIONS, COUPONS),
        """
        CREATE TRIGGER IF NOT EXISTS trg_coupon_redemption_once_snapshot
        BEFORE INSERT ON coupon_redemptions
        FOR EACH ROW
        BEGIN
            SELECT RAISE(ABORT,
                'coupon_redemptions.once_per_workspace must match coupons.once_per_workspace')
            WHERE EXISTS (SELECT 1 FROM coupons AS c WHERE c.id = NEW.coupon_id)
                AND NEW.once_per_workspace IS NOT (
                    SELECT c.once_per_workspace FROM coupons AS c WHERE c.id = NEW.coupon_id
                );
        END
        """,
    ),
)

_VIEW = """
CREATE VIEW IF NOT EXISTS charges_with_last_transaction AS
SELECT
    c.*,
    (
        SELECT ct.external_id
        FROM charge_transactions AS ct
        WHERE ct.charge_id = c.id
        ORDER BY ct.created_at DESC, ct.id DESC
        LIMIT 1
    ) AS last_transaction_id,
    (
        SELECT ct.status
        FROM charge_transactions AS ct
        WHERE ct.charge_id = c.id
        ORDER BY ct.created_at DESC, ct.id DESC
        LIMIT 1
    ) AS last_transaction_status
FROM charges AS c
"""

VIEW = "charges_with_last_transaction"


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for _name, required, statement in _TRIGGERS:
        if set(required) <= tables:
            op.execute(statement)
    if {CHARGES, CHARGE_TRANSACTIONS} <= tables:
        op.execute(_VIEW)


def downgrade() -> None:
    op.execute(f"DROP VIEW IF EXISTS {VIEW}")
    for name, _required, _statement in reversed(_TRIGGERS):
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
