from types import TracebackType
from typing import Protocol, Self

from creator.asset.ports import AssetRepository
from creator.auth.ports import AuthSessionRepository
from creator.billing_account.ports import BillingAccountRepository, BillingAddressRepository
from creator.billing_provider.ports import (
    ProviderCustomerRepository,
    ProviderDisputeRepository,
    ProviderIdempotencyKeyRepository,
    ProviderSubscriptionRepository,
    ProviderWebhookEventRepository,
)
from creator.brand.ports import (
    BrandAssetRepository,
    BrandColorRepository,
    BrandRepository,
    BrandSettingsRepository,
)
from creator.campaign.ports import CampaignRepository
from creator.charge.ports import ChargeRepository
from creator.content.ports import ContentRepository
from creator.coupon.ports import CouponRedemptionRepository, CouponRepository
from creator.credit.ports import WorkspaceCreditTransactionRepository
from creator.credit_package.ports import CreditPackageRepository
from creator.design_structure.ports import DesignStructureRepository
from creator.generation.ports import (
    GeneratedImageRepository,
    GenerationRepository,
    ImageGenerationRepository,
)
from creator.invoice.ports import InvoiceRepository
from creator.notification.ports import (
    NotificationPreferenceRepository,
    NotificationRecipientRepository,
    NotificationRepository,
    UserDeviceRepository,
)
from creator.order.ports import OrderRepository
from creator.payment_method.ports import BillingPaymentMethodRepository
from creator.persona.ports import PersonaRepository
from creator.plan.ports import PlanItemRepository, PlanRepository
from creator.planning.ports import PlanningRepository
from creator.post_structure.ports import PostStructureRepository
from creator.project.ports import ProjectRepository
from creator.refund.ports import RefundRepository
from creator.subscription.ports import SubscriptionHistoryRepository, SubscriptionRepository
from creator.user.ports import SettingsRepository, UserRepository
from creator.workflow.ports import AgentWorkflowRepository, OutboxRepository
from creator.workspace.ports import (
    WorkspaceInviteRepository,
    WorkspaceInviteUsageRepository,
    WorkspaceRepository,
)


class UnitOfWork(Protocol):
    users: UserRepository
    auth_sessions: AuthSessionRepository
    settings: SettingsRepository
    workspaces: WorkspaceRepository
    brands: BrandRepository
    projects: ProjectRepository
    contents: ContentRepository
    generations: GenerationRepository
    assets: AssetRepository
    brand_settings: BrandSettingsRepository
    image_generations: ImageGenerationRepository
    agent_workflows: AgentWorkflowRepository
    campaigns: CampaignRepository
    post_structures: PostStructureRepository
    planning: PlanningRepository
    personas: PersonaRepository
    generated_images: GeneratedImageRepository
    brand_assets: BrandAssetRepository
    outbox: OutboxRepository
    user_devices: UserDeviceRepository
    notification_preferences: NotificationPreferenceRepository
    notifications: NotificationRepository
    notification_recipients: NotificationRecipientRepository
    plans: PlanRepository
    plan_items: PlanItemRepository
    billing_accounts: BillingAccountRepository
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

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
