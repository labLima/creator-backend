"""Portable enum vocabulary mirrored from Creator_DB_final.sql.

The final modeling declares 52 native PostgreSQL enum types. SQLite has no
native enum, so the vocabulary lives here as tuples and the models render it as
VARCHAR plus a CHECK constraint through :func:`enum_column`.

The ``StrEnum`` classes in :mod:`creator.infrastructure.database.enums` are the
application-level vocabulary; this module is the physical contract asserted
against the dump by ``tests/test_portable_enums.py``. When the two disagree the
dump wins and the StrEnum follows.

Generated from the dump; edit only together with the modeling.
"""

from __future__ import annotations

from typing import Final

import sqlalchemy as sa

ADDRESS_STATUS: Final[tuple[str, ...]] = (
    "ACTIVE",
    "INACTIVE",
    "DELETED",
)
AGE_RANGE: Final[tuple[str, ...]] = (
    "UP_TO_17",
    "FROM_18_TO_24",
    "FROM_25_TO_34",
    "FROM_35_TO_44",
    "FROM_45_TO_54",
    "FROM_55_TO_64",
    "FROM_65_PLUS",
)
APPROVAL_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "APPROVED",
    "REJECTED",
)
ART_RATIO: Final[tuple[str, ...]] = (
    "RATIO_4_5",
    "RATIO_1_1",
    "RATIO_9_16",
    "RATIO_16_9",
)
BILLING_ACCOUNT_TYPE: Final[tuple[str, ...]] = (
    "INDIVIDUAL",
    "COMPANY",
)
BILLING_INTERVAL: Final[tuple[str, ...]] = (
    "DAY",
    "WEEK",
    "MONTH",
    "YEAR",
)
BILLING_TYPE: Final[tuple[str, ...]] = (
    "PREPAID",
    "POSTPAID",
)
BRAND_ASSET_TYPE: Final[tuple[str, ...]] = (
    "LOGO",
    "IMAGE",
    "FONT",
    "ICON",
    "DOCUMENT",
    "OTHER",
)
CAMPAIGN_VOICE: Final[tuple[str, ...]] = (
    "INSPIRATIONAL",
    "MOTIVATIONAL",
    "PROFESSIONAL",
    "CASUAL",
    "ELEGANT",
    "MODERN",
    "TRADITIONAL",
    "FUN",
    "SERIOUS",
)
CARD_BRAND: Final[tuple[str, ...]] = (
    "VISA",
    "MASTERCARD",
    "AMEX",
    "ELO",
    "HIPERCARD",
    "DINERS",
    "DISCOVER",
    "JCB",
    "AURA",
    "CABAL",
    "OTHER",
)
CARD_STATUS: Final[tuple[str, ...]] = (
    "ACTIVE",
    "DELETED",
    "EXPIRED",
)
CATALOG_STATUS: Final[tuple[str, ...]] = (
    "ACTIVE",
    "INACTIVE",
    "ARCHIVED",
)
CHARGE_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "PAID",
    "CANCELED",
    "PROCESSING",
    "FAILED",
    "OVERPAID",
    "UNDERPAID",
    "CHARGEDBACK",
)
CONSENT_TYPE: Final[tuple[str, ...]] = (
    "TERMS_OF_USE",
    "PRIVACY_POLICY",
    "MARKETING_COMMUNICATIONS",
)
CONTENT_FORMAT: Final[tuple[str, ...]] = (
    "IMAGE",
    "CAROUSEL",
    "STORIES",
)
COUPON_APPLIES_TO: Final[tuple[str, ...]] = (
    "SUBSCRIPTION_AND_CREDITS",
    "SUBSCRIPTION_ONLY",
    "CREDITS_ONLY",
)
COUPON_REDEMPTION_STATUS: Final[tuple[str, ...]] = (
    "APPLIED",
    "CANCELED",
)
COUPON_TYPE: Final[tuple[str, ...]] = (
    "DISCOUNT",
    "CREDIT",
)
CREDIT_TRANSACTION_TYPE: Final[tuple[str, ...]] = (
    "SUBSCRIPTION_CREDIT",
    "TOP_UP",
    "COUPON_CREDIT",
    "GENERATION",
    "EXPIRATION",
    "REFUND",
    "ADJUSTMENT",
)
DEVICE_PLATFORM: Final[tuple[str, ...]] = (
    "IOS",
    "ANDROID",
    "WEB",
)
DISPUTE_RESULT: Final[tuple[str, ...]] = (
    "WON",
    "LOST",
    "CANCELED",
)
DISPUTE_STATUS: Final[tuple[str, ...]] = (
    "OPEN",
    "UNDER_REVIEW",
    "RESOLVED",
)
FISCAL_INVOICE_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "PROCESSING",
    "ISSUED",
    "CANCELED",
    "FAILED",
)
FUNDING_SOURCE: Final[tuple[str, ...]] = (
    "CREDIT",
    "DEBIT",
)
GENERATION_STATUS: Final[tuple[str, ...]] = (
    "GENERATING",
    "SUCCEEDED",
    "FAILED",
)
IDEMPOTENCY_STATUS: Final[tuple[str, ...]] = (
    "STARTED",
    "COMPLETED",
    "FAILED",
)
IMAGE_FEEDBACK_TYPE: Final[tuple[str, ...]] = (
    "POSITIVE",
    "NEGATIVE",
    "NOT_USED",
)
INVITE_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "ACCEPTED",
    "REVOKED",
    "EXPIRED",
)
INVITE_TYPE: Final[tuple[str, ...]] = (
    "EMAIL",
    "LINK",
)
INVOICE_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "PAID",
    "CANCELED",
    "SCHEDULED",
    "FAILED",
)
MEMBER_STATUS: Final[tuple[str, ...]] = (
    "ACTIVE",
    "SUSPENDED",
    "REMOVED",
)
NOTIFICATION_CHANNEL: Final[tuple[str, ...]] = (
    "EMAIL",
    "IN_APP",
    "PUSH",
)
NOTIFICATION_DELIVERY_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "SENT",
    "FAILED",
)
NOTIFICATION_RESOURCE_TYPE: Final[tuple[str, ...]] = (
    "WORKSPACE_INVITE",
    "WORKSPACE_MEMBER",
    "POST",
    "GENERATED_IMAGE",
    "SUBSCRIPTION",
    "ORDER",
    "INVOICE",
    "CHARGE",
    "COUPON",
)
NOTIFICATION_TYPE: Final[tuple[str, ...]] = (
    "CONTENT_GENERATION",
    "CONTENT_APPROVAL",
    "INVITE",
    "BILLING",
    "CREDITS",
    "COUPON",
    "SYSTEM",
)
ORDER_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "PAID",
    "CANCELED",
    "FAILED",
)
PAYMENT_METHOD_TYPE: Final[tuple[str, ...]] = (
    "CREDIT_CARD",
    "DEBIT_CARD",
    "BOLETO",
    "PIX",
)
PAYMENT_PROVIDER: Final[tuple[str, ...]] = (
    "PAGARME",
    "STRIPE",
)
PERSONA_GENDER: Final[tuple[str, ...]] = (
    "MALE",
    "FEMALE",
    "NON_BINARY",
    "OTHER",
    "PREFER_NOT_TO_SAY",
)
PLAN_TYPE: Final[tuple[str, ...]] = (
    "FREE",
    "STARTER",
    "PRO",
    "STUDIO",
    "ENTERPRISE",
)
PRICING_SCHEME_TYPE: Final[tuple[str, ...]] = (
    "FLAT",
    "TIERED",
    "VOLUME",
    "STAIRSTEP",
)
PROVIDER_SUBSCRIPTION_STATUS: Final[tuple[str, ...]] = (
    "ACTIVE",
    "CANCELED",
    "FUTURE",
)
PUBLICATION_STATUS: Final[tuple[str, ...]] = (
    "DRAFT",
    "SCHEDULED",
    "PUBLISHED",
)
REFUND_REASON: Final[tuple[str, ...]] = (
    "CUSTOMER_REQUEST",
    "CHARGEBACK",
    "FRAUD_SUSPECT",
    "DUPLICATE",
    "SERVICE_FAILURE",
    "OTHER",
)
REFUND_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "SUCCEEDED",
    "FAILED",
)
RESIZE_STATUS: Final[tuple[str, ...]] = (
    "PENDING",
    "PROCESSING",
    "SUCCEEDED",
    "FAILED",
)
SUBSCRIPTION_CHANGE_TYPE: Final[tuple[str, ...]] = (
    "CREATE",
    "UPGRADE",
    "DOWNGRADE",
    "CANCEL",
    "RENEW",
)
SUBSCRIPTION_STATUS: Final[tuple[str, ...]] = (
    "ACTIVE",
    "TRIALING",
    "PAST_DUE",
    "CANCELED",
    "EXPIRED",
)
SUBSCRIPTION_STATUS_REASON: Final[tuple[str, ...]] = (
    "PAYMENT_FAILED",
    "CARD_EXPIRED",
    "CUSTOMER_REQUEST",
    "PLAN_CHANGED",
    "FRAUD_SUSPECT",
    "DUNNING_EXHAUSTED",
    "TRIAL_ENDED",
)
TRANSACTION_STATUS: Final[tuple[str, ...]] = (
    "AUTHORIZED_PENDING_CAPTURE",
    "NOT_AUTHORIZED",
    "CAPTURED",
    "PARTIAL_CAPTURE",
    "WAITING_CAPTURE",
    "REFUNDED",
    "VOIDED",
    "PARTIAL_REFUNDED",
    "PARTIAL_VOID",
    "ERROR_ON_VOIDING",
    "ERROR_ON_REFUNDING",
    "WAITING_CANCELLATION",
    "WITH_ERROR",
    "FAILED",
    "WAITING_PAYMENT",
    "PENDING_REFUND",
    "GENERATED",
    "VIEWED",
    "PAID",
    "CHARGEDBACK",
)
WEBHOOK_PROCESSING_STATUS: Final[tuple[str, ...]] = (
    "RECEIVED",
    "PROCESSING",
    "PROCESSED",
    "FAILED",
    "IGNORED",
)
WORKSPACE_ROLE: Final[tuple[str, ...]] = (
    "OWNER",
    "MANAGER",
    "EDITOR",
    "VIEWER",
)


ENUMS: Final[dict[str, tuple[str, ...]]] = {
    "address_status": ADDRESS_STATUS,
    "age_range": AGE_RANGE,
    "approval_status": APPROVAL_STATUS,
    "art_ratio": ART_RATIO,
    "billing_account_type": BILLING_ACCOUNT_TYPE,
    "billing_interval": BILLING_INTERVAL,
    "billing_type": BILLING_TYPE,
    "brand_asset_type": BRAND_ASSET_TYPE,
    "campaign_voice": CAMPAIGN_VOICE,
    "card_brand": CARD_BRAND,
    "card_status": CARD_STATUS,
    "catalog_status": CATALOG_STATUS,
    "charge_status": CHARGE_STATUS,
    "consent_type": CONSENT_TYPE,
    "content_format": CONTENT_FORMAT,
    "coupon_applies_to": COUPON_APPLIES_TO,
    "coupon_redemption_status": COUPON_REDEMPTION_STATUS,
    "coupon_type": COUPON_TYPE,
    "credit_transaction_type": CREDIT_TRANSACTION_TYPE,
    "device_platform": DEVICE_PLATFORM,
    "dispute_result": DISPUTE_RESULT,
    "dispute_status": DISPUTE_STATUS,
    "fiscal_invoice_status": FISCAL_INVOICE_STATUS,
    "funding_source": FUNDING_SOURCE,
    "generation_status": GENERATION_STATUS,
    "idempotency_status": IDEMPOTENCY_STATUS,
    "image_feedback_type": IMAGE_FEEDBACK_TYPE,
    "invite_status": INVITE_STATUS,
    "invite_type": INVITE_TYPE,
    "invoice_status": INVOICE_STATUS,
    "member_status": MEMBER_STATUS,
    "notification_channel": NOTIFICATION_CHANNEL,
    "notification_delivery_status": NOTIFICATION_DELIVERY_STATUS,
    "notification_resource_type": NOTIFICATION_RESOURCE_TYPE,
    "notification_type": NOTIFICATION_TYPE,
    "order_status": ORDER_STATUS,
    "payment_method_type": PAYMENT_METHOD_TYPE,
    "payment_provider": PAYMENT_PROVIDER,
    "persona_gender": PERSONA_GENDER,
    "plan_type": PLAN_TYPE,
    "pricing_scheme_type": PRICING_SCHEME_TYPE,
    "provider_subscription_status": PROVIDER_SUBSCRIPTION_STATUS,
    "publication_status": PUBLICATION_STATUS,
    "refund_reason": REFUND_REASON,
    "refund_status": REFUND_STATUS,
    "resize_status": RESIZE_STATUS,
    "subscription_change_type": SUBSCRIPTION_CHANGE_TYPE,
    "subscription_status": SUBSCRIPTION_STATUS,
    "subscription_status_reason": SUBSCRIPTION_STATUS_REASON,
    "transaction_status": TRANSACTION_STATUS,
    "webhook_processing_status": WEBHOOK_PROCESSING_STATUS,
    "workspace_role": WORKSPACE_ROLE,
}


def enum_column(name: str, *, length: int | None = None, create_constraint: bool = True) -> sa.Enum:
    """Render a portable enum column: VARCHAR plus CHECK, never a native type.

    ``validate_strings`` makes an out-of-vocabulary value fail at flush time
    instead of being written as free text.
    """
    values = ENUMS.get(name)
    if values is None:
        raise KeyError(f"unknown enum {name!r}; add it from Creator_DB_final.sql")
    size = length if length is not None else max(len(value) for value in values)
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=create_constraint,
        length=size,
        validate_strings=True,
    )


__all__ = ["ENUMS", "enum_column"]
