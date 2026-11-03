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
from creator.billing_account.ports import BillingAccountRepository, BillingAddressRepository
from creator.billing_account.repository import (
    SqlAlchemyBillingAccountRepository,
    SqlAlchemyBillingAddressRepository,
)
from creator.billing_provider.ports import (
    ProviderCustomerRepository,
    ProviderDisputeRepository,
    ProviderIdempotencyKeyRepository,
    ProviderSubscriptionRepository,
    ProviderWebhookEventRepository,
)
from creator.billing_provider.repository import (
    SqlAlchemyProviderCustomerRepository,
    SqlAlchemyProviderDisputeRepository,
    SqlAlchemyProviderIdempotencyKeyRepository,
    SqlAlchemyProviderSubscriptionRepository,
    SqlAlchemyProviderWebhookEventRepository,
)
from creator.brand.ports import (
    BrandAssetRepository,
    BrandColorRepository,
    BrandRepository,
    BrandSettingsRepository,
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
from creator.coupon.ports import CouponRedemptionRepository, CouponRepository
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
from creator.generation.ports import (
    GeneratedImageRepository,
    GenerationRepository,
    ImageGenerationRepository,
)
from creator.generation.repository import (
    SqlAlchemyGeneratedImageRepository,
    SqlAlchemyGenerationRepository,
    SqlAlchemyImageGenerationRepository,
)
from creator.infrastructure.database.db import SessionLocal
from creator.infrastructure.persistence.sql import map_sqlalchemy_error
from creator.invoice.ports import InvoiceRepository
from creator.invoice.repository import SqlAlchemyInvoiceRepository
from creator.notification.ports import (
    NotificationPreferenceRepository,
    NotificationRecipientRepository,
    NotificationRepository,
    UserDeviceRepository,
)
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
from creator.plan.ports import PlanItemRepository, PlanRepository
from creator.plan.repository import SqlAlchemyPlanItemRepository, SqlAlchemyPlanRepository
from creator.planning.ports import PlanningRepository
from creator.planning.repository import SqlAlchemyPlanningRepository
from creator.post_structure.ports import PostStructureRepository
from creator.post_structure.repository import SqlAlchemyPostStructureRepository
from creator.project.ports import ProjectRepository
from creator.project.repository import SqlAlchemyProjectRepository
from creator.refund.ports import RefundRepository
from creator.refund.repository import SqlAlchemyRefundRepository
from creator.subscription.ports import SubscriptionHistoryRepository, SubscriptionRepository
from creator.subscription.repository import (
    SqlAlchemySubscriptionHistoryRepository,
    SqlAlchemySubscriptionRepository,
)
from creator.uow import UnitOfWork
from creator.user.ports import SettingsRepository, UserRepository
from creator.user.repository import SqlAlchemySettingsRepository, SqlAlchemyUserRepository
from creator.workflow.ports import AgentWorkflowRepository, OutboxRepository
from creator.workflow.repository import (
    SqlAlchemyAgentWorkflowRepository,
    SqlAlchemyOutboxRepository,
)
from creator.workspace.ports import (
    WorkspaceInviteRepository,
    WorkspaceInviteUsageRepository,
    WorkspaceRepository,
)
from creator.workspace.repository import (
    SqlAlchemyWorkspaceInviteRepository,
    SqlAlchemyWorkspaceInviteUsageRepository,
    SqlAlchemyWorkspaceRepository,
)

SessionFactory = Callable[[], Session]
logger = logging.getLogger(__name__)


class SqlAlchemyUnitOfWork(UnitOfWork):
    users: UserRepository
    auth_sessions: AuthSessionRepository
    settings: SettingsRepository
    workspaces: WorkspaceRepository
    brands: BrandRepository
    projects: ProjectRepository
    contents: ContentRepository
    generations: GenerationRepository
    assets: AssetRepository
    campaigns: CampaignRepository
    post_structures: PostStructureRepository
    planning: PlanningRepository
    personas: PersonaRepository
    generated_images: GeneratedImageRepository
    brand_assets: BrandAssetRepository
    brand_settings: BrandSettingsRepository
    image_generations: ImageGenerationRepository
    agent_workflows: AgentWorkflowRepository
    outbox: OutboxRepository
    user_devices: UserDeviceRepository
    notification_preferences: NotificationPreferenceRepository
    notifications: NotificationRepository
    notification_recipients: NotificationRecipientRepository
    plans: PlanRepository
    billing_accounts: BillingAccountRepository
    plan_items: PlanItemRepository
    subscriptions: SubscriptionRepository
    invoices: InvoiceRepository
    charges: ChargeRepository
    workspace_invites: WorkspaceInviteRepository
    billing_addresses: BillingAddressRepository
    billing_payment_methods: BillingPaymentMethodRepository
    coupons: CouponRepository
    credit_packages: CreditPackageRepository
    orders: OrderRepository
    coupon_redemptions: CouponRedemptionRepository
    workspace_credit_transactions: WorkspaceCreditTransactionRepository
    refunds: RefundRepository
    provider_disputes: ProviderDisputeRepository
    provider_customers: ProviderCustomerRepository
    provider_subscriptions: ProviderSubscriptionRepository
    provider_webhook_events: ProviderWebhookEventRepository
    provider_idempotency_keys: ProviderIdempotencyKeyRepository
    design_structures: DesignStructureRepository
    brand_colors: BrandColorRepository
    subscription_history: SubscriptionHistoryRepository
    workspace_invite_usages: WorkspaceInviteUsageRepository

    def __init__(self, session_factory: SessionFactory = SessionLocal) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._committed = False
        self._started_at = 0.0

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        session = self._session_factory()
        self._session = session
        self._started_at = time.perf_counter()
        self.users = SqlAlchemyUserRepository(session)
        self.auth_sessions = SqlAlchemyAuthSessionRepository(session)
        self.settings = SqlAlchemySettingsRepository(session)
        self.workspaces = SqlAlchemyWorkspaceRepository(session)
        self.brands = SqlAlchemyBrandRepository(session)
        self.projects = SqlAlchemyProjectRepository(session)
        self.contents = SqlAlchemyContentRepository(session)
        self.generations = SqlAlchemyGenerationRepository(session)
        self.assets = SqlAlchemyAssetRepository(session)
        self.brand_assets = SqlAlchemyBrandAssetRepository(session)
        self.campaigns = SqlAlchemyCampaignRepository(session)
        self.post_structures = SqlAlchemyPostStructureRepository(session)
        self.planning = SqlAlchemyPlanningRepository(session)
        self.personas = SqlAlchemyPersonaRepository(session)
        self.generated_images = SqlAlchemyGeneratedImageRepository(session)
        self.brand_settings = SqlAlchemyBrandSettingsRepository(session)
        self.image_generations = SqlAlchemyImageGenerationRepository(session)
        self.agent_workflows = SqlAlchemyAgentWorkflowRepository(session)
        self.outbox = SqlAlchemyOutboxRepository(session)
        self.user_devices = SqlAlchemyUserDeviceRepository(session)
        self.notification_preferences = SqlAlchemyNotificationPreferenceRepository(session)
        self.notifications = SqlAlchemyNotificationRepository(session)
        self.notification_recipients = SqlAlchemyNotificationRecipientRepository(session)
        self.plans = SqlAlchemyPlanRepository(session)
        self.billing_accounts = SqlAlchemyBillingAccountRepository(session)
        self.plan_items = SqlAlchemyPlanItemRepository(session)
        self.subscriptions = SqlAlchemySubscriptionRepository(session)
        self.invoices = SqlAlchemyInvoiceRepository(session)
        self.charges = SqlAlchemyChargeRepository(session)
        self.workspace_invites = SqlAlchemyWorkspaceInviteRepository(session)
        self.billing_addresses = SqlAlchemyBillingAddressRepository(session)
        self.billing_payment_methods = SqlAlchemyBillingPaymentMethodRepository(session)
        self.coupons = SqlAlchemyCouponRepository(session)
        self.credit_packages = SqlAlchemyCreditPackageRepository(session)
        self.orders = SqlAlchemyOrderRepository(session)
        self.coupon_redemptions = SqlAlchemyCouponRedemptionRepository(session)
        self.workspace_credit_transactions = SqlAlchemyWorkspaceCreditTransactionRepository(session)
        self.refunds = SqlAlchemyRefundRepository(session)
        self.provider_disputes = SqlAlchemyProviderDisputeRepository(session)
        self.provider_customers = SqlAlchemyProviderCustomerRepository(session)
        self.provider_subscriptions = SqlAlchemyProviderSubscriptionRepository(session)
        self.provider_webhook_events = SqlAlchemyProviderWebhookEventRepository(session)
        self.provider_idempotency_keys = SqlAlchemyProviderIdempotencyKeyRepository(session)
        self.design_structures = SqlAlchemyDesignStructureRepository(session)
        self.brand_colors = SqlAlchemyBrandColorRepository(session)
        self.subscription_history = SqlAlchemySubscriptionHistoryRepository(session)
        self.workspace_invite_usages = SqlAlchemyWorkspaceInviteUsageRepository(session)
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
