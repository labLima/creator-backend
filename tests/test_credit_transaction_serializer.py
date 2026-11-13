"""The credit ledger payload must publish the final modeling, not the legacy triple.

``_workspace_credit_transaction_data`` is the mapper `creator.credit.service`
uses for both credit reads. The final modeling replaces
``transaction_type``/``reference_type``/``reference_id`` with the
``credit_transaction_type`` vocabulary plus one dedicated column per correlation
target, adds the cumulative ``balance_after`` and drops the soft-delete pair
(issue #162).

The mapper is tested directly, with a stub record, because the guarantee is about
the payload shape: the HTTP tests in `tests/test_api.py` do not cover this route.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from creator.application.serializers import _workspace_credit_transaction_data

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
TRANSACTION_ID = UUID("22222222-2222-2222-2222-222222222222")
ORDER_ID = UUID("33333333-3333-3333-3333-333333333333")
GENERATED_IMAGE_ID = UUID("44444444-4444-4444-4444-444444444444")
CREATED_BY = UUID("55555555-5555-5555-5555-555555555555")
CREATED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


class LedgerRecord:
    """A Credit Transaction record with every final column populated.

    The legacy ``transaction_type``/``reference_type``/``reference_id`` and the
    soft-delete pair are present on purpose: the mapper must stop reading them,
    so a payload that still publishes them fails on the key assertion instead of
    on an ``AttributeError``.
    """

    id = TRANSACTION_ID
    workspace_id = WORKSPACE_ID
    amount = -30
    balance_after = 70
    type = "GENERATION"
    order_id = ORDER_ID
    invoice_id = None
    generated_image_id = GENERATED_IMAGE_ID
    image_resize_id = None
    created_by = CREATED_BY
    created_at = CREATED_AT

    transaction_type = "GENERATION"
    reference_type = "generated_image"
    reference_id = GENERATED_IMAGE_ID
    updated_at = CREATED_AT
    deleted_at = None


EXPECTED_KEYS = {
    "id",
    "workspace_id",
    "amount",
    "type",
    "balance_after",
    "order_id",
    "invoice_id",
    "generated_image_id",
    "image_resize_id",
    "created_by",
    "created_at",
}
LEGACY_KEYS = {"transaction_type", "reference_type", "reference_id", "updated_at", "deleted_at"}


def test_payload_publishes_the_final_ledger_columns() -> None:
    payload = _workspace_credit_transaction_data(LedgerRecord())

    missing = sorted(EXPECTED_KEYS - set(payload))
    assert not missing, (
        "the credit transaction payload is missing the final modeling columns "
        f"{missing}; got {sorted(payload)}"
    )
    leaked = sorted(LEGACY_KEYS & set(payload))
    assert not leaked, (
        f"the payload still publishes the legacy columns {leaked}; a client must read "
        f"`type` and the dedicated references, not the generic triple"
    )
    assert set(payload) == EXPECTED_KEYS, (
        f"unexpected payload keys {sorted(set(payload) - EXPECTED_KEYS)}"
    )


def test_payload_values_are_serialised() -> None:
    payload = _workspace_credit_transaction_data(LedgerRecord())

    assert payload["id"] == str(TRANSACTION_ID)
    assert payload["workspace_id"] == str(WORKSPACE_ID)
    assert payload["amount"] == -30
    assert payload["balance_after"] == 70, (
        "balance_after is the ledger balance after the transaction and must be published; "
        f"got {payload['balance_after']!r}"
    )
    assert payload["type"] == "GENERATION"
    assert payload["order_id"] == str(ORDER_ID)
    assert payload["generated_image_id"] == str(GENERATED_IMAGE_ID)
    assert payload["created_by"] == str(CREATED_BY)
    assert payload["created_at"] == CREATED_AT.isoformat()


def test_payload_keeps_absent_references_null() -> None:
    class MinimalRecord:
        id = TRANSACTION_ID
        workspace_id = WORKSPACE_ID
        amount = 100
        balance_after = 100
        type = "TOP_UP"
        order_id = None
        invoice_id = None
        generated_image_id = None
        image_resize_id = None
        created_by = None
        created_at = CREATED_AT

    payload = _workspace_credit_transaction_data(MinimalRecord())

    for key in ("order_id", "invoice_id", "generated_image_id", "image_resize_id", "created_by"):
        assert payload[key] is None, (
            f"{key} must be null when the ledger row has no such reference; got {payload[key]!r}"
        )
