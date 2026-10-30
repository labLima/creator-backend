"""Import every capability table so `Base.metadata` is complete.

This module is the single aggregator: Alembic, `create_all()` and the schema
snapshot tests import it. A table module missing here disappears from the
metadata without any other signal, which is exactly the failure
`tests/test_schema_inventory.py` is designed to catch.
"""

from __future__ import annotations

from creator.asset import models as _asset_tables  # noqa: F401
from creator.auth import models as _auth_tables  # noqa: F401
from creator.billing_account import models as _billing_account_tables  # noqa: F401
from creator.billing_provider import models as _billing_provider_tables  # noqa: F401
from creator.brand import models as _brand_tables  # noqa: F401
from creator.campaign import models as _campaign_tables  # noqa: F401
from creator.charge import models as _charge_tables  # noqa: F401
from creator.content import models as _content_tables  # noqa: F401
from creator.coupon import models as _coupon_tables  # noqa: F401
from creator.credit import models as _credit_tables  # noqa: F401
from creator.credit_package import models as _credit_package_tables  # noqa: F401
from creator.design_structure import models as _design_structure_tables  # noqa: F401
from creator.generation import models as _generation_tables  # noqa: F401
from creator.invoice import models as _invoice_tables  # noqa: F401
from creator.notification import models as _notification_tables  # noqa: F401
from creator.order import models as _order_tables  # noqa: F401
from creator.payment_method import models as _payment_method_tables  # noqa: F401
from creator.persona import models as _persona_tables  # noqa: F401
from creator.plan import models as _plan_tables  # noqa: F401
from creator.planning import models as _planning_tables  # noqa: F401
from creator.post_structure import models as _post_structure_tables  # noqa: F401
from creator.project import models as _project_tables  # noqa: F401
from creator.refund import models as _refund_tables  # noqa: F401
from creator.subscription import models as _subscription_tables  # noqa: F401
from creator.user import models as _user_tables  # noqa: F401
from creator.workflow import models as _workflow_tables  # noqa: F401
from creator.workspace import models as _workspace_tables  # noqa: F401
