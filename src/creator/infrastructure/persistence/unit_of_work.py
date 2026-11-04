from __future__ import annotations

import logging
import time
from collections.abc import Callable, Generator
from types import TracebackType

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from creator.asset.ports import AssetRepository
from creator.asset.repository import SqlAlchemyAssetRepository
from creator.auth.ports import AuthSessionRepository
from creator.auth.repository import SqlAlchemyAuthSessionRepository
from creator.billing_account.repository import (
    SqlAlchemyBillingAccountRepository,
    SqlAlchemyBillingAddressRepository,
)
from creator.billing_provider.repository import (
    SqlAlchemyProviderCustomerRepository,
    SqlAlchemyProviderDisputeRepository,
    SqlAlchemyProviderIdempotencyKeyRepository,
    SqlAlchemyProviderSubscriptionRepository,
    SqlAlchemyProviderWebhookEventRepository,
)
from creator.brand.repository import (
    SqlAlchemyBrandAssetRepository,
    SqlAlchemyBrandColorRepository,
    SqlAlchemyBrandRepository,
    SqlAlchemyBrandSettingsRepository,
)
from creator.campaign.ports import CampaignRepository
from creator.campaign.repository import SqlAlchemyCampaignRepository
from creator.charge.ports import ChargeRepository
from creator.charge.repository import SqlAlchemyChargeRepository
from creator.content.ports import ContentRepository
from creator.content.repository import SqlAlchemyContentRepository
from creator.coupon.repository import (
    SqlAlchemyCouponRedemptionRepository,
    SqlAlchemyCouponRepository,
)
from creator.credit.ports import WorkspaceCreditTransactionRepository
from creator.credit.repository import SqlAlchemyWorkspaceCreditTransactionRepository
from creator.credit_package.ports import CreditPackageRepository
from creator.credit_package.repository import SqlAlchemyCreditPackageRepository
from creator.design_structure.ports import DesignStructureRepository
from creator.design_structure.repository import SqlAlchemyDesignStructureRepository
from creator.domain.exceptions import PersistenceError
from creator.generation.repository import (
    SqlAlchemyGeneratedImageRepository,
    SqlAlchemyGenerationRepository,
    SqlAlchemyImageGenerationRepository,
)
from creator.infrastructure.database.db import SessionLocal
from creator.infrastructure.persistence.sql import map_sqlalchemy_error
from creator.invoice.ports import InvoiceRepository
from creator.invoice.repository import SqlAlchemyInvoiceRepository
from creator.notification.repository import (
    SqlAlchemyNotificationPreferenceRepository,
    SqlAlchemyNotificationRecipientRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyUserDeviceRepository,
)
from creator.order.ports import OrderRepository
from creator.order.repository import SqlAlchemyOrderRepository
from creator.payment_method.ports import BillingPaymentMethodRepository
from creator.payment_method.repository import SqlAlchemyBillingPaymentMethodRepository
from creator.persona.ports import PersonaRepository
from creator.persona.repository import SqlAlchemyPersonaRepository
from creator.plan.repository import SqlAlchemyPlanItemRepository, SqlAlchemyPlanRepository
from creator.planning.ports import PlanningRepository
from creator.planning.repository import SqlAlchemyPlanningRepository
from creator.post_structure.ports import PostStructureRepository
from creator.post_structure.repository import SqlAlchemyPostStructureRepository
from creator.project.ports import ProjectRepository
from creator.project.repository import SqlAlchemyProjectRepository
from creator.refund.ports import RefundRepository
from creator.refund.repository import SqlAlchemyRefundRepository
from creator.subscription.repository import (
    SqlAlchemySubscriptionHistoryRepository,
    SqlAlchemySubscriptionRepository,
)
from creator.uow import (
    BillingAccountRepositories,
    BillingProviderRepositories,
    BrandRepositories,
    CouponRepositories,
    GenerationRepositories,
    NotificationRepositories,
    PlanRepositories,
    SubscriptionRepositories,
    UnitOfWork,
    UserRepositories,
    WorkflowRepositories,
    WorkspaceRepositories,
)
from creator.user.repository import SqlAlchemySettingsRepository, SqlAlchemyUserRepository
from creator.workflow.ports import OutboxRepository
from creator.workflow.repository import (
    SqlAlchemyAgentWorkflowRepository,
    SqlAlchemyOutboxRepository,
)
from creator.workspace.repository import (
    SqlAlchemyWorkspaceInviteRepository,
    SqlAlchemyWorkspaceInviteUsageRepository,
    SqlAlchemyWorkspaceRepository,
)

SessionFactory = Callable[[], Session]
logger = logging.getLogger(__name__)


class SqlAlchemyUnitOfWork(UnitOfWork):
    auth_sessions: AuthSessionRepository
    user: UserRepositories
    workspace: WorkspaceRepositories
    brand: BrandRepositories
    projects: ProjectRepository
    contents: ContentRepository
    generation: GenerationRepositories
    assets: AssetRepository
    campaigns: CampaignRepository
    post_structures: PostStructureRepository
    planning: PlanningRepository
    personas: PersonaRepository
    agent_workflow: WorkflowRepositories
    outbox: OutboxRepository
    notification: NotificationRepositories
    plan: PlanRepositories
    billing_account: BillingAccountRepositories
    billing_provider: BillingProviderRepositories
    coupon: CouponRepositories
    subscription: SubscriptionRepositories
    invoices: InvoiceRepository
    charges: ChargeRepository
    billing_payment_methods: BillingPaymentMethodRepository
    credit_packages: CreditPackageRepository
    orders: OrderRepository
    workspace_credit_transactions: WorkspaceCreditTransactionRepository
    refunds: RefundRepository
    design_structures: DesignStructureRepository

    def __init__(self, session_factory: SessionFactory = SessionLocal) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._committed = False
        self._started_at = 0.0

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        session = self._session_factory()
        self._session = session
        self._started_at = time.perf_counter()
        users = SqlAlchemyUserRepository(session)
        self.auth_sessions = SqlAlchemyAuthSessionRepository(session)
        settings = SqlAlchemySettingsRepository(session)
        workspaces = SqlAlchemyWorkspaceRepository(session)
        brands = SqlAlchemyBrandRepository(session)
        self.projects = SqlAlchemyProjectRepository(session)
        self.contents = SqlAlchemyContentRepository(session)
        generations = SqlAlchemyGenerationRepository(session)
        self.assets = SqlAlchemyAssetRepository(session)
        brand_assets = SqlAlchemyBrandAssetRepository(session)
        self.campaigns = SqlAlchemyCampaignRepository(session)
        self.post_structures = SqlAlchemyPostStructureRepository(session)
        self.planning = SqlAlchemyPlanningRepository(session)
        self.personas = SqlAlchemyPersonaRepository(session)
        generated_images = SqlAlchemyGeneratedImageRepository(session)
        brand_settings = SqlAlchemyBrandSettingsRepository(session)
        image_generations = SqlAlchemyImageGenerationRepository(session)
        agent_workflows = SqlAlchemyAgentWorkflowRepository(session)
        self.outbox = SqlAlchemyOutboxRepository(session)
        user_devices = SqlAlchemyUserDeviceRepository(session)
        notification_preferences = SqlAlchemyNotificationPreferenceRepository(session)
        notifications = SqlAlchemyNotificationRepository(session)
        notification_recipients = SqlAlchemyNotificationRecipientRepository(session)
        plans = SqlAlchemyPlanRepository(session)
        billing_accounts = SqlAlchemyBillingAccountRepository(session)
        plan_items = SqlAlchemyPlanItemRepository(session)
        subscriptions = SqlAlchemySubscriptionRepository(session)
        self.invoices = SqlAlchemyInvoiceRepository(session)
        self.charges = SqlAlchemyChargeRepository(session)
        workspace_invites = SqlAlchemyWorkspaceInviteRepository(session)
        billing_addresses = SqlAlchemyBillingAddressRepository(session)
        self.billing_payment_methods = SqlAlchemyBillingPaymentMethodRepository(session)
        coupons = SqlAlchemyCouponRepository(session)
        self.credit_packages = SqlAlchemyCreditPackageRepository(session)
        self.orders = SqlAlchemyOrderRepository(session)
        coupon_redemptions = SqlAlchemyCouponRedemptionRepository(session)
        self.workspace_credit_transactions = SqlAlchemyWorkspaceCreditTransactionRepository(session)
        self.refunds = SqlAlchemyRefundRepository(session)
        provider_disputes = SqlAlchemyProviderDisputeRepository(session)
        provider_customers = SqlAlchemyProviderCustomerRepository(session)
        provider_subscriptions = SqlAlchemyProviderSubscriptionRepository(session)
        provider_webhook_events = SqlAlchemyProviderWebhookEventRepository(session)
        provider_idempotency_keys = SqlAlchemyProviderIdempotencyKeyRepository(session)
        self.design_structures = SqlAlchemyDesignStructureRepository(session)
        brand_colors = SqlAlchemyBrandColorRepository(session)
        subscription_history = SqlAlchemySubscriptionHistoryRepository(session)
        workspace_invite_usages = SqlAlchemyWorkspaceInviteUsageRepository(session)

        self.user = UserRepositories(users=users, settings=settings)
        self.workspace = WorkspaceRepositories(
            workspaces=workspaces, invites=workspace_invites, invite_usages=workspace_invite_usages
        )
        self.brand = BrandRepositories(
            brands=brands, assets=brand_assets, settings=brand_settings, colors=brand_colors
        )
        self.generation = GenerationRepositories(
            generations=generations,
            generated_images=generated_images,
            image_jobs=image_generations,
        )
        self.agent_workflow = WorkflowRepositories(workflows=agent_workflows)
        self.notification = NotificationRepositories(
            devices=user_devices,
            preferences=notification_preferences,
            notifications=notifications,
            recipients=notification_recipients,
        )
        self.plan = PlanRepositories(plans=plans, items=plan_items)
        self.billing_account = BillingAccountRepositories(
            accounts=billing_accounts, addresses=billing_addresses
        )
        self.billing_provider = BillingProviderRepositories(
            customers=provider_customers,
            disputes=provider_disputes,
            idempotency_keys=provider_idempotency_keys,
            subscriptions=provider_subscriptions,
            webhook_events=provider_webhook_events,
        )
        self.coupon = CouponRepositories(coupons=coupons, redemptions=coupon_redemptions)
        self.subscription = SubscriptionRepositories(
            subscriptions=subscriptions, history=subscription_history
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._require_session()
        try:
            if exc_type is not None or not self._committed:
                session.rollback()
                logger.info(
                    "unit_of_work_rollback",
                    extra={
                        "exception_type": exc_type.__name__ if exc_type else None,
                        "duration_ms": int((time.perf_counter() - self._started_at) * 1000),
                    },
                )
        finally:
            session.close()

    def commit(self) -> None:
        session = self._require_session()
        try:
            session.commit()
        except SQLAlchemyError as error:
            session.rollback()
            logger.error(
                "unit_of_work_commit_failed",
                extra={"exception_type": error.__class__.__name__},
            )
            raise map_sqlalchemy_error(error) from error
        self._committed = True
        logger.info(
            "unit_of_work_commit",
            extra={"duration_ms": int((time.perf_counter() - self._started_at) * 1000)},
        )

    def rollback(self) -> None:
        self._require_session().rollback()
        self._committed = False
        logger.info(
            "unit_of_work_explicit_rollback",
            extra={"duration_ms": int((time.perf_counter() - self._started_at) * 1000)},
        )

    def _require_session(self) -> Session:
        if self._session is None:
            raise PersistenceError("Unit of Work is not active")
        return self._session


def get_unit_of_work() -> Generator[SqlAlchemyUnitOfWork, None, None]:
    with SqlAlchemyUnitOfWork() as unit_of_work:
        yield unit_of_work
