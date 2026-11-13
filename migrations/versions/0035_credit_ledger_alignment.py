"""Align ``workspace_credit_transactions`` to the final modeling (T15, issue #162).

The Credit Transaction ledger is append-only (ADR-019). The final modeling
replaces the generic ``transaction_type``/``reference_type``/``reference_id``
triple with the ``credit_transaction_type`` vocabulary plus one dedicated
column per correlation target, adds the cumulative ``balance_after`` and drops
``updated_at``/``deleted_at``. Corrections are new transactions, so there is no
soft delete left to filter.

The rebuild is the SQLite create/copy/drop/rename pattern used by the rest of
the alignment chain:

- rows with ``deleted_at IS NOT NULL`` or ``amount = 0`` are dropped: the final
  shape has no soft-delete column, and a zero movement is not a ledger entry;
- ``type`` keeps a legacy value that already belongs to the final vocabulary and
  maps the known aliases; every other value becomes ``ADJUSTMENT``;
- the four dedicated references are filled only when ``reference_type`` names
  the target and the target row exists, so a dangling legacy reference becomes
  NULL instead of a foreign-key violation;
- ``balance_after`` is the cumulative ``SUM(amount)`` per workspace ordered by
  ``created_at``. A negative intermediate balance aborts the migration, because
  a Credit Wallet can never go below zero;
- two legacy rows can map onto the same ``UNIQUE (reference, type)`` entry after
  the backfill; that collision aborts before any DDL with a message naming the
  key, instead of failing late with ``UNIQUE constraint failed``;
- the ``workspace_credit_lots.grant_transaction_id`` and
  ``workspace_credit_lot_consumptions.transaction_id`` references are ``NOT
  NULL``/``ON DELETE RESTRICT``, so a dropped transaction they depend on aborts
  the migration instead of orphaning the Credit Lot.

``migrations/env.py`` disables ``PRAGMA foreign_keys`` for the rebuild, so the
credit lots and coupon redemptions that reference this table are not cascaded
away: their rows are copied unchanged and keep resolving after the rename. The
one child that tolerates a dropped parent is
``coupon_redemptions.credit_transaction_id`` (``ON DELETE SET NULL``): those
links are nulled explicitly before the swap so the upgraded database stays free
of dangling references.

The downgrade rebuilds the legacy shape and maps ``type`` back to
``transaction_type``. It is shape-based and lossy: the original legacy value of
an aliased/unknown transaction type, the generic ``reference_type`` when more
than one dedicated column was set, and the dropped soft-deleted/zero rows are
not recoverable.
"""

import sqlalchemy as sa
from alembic import op

from creator.infrastructure.database.constraints import at_most_one_of
from creator.infrastructure.database.types import timestamp_tz, uuid_pk

revision = "0035_credit_ledger_alignment"
down_revision = "0034_billing_media_micro"
branch_labels = None
depends_on = None

TABLE = "workspace_credit_transactions"
REBUILD_TABLE = "workspace_credit_transactions_rebuild"
LEGACY_TABLE = "workspace_credit_transactions_legacy"

_CREDIT_TRANSACTION_TYPES = (
    "SUBSCRIPTION_CREDIT",
    "TOP_UP",
    "COUPON_CREDIT",
    "GENERATION",
    "EXPIRATION",
    "REFUND",
    "ADJUSTMENT",
)

# ``VARCHAR`` width of the final modeling: the longest member of the vocabulary.
_VOCABULARY_LENGTH = max(len(value) for value in _CREDIT_TRANSACTION_TYPES)

# Final values keep themselves; the aliases cover the vocabulary the legacy
# generic column accepted. Anything else is an ADJUSTMENT, never an error: the
# movement is preserved and the ledger stays append-only.
_MAPPED_TYPE_SQL = """
CASE
    WHEN upper(t.transaction_type) IN (
        'SUBSCRIPTION_CREDIT', 'TOP_UP', 'COUPON_CREDIT', 'GENERATION',
        'EXPIRATION', 'REFUND', 'ADJUSTMENT'
    ) THEN upper(t.transaction_type)
    WHEN upper(t.transaction_type) IN ('CREDIT', 'GRANT', 'TOPUP', 'PURCHASE') THEN 'TOP_UP'
    WHEN upper(t.transaction_type) = 'SUBSCRIPTION' THEN 'SUBSCRIPTION_CREDIT'
    WHEN upper(t.transaction_type) = 'COUPON' THEN 'COUPON_CREDIT'
    WHEN upper(t.transaction_type) IN ('DEBIT', 'SPEND') THEN 'GENERATION'
    WHEN upper(t.transaction_type) = 'EXPIRE' THEN 'EXPIRATION'
    WHEN upper(t.transaction_type) = 'ADJUST' THEN 'ADJUSTMENT'
    ELSE 'ADJUSTMENT'
END
"""

# A mapped type must satisfy ``chk_credit_tx_amount_by_type``. A legacy row
# whose sign disagrees with its type keeps its amount and becomes an ADJUSTMENT
# (the one type that accepts either sign) instead of failing the copy.
_SIGNED_TYPE_SQL = """
CASE
    WHEN mapped_type = 'ADJUSTMENT' THEN 'ADJUSTMENT'
    WHEN mapped_type IN ('SUBSCRIPTION_CREDIT', 'TOP_UP', 'COUPON_CREDIT', 'REFUND')
         AND amount > 0 THEN mapped_type
    WHEN mapped_type IN ('GENERATION', 'EXPIRATION') AND amount < 0 THEN mapped_type
    ELSE 'ADJUSTMENT'
END
"""

_REFERENCE_SQL = """
CASE WHEN lower(reference_type) = 'order' AND EXISTS (
        SELECT 1 FROM orders o
        WHERE o.id = t.reference_id AND o.workspace_id = t.workspace_id
    ) THEN t.reference_id END AS order_id,
CASE WHEN lower(reference_type) = 'invoice' AND EXISTS (
        SELECT 1 FROM invoices i WHERE i.id = t.reference_id
    ) THEN t.reference_id END AS invoice_id,
CASE WHEN lower(reference_type) = 'generated_image' AND EXISTS (
        SELECT 1 FROM generated_images g WHERE g.id = t.reference_id
    ) THEN t.reference_id END AS generated_image_id,
CASE WHEN lower(reference_type) = 'image_resize' AND EXISTS (
        SELECT 1 FROM image_resizes r WHERE r.id = t.reference_id
    ) THEN t.reference_id END AS image_resize_id
"""

# The rows the final shape keeps, mapped to the final vocabulary and references.
# Both the copy and the duplicate pre-check read this one definition, so the
# keys the check rejects are exactly the keys the ``UNIQUE (reference, type)``
# indexes would reject.
_ALIGNED_ROWS_CTE = f"""
WITH mapped AS (
    SELECT
        t.id,
        t.workspace_id,
        t.amount,
        t.created_at,
        t.reference_type,
        t.reference_id,
        {_MAPPED_TYPE_SQL} AS mapped_type
    FROM {TABLE} t
    WHERE t.deleted_at IS NULL AND t.amount <> 0
),
aligned AS (
    SELECT
        t.id,
        t.workspace_id,
        t.amount,
        t.created_at,
        {_SIGNED_TYPE_SQL} AS type,
        {_REFERENCE_SQL}
    FROM mapped t
)
"""

_COPY_INTO_FINAL = f"""
{_ALIGNED_ROWS_CTE}
INSERT INTO {REBUILD_TABLE} (
    id, workspace_id, amount, balance_after, type, order_id, invoice_id,
    generated_image_id, image_resize_id, created_by, created_at
)
SELECT
    t.id,
    t.workspace_id,
    t.amount,
    SUM(t.amount) OVER (
        PARTITION BY t.workspace_id
        ORDER BY t.created_at, t.id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ),
    t.type,
    t.order_id,
    t.invoice_id,
    t.generated_image_id,
    t.image_resize_id,
    NULL,
    t.created_at
FROM aligned t
"""

# The rows the backfill drops: the final shape has no soft-delete column and a
# zero movement is not a ledger entry. Single source of truth for every child
# cleanup and every abort below.
_DROPPED_IDS_SQL = f"SELECT id FROM {TABLE} WHERE deleted_at IS NOT NULL OR amount = 0"

_COUPON_REDEMPTIONS = "coupon_redemptions"
_CREDIT_LOTS = "workspace_credit_lots"
_CREDIT_LOT_CONSUMPTIONS = "workspace_credit_lot_consumptions"

# ``coupon_redemptions.credit_transaction_id`` is ``ON DELETE SET NULL``: null the
# links to the dropped rows before the swap, because ``PRAGMA foreign_keys`` is
# OFF during the rebuild and nothing would cascade.
_DETACH_DROPPED_COUPON_REDEMPTIONS = f"""
UPDATE {_COUPON_REDEMPTIONS}
SET credit_transaction_id = NULL, updated_at = CURRENT_TIMESTAMP
WHERE credit_transaction_id IN ({_DROPPED_IDS_SQL})
"""

# Each unique index over a dedicated reference, expressed against the aligned
# rows so it groups exactly what the index will store.
_DUPLICATE_KEY_CHECKS = " UNION ALL ".join(
    f"""
    SELECT '{column}' AS reference_column, {column} AS reference_id, type, COUNT(*) AS total
    FROM aligned
    WHERE {column} IS NOT NULL
    GROUP BY {column}, type
    HAVING COUNT(*) > 1
    """
    for column in ("order_id", "invoice_id", "generated_image_id", "image_resize_id")
)

_COPY_INTO_LEGACY = f"""
INSERT INTO {LEGACY_TABLE} (
    id, workspace_id, amount, transaction_type, reference_type, reference_id,
    created_at, updated_at, deleted_at
)
SELECT
    id,
    workspace_id,
    amount,
    type,
    CASE
        WHEN order_id IS NOT NULL THEN 'order'
        WHEN invoice_id IS NOT NULL THEN 'invoice'
        WHEN generated_image_id IS NOT NULL THEN 'generated_image'
        WHEN image_resize_id IS NOT NULL THEN 'image_resize'
    END,
    COALESCE(order_id, invoice_id, generated_image_id, image_resize_id),
    created_at,
    created_at,
    NULL
FROM {TABLE}
"""


def _columns(table: str) -> dict[str, dict[str, object]]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return {}
    return {column["name"]: dict(column) for column in inspector.get_columns(table)}


def _abort_on_negative_balance() -> None:
    """Fail loudly instead of writing a wallet balance below zero."""
    row = (
        op.get_bind()
        .execute(
            sa.text(
                f"""
            SELECT workspace_id, running_balance FROM (
                SELECT workspace_id,
                       SUM(amount) OVER (
                           PARTITION BY workspace_id
                           ORDER BY created_at, id
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                       ) AS running_balance
                FROM {TABLE}
                WHERE deleted_at IS NULL AND amount <> 0
            )
            WHERE running_balance < 0
            ORDER BY workspace_id
            LIMIT 1
            """
            )
        )
        .fetchone()
    )
    if row is not None:
        raise ValueError(
            "workspace_credit_transactions: the cumulative credit balance for workspace "
            f"{row[0]} would be {row[1]} after the backfill; a Credit Wallet cannot go "
            "below zero. Correct the legacy ledger rows and rerun the migration."
        )


def _first_row(sql: str) -> tuple[object, ...] | None:
    return op.get_bind().execute(sa.text(sql)).fetchone()


def _abort_on_duplicate_mapped_keys() -> None:
    """Refuse to collapse two legacy movements onto one unique ledger entry.

    The final modeling declares ``UNIQUE (reference, type)`` for each dedicated
    reference, so two legacy rows that map to the same pair cannot both be
    copied. The ledger is append-only, so silently keeping one would lose an
    amount; failing late inside the ``INSERT``/``CREATE UNIQUE INDEX`` would also
    leave a half-rebuilt table behind (SQLite DDL is non-transactional here). The
    check therefore runs before any DDL and names the colliding key.
    """
    row = _first_row(f"{_ALIGNED_ROWS_CTE}{_DUPLICATE_KEY_CHECKS} LIMIT 1")
    if row is not None:
        raise ValueError(
            "workspace_credit_transactions: the legacy ledger has a duplicate "
            f"({row[0]}, type) key: {row[3]} transactions map to {row[0]}={row[1]} with "
            f"type {row[2]}. The final modeling declares UNIQUE (reference, type), so the "
            "movements cannot both be kept. Merge or correct the duplicate legacy rows and "
            "rerun the migration."
        )


def _abort_on_dropped_lot_grant() -> None:
    """A Credit Lot cannot lose the transaction that granted it.

    ``workspace_credit_lots.grant_transaction_id`` is ``NOT NULL`` and
    ``ON DELETE RESTRICT``: the backfill cannot null it, and dropping the grant
    would leave a lot whose amount has no origin.
    """
    row = _first_row(
        f"""
        SELECT lot.id, lot.grant_transaction_id
        FROM {_CREDIT_LOTS} lot
        WHERE lot.grant_transaction_id IN ({_DROPPED_IDS_SQL})
        ORDER BY lot.id
        LIMIT 1
        """
    )
    if row is not None:
        raise ValueError(
            "workspace_credit_transactions: the backfill drops transaction "
            f"{row[1]}, which is the grant_transaction_id of Credit Lot {row[0]}. "
            "workspace_credit_lots.grant_transaction_id is NOT NULL and ON DELETE RESTRICT, "
            "so dropping the grant would orphan the lot. Restore the transaction (clear its "
            "deleted_at/deleted amount) or remove the lot, then rerun the migration."
        )


def _abort_on_dropped_lot_consumption() -> None:
    """A lot consumption cannot lose the transaction it accounts for.

    ``workspace_credit_lot_consumptions.transaction_id`` is ``NOT NULL`` and
    ``ON DELETE RESTRICT``: the consumption would no longer match a ledger entry.
    """
    row = _first_row(
        f"""
        SELECT consumption.id, consumption.transaction_id
        FROM {_CREDIT_LOT_CONSUMPTIONS} consumption
        WHERE consumption.transaction_id IN ({_DROPPED_IDS_SQL})
        ORDER BY consumption.id
        LIMIT 1
        """
    )
    if row is not None:
        raise ValueError(
            "workspace_credit_transactions: the backfill drops transaction "
            f"{row[1]}, which is the transaction_id of Credit Lot consumption {row[0]}. "
            "workspace_credit_lot_consumptions.transaction_id is NOT NULL and "
            "ON DELETE RESTRICT, so the consumption would point at nothing. Restore the "
            "transaction or remove the consumption, then rerun the migration."
        )


def _detach_dropped_coupon_redemptions() -> None:
    """Null the coupon links whose transaction the backfill drops.

    ``coupon_redemptions.credit_transaction_id`` is ``ON DELETE SET NULL``, but
    ``migrations/env.py`` turns foreign keys off for the rebuild, so the database
    would keep the dangling id forever. The value is neutralised explicitly and
    every resolvable link is preserved.
    """
    op.execute(_DETACH_DROPPED_COUPON_REDEMPTIONS)


def _create_final_table() -> None:
    op.create_table(
        REBUILD_TABLE,
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("workspace_id", uuid_pk, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        # Frozen history: the vocabulary is spelled out as literal SQL instead of
        # importing the live enum, so a later change to `portable_enums` cannot
        # rewrite what this revision did. The width is the longest vocabulary
        # member, so an upgraded database matches the final metadata exactly and
        # `alembic check` stays silent on the upgraded shape.
        sa.Column("type", sa.String(_VOCABULARY_LENGTH), nullable=False),
        sa.Column("order_id", uuid_pk),
        sa.Column("invoice_id", uuid_pk),
        sa.Column("generated_image_id", uuid_pk),
        sa.Column("image_resize_id", uuid_pk),
        sa.Column("created_by", uuid_pk),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["order_id", "workspace_id"],
            ["orders.id", "orders.workspace_id"],
            name="fk_credit_tx_order",
            ondelete="RESTRICT",
        ),
        # SQLite cannot name a constraint added later, so the rebuild declares the
        # single-column foreign keys with the names the final metadata uses.
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_credit_tx_workspace",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_credit_tx_invoice",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["generated_image_id"],
            ["generated_images.id"],
            name="fk_credit_tx_generated_image",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["image_resize_id"],
            ["image_resizes.id"],
            name="fk_credit_tx_image_resize",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_credit_tx_created_by",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "type IN (" + ", ".join(f"'{value}'" for value in _CREDIT_TRANSACTION_TYPES) + ")",
            name="credit_transaction_type",
        ),
        sa.CheckConstraint(
            at_most_one_of("order_id", "invoice_id", "generated_image_id", "image_resize_id"),
            name="chk_credit_tx_single_reference",
        ),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="chk_credit_tx_balance_nonnegative",
        ),
        sa.CheckConstraint(
            "amount <> 0",
            name="chk_credit_tx_amount_nonzero",
        ),
        sa.CheckConstraint(
            "(type IN ('SUBSCRIPTION_CREDIT', 'TOP_UP', 'COUPON_CREDIT', 'REFUND') "
            "AND amount > 0) "
            "OR (type IN ('GENERATION', 'EXPIRATION') AND amount < 0) "
            "OR type = 'ADJUSTMENT'",
            name="chk_credit_tx_amount_by_type",
        ),
    )


def _create_indexes() -> None:
    op.create_index(
        "ix_workspace_credit_transactions_workspace_id_created_at",
        TABLE,
        ["workspace_id", "created_at"],
    )
    op.create_index("uq_credit_tx_id_workspace", TABLE, ["id", "workspace_id"], unique=True)
    op.create_index(
        "uq_workspace_credit_transactions_order_id_type",
        TABLE,
        ["order_id", "type"],
        unique=True,
    )
    op.create_index(
        "uq_workspace_credit_transactions_invoice_id_type",
        TABLE,
        ["invoice_id", "type"],
        unique=True,
    )
    op.create_index(
        "uq_workspace_credit_transactions_generated_image_id_type",
        TABLE,
        ["generated_image_id", "type"],
        unique=True,
    )
    op.create_index(
        "uq_credit_tx_image_resize",
        TABLE,
        ["image_resize_id", "type"],
        unique=True,
    )
    op.create_index(
        "idx_m8_workspace_credit_transactions_created_by",
        TABLE,
        ["created_by"],
        sqlite_where=sa.text("created_by IS NOT NULL"),
    )


def upgrade() -> None:
    columns = _columns(TABLE)
    if not columns:
        return
    if {"type", "balance_after"} <= set(columns):
        # Already aligned: a fresh database is created from the final metadata by
        # the baseline, so this revision only has work to do on an existing one.
        return
    _abort_on_negative_balance()
    # Every pre-check runs before any DDL: SQLite DDL is not part of the Alembic
    # transaction here, so a late abort would leave a half-rebuilt database.
    _abort_on_duplicate_mapped_keys()
    _abort_on_dropped_lot_grant()
    _abort_on_dropped_lot_consumption()
    _detach_dropped_coupon_redemptions()
    _create_final_table()
    op.execute(_COPY_INTO_FINAL)
    op.drop_table(TABLE)
    op.rename_table(REBUILD_TABLE, TABLE)
    _create_indexes()


def downgrade() -> None:
    columns = _columns(TABLE)
    if not columns or "transaction_type" in columns:
        return
    op.create_table(
        LEGACY_TABLE,
        sa.Column("workspace_id", uuid_pk, sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("reference_type", sa.String(40)),
        sa.Column("reference_id", uuid_pk),
        sa.Column("id", uuid_pk, primary_key=True),
        sa.Column("created_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", timestamp_tz, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", timestamp_tz),
    )
    op.execute(_COPY_INTO_LEGACY)
    op.drop_table(TABLE)
    op.rename_table(LEGACY_TABLE, TABLE)
    op.create_index("uq_credit_tx_id_workspace", TABLE, ["id", "workspace_id"], unique=True)
