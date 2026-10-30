"""API composition root.

This is the only module that knows the capability list.
Include order follows the first appearance of each capability in the
pre-refactor `creator.main` so route precedence is unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter

from creator.api.system import router as system_router
from creator.modules.asset.router import router as asset_router
from creator.modules.auth.router import router as auth_router
from creator.modules.billing_account.router import router as billing_account_router
from creator.modules.billing_provider.router import router as billing_provider_router
from creator.modules.brand.router import router as brand_router
from creator.modules.campaign.router import router as campaign_router
from creator.modules.charge.router import router as charge_router
from creator.modules.content.router import router as content_router
from creator.modules.coupon.router import router as coupon_router
from creator.modules.credit.router import router as credit_router
from creator.modules.credit_package.router import router as credit_package_router
from creator.modules.design_structure.router import router as design_structure_router
from creator.modules.generation.router import router as generation_router
from creator.modules.invoice.router import router as invoice_router
from creator.modules.notification.router import router as notification_router
from creator.modules.order.router import router as order_router
from creator.modules.payment_method.router import router as payment_method_router
from creator.modules.persona.router import router as persona_router
from creator.modules.plan.router import router as plan_router
from creator.modules.planning.router import router as planning_router
from creator.modules.post_structure.router import router as post_structure_router
from creator.modules.project.router import router as project_router
from creator.modules.refund.router import router as refund_router
from creator.modules.subscription.router import router as subscription_router
from creator.modules.user.router import router as user_router
from creator.modules.workflow.router import router as workflow_router
from creator.modules.workspace.router import router as workspace_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(system_router)
api_router.include_router(user_router)
api_router.include_router(workspace_router)
api_router.include_router(brand_router)
api_router.include_router(project_router)
api_router.include_router(campaign_router)
api_router.include_router(persona_router)
api_router.include_router(planning_router)
api_router.include_router(post_structure_router)
api_router.include_router(content_router)
api_router.include_router(workflow_router)
api_router.include_router(generation_router)
api_router.include_router(subscription_router)
api_router.include_router(design_structure_router)
api_router.include_router(credit_router)
api_router.include_router(billing_account_router)
api_router.include_router(payment_method_router)
api_router.include_router(invoice_router)
api_router.include_router(charge_router)
api_router.include_router(order_router)
api_router.include_router(coupon_router)
api_router.include_router(billing_provider_router)
api_router.include_router(refund_router)
api_router.include_router(credit_package_router)
api_router.include_router(plan_router)
api_router.include_router(notification_router)
api_router.include_router(asset_router)
