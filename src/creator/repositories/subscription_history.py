"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.subscription.ports import SubscriptionHistoryRecord, SubscriptionHistoryRepository

__all__ = [
    "SubscriptionHistoryRecord",
    "SubscriptionHistoryRepository",
]
