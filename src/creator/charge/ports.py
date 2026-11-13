"""Persistence ports owned by the charge capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChargeRecord:
    id: UUID
    billing_account_id: UUID
    invoice_id: UUID | None
    amount_cents: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True)
class ChargeWithLastTransactionRecord:
    """A charge plus its latest transaction, as ``charges_with_last_transaction`` exposes it.

    The view is the T20 port of the dump's ``LEFT JOIN LATERAL``: ``last_transaction_id``
    is the transaction's ``external_id`` and ``last_transaction_status`` its status, both
    ``None`` when the charge has no transaction at all. A charge of another tenant is not
    readable through the seam, exactly like ``get_for_user``.
    """

    charge: ChargeRecord
    last_transaction_id: str | None
    last_transaction_status: str | None


class ChargeRepository(Protocol):
    def list_for_user(self, *, user_id: UUID) -> list[ChargeRecord]: ...
    def get_for_user(self, *, user_id: UUID, charge_id: UUID) -> ChargeRecord | None: ...
    def get_with_last_transaction_for_user(
        self, *, user_id: UUID, charge_id: UUID
    ) -> ChargeWithLastTransactionRecord | None:
        """The charge and its latest transaction, scoped to the billing account owner.

        Reads the ``charges_with_last_transaction`` view of the final modeling; ``None``
        for a charge that does not belong to the user's billing account.
        """
        ...

    def add(
        self, *, billing_account_id: UUID, invoice_id: UUID | None, amount_cents: int, currency: str
    ) -> ChargeRecord: ...
    def update(self, *, charge_id: UUID, fields: dict[str, object]) -> ChargeRecord: ...
    def soft_delete(self, *, charge_id: UUID) -> None: ...
