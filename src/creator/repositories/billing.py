"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.billing_account.ports import (
    BillingAccountRecord,
    BillingAccountRepository,
    BillingAddressRecord,
    BillingAddressRepository,
)
from creator.charge.ports import ChargeRecord, ChargeRepository
from creator.invoice.ports import InvoiceRecord, InvoiceRepository
from creator.payment_method.ports import BillingPaymentMethodRecord, BillingPaymentMethodRepository
from creator.plan.ports import PlanItemRecord, PlanItemRepository, PlanRecord, PlanRepository
from creator.subscription.ports import SubscriptionRecord, SubscriptionRepository

__all__ = [
    "BillingAccountRecord",
    "BillingAccountRepository",
    "BillingAddressRecord",
    "BillingAddressRepository",
    "BillingPaymentMethodRecord",
    "BillingPaymentMethodRepository",
    "ChargeRecord",
    "ChargeRepository",
    "InvoiceRecord",
    "InvoiceRepository",
    "PlanItemRecord",
    "PlanItemRepository",
    "PlanRecord",
    "PlanRepository",
    "SubscriptionRecord",
    "SubscriptionRepository",
]
