"""Compatibility shim; implementations moved to capability repositories."""

from __future__ import annotations

from creator.subscription.repository import SqlAlchemySubscriptionHistoryRepository

__all__ = [
    "SqlAlchemySubscriptionHistoryRepository",
]
