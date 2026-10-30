"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.billing_provider.ports import (
    ProviderCustomerRecord,
    ProviderCustomerRepository,
    ProviderSubscriptionRecord,
    ProviderSubscriptionRepository,
)

__all__ = [
    "ProviderCustomerRecord",
    "ProviderCustomerRepository",
    "ProviderSubscriptionRecord",
    "ProviderSubscriptionRepository",
]
