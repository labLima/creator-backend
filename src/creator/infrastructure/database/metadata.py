"""Import every capability table so `Base.metadata` is complete.

This module is the single aggregator: Alembic, `create_all()` and the schema
snapshot tests import it. A table module missing here disappears from the
metadata without any other signal, which is exactly the failure
`tests/test_schema_inventory.py` is designed to catch.
"""

from __future__ import annotations

from creator.modules.asset.adapters import tables as _asset_tables  # noqa: F401
from creator.modules.auth.adapters import tables as _auth_tables  # noqa: F401
from creator.modules.billing_account.adapters import tables as _billing_account_tables  # noqa: F401
from creator.modules.billing_provider.adapters import tables as _billing_provider_tables  # noqa: F401
from creator.modules.brand.adapters import tables as _brand_tables  # noqa: F401
from creator.modules.campaign.adapters import tables as _campaign_tables  # noqa: F401
from creator.modules.charge.adapters import tables as _charge_tables  # noqa: F401
from creator.modules.content.adapters import tables as _content_tables  # noqa: F401
from creator.modules.coupon.adapters import tables as _coupon_tables  # noqa: F401
from creator.modules.credit.adapters import tables as _credit_tables  # noqa: F401
from creator.modules.credit_package.adapters import tables as _credit_package_tables  # noqa: F401
from creator.modules.design_structure.adapters import tables as _design_structure_tables  # noqa: F401
from creator.modules.generation.adapters import tables as _generation_tables  # noqa: F401
from creator.modules.invoice.adapters import tables as _invoice_tables  # noqa: F401
from creator.modules.notification.adapters import tables as _notification_tables  # noqa: F401
from creator.modules.order.adapters import tables as _order_tables  # noqa: F401
from creator.modules.payment_method.adapters import tables as _payment_method_tables  # noqa: F401
from creator.modules.persona.adapters import tables as _persona_tables  # noqa: F401
from creator.modules.plan.adapters import tables as _plan_tables  # noqa: F401
from creator.modules.planning.adapters import tables as _planning_tables  # noqa: F401
from creator.modules.post_structure.adapters import tables as _post_structure_tables  # noqa: F401
from creator.modules.project.adapters import tables as _project_tables  # noqa: F401
from creator.modules.refund.adapters import tables as _refund_tables  # noqa: F401
from creator.modules.subscription.adapters import tables as _subscription_tables  # noqa: F401
from creator.modules.user.adapters import tables as _user_tables  # noqa: F401
from creator.modules.workflow.adapters import tables as _workflow_tables  # noqa: F401
from creator.modules.workspace.adapters import tables as _workspace_tables  # noqa: F401
