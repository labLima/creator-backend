"""API composition root.

This is the only module that knows the capability list.
Include order follows the first appearance of each capability in the
pre-refactor `creator.main` so route precedence is unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter

from creator.api.system import router as system_router
from creator.asset.router import router as asset_router
from creator.auth.router import router as auth_router
from creator.billing_account.router import router as billing_account_router
from creator.billing_provider.router import router as billing_provider_router
from creator.brand.router import router as brand_router
from creator.campaign.router import router as campaign_router
from creator.charge.router import router as charge_router
from creator.content.router import router as content_router
from creator.coupon.router import router as coupon_router
from creator.credit.router import router as credit_router
from creator.credit_package.router import router as credit_package_router
from creator.design_structure.router import router as design_structure_router
from creator.generation.router import router as generation_router
from creator.invoice.router import router as invoice_router
from creator.notification.router import router as notification_router
from creator.order.router import router as order_router
from creator.payment_method.router import router as payment_method_router
from creator.persona.router import router as persona_router
from creator.plan.router import router as plan_router
from creator.planning.router import router as planning_router
from creator.post_structure.router import router as post_structure_router
from creator.project.router import router as project_router
from creator.refund.router import router as refund_router
from creator.subscription.router import router as subscription_router
from creator.user.router import router as user_router
from creator.workflow.router import router as workflow_router
from creator.workspace.router import router as workspace_router

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
