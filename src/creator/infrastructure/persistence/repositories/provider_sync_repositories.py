"""Compatibility shim; implementations moved to capability repositories."""

from __future__ import annotations

from creator.billing_provider.repository import (
    SqlAlchemyProviderCustomerRepository,
    SqlAlchemyProviderSubscriptionRepository,
)

__all__ = [
    "SqlAlchemyProviderCustomerRepository",
    "SqlAlchemyProviderSubscriptionRepository",
]
