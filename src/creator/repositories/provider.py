"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.billing_provider.ports import ProviderDisputeRecord, ProviderDisputeRepository
from creator.refund.ports import RefundRecord, RefundRepository

__all__ = [
    "ProviderDisputeRecord",
    "ProviderDisputeRepository",
    "RefundRecord",
    "RefundRepository",
]
