import pytest

from creator.campaign.schemas import CampaignCreateRequest
from creator.infrastructure.database import metadata as _models  # noqa: F401
from creator.infrastructure.database.db import Base
from creator.infrastructure.database.schema_manifest import LEGACY_TABLES, PDF_TABLES
from creator.notification.schemas import NotificationCreateRequest
from creator.plan.schemas import PlanCreateRequest

EXPECTED_DIAGRAM_TABLES = {
    "plans",
    "plan_items",
    "billing_accounts",
    "billing_addresses",
    "billing_payment_methods",
    "subscriptions",
    "subscription_history",
    "invoices",
    "charges",
    "refunds",
    "provider_webhook_events",
    "provider_idempotency_keys",
    "provider_disputes",
    "campaigns",
    "personas",
    "notifications",
    "notification_recipients",
    "user_devices",
    "notification_preferences",
    "workspace_invites",
    "workspace_invite_usages",
    "brand_colors",
    "brand_assets",
    "coupons",
    "credit_packages",
    "orders",
    "coupon_redemptions",
    "workspace_credit_transactions",
}


def test_pdf_schema_tables_are_registered_in_metadata() -> None:
    assert EXPECTED_DIAGRAM_TABLES <= set(Base.metadata.tables)
    assert PDF_TABLES <= set(Base.metadata.tables)
    assert LEGACY_TABLES <= set(Base.metadata.tables)


def test_core_columns_match_pdf_lengths() -> None:
    users = Base.metadata.tables["users"]
    workspaces = Base.metadata.tables["workspaces"]
    assert users.c.email.type.length == 254
    assert users.c.display_name.type.length == 50
    assert workspaces.c.name.type.length == 50


def test_new_dtos_reject_unknown_fields() -> None:
    assert PlanCreateRequest(code="pro", type="PRO", name="Pro").is_active is True
    assert (
        CampaignCreateRequest(
            workspace_id="00000000-0000-0000-0000-000000000001",
            brand_id="00000000-0000-0000-0000-000000000002",
            name="Launch",
        ).name
        == "Launch"
    )
    assert (
        NotificationCreateRequest(
            workspace_id="00000000-0000-0000-0000-000000000001",
            type="SYSTEM",
            title="Hi",
            body="Hello",
        ).payload
        == {}
    )
    with pytest.raises(ValueError):
        CampaignCreateRequest(
            workspace_id="00000000-0000-0000-0000-000000000001",
            brand_id="00000000-0000-0000-0000-000000000002",
            name="Launch",
            unexpected=True,
        )
    with pytest.raises(ValueError):
        NotificationCreateRequest(
            workspace_id="00000000-0000-0000-0000-000000000001",
            type="SYSTEM",
            title="Hi",
            body="Hello",
            created_by="00000000-0000-0000-0000-000000000002",
        )
