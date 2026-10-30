from types import TracebackType
from typing import Protocol, Self

from creator.auth.ports import AuthSessionRepository
from creator.brand.ports import (
    BrandAssetRepository,
    BrandColorRepository,
    BrandRepository,
    BrandSettingsRepository,
)
from creator.repositories.agent_workflows import AgentWorkflowRepository
from creator.repositories.billing import (
    BillingAccountRepository,
    BillingAddressRepository,
    BillingPaymentMethodRepository,
    ChargeRepository,
    InvoiceRepository,
    PlanItemRepository,
    PlanRepository,
    SubscriptionRepository,
)
from creator.repositories.catalog import CouponRepository, CreditPackageRepository
from creator.repositories.commerce import (
    CouponRedemptionRepository,
    OrderRepository,
    WorkspaceCreditTransactionRepository,
)
from creator.repositories.content import ContentRepository
from creator.repositories.core import AssetRepository, GenerationRepository, ProjectRepository
from creator.repositories.design import DesignStructureRepository
from creator.repositories.image_generation import ImageGenerationRepository
from creator.repositories.notifications import (
    NotificationPreferenceRepository,
    NotificationRecipientRepository,
    NotificationRepository,
    UserDeviceRepository,
)
from creator.repositories.outbox import OutboxRepository
from creator.repositories.provider import ProviderDisputeRepository, RefundRepository
from creator.repositories.provider_audit import (
    ProviderIdempotencyKeyRepository,
    ProviderWebhookEventRepository,
)
from creator.repositories.provider_sync import (
    ProviderCustomerRepository,
    ProviderSubscriptionRepository,
)
from creator.repositories.schema import (
    CampaignRepository,
    GeneratedImageRepository,
    PersonaRepository,
    PlanningRepository,
    PostStructureRepository,
)
from creator.repositories.subscription_history import SubscriptionHistoryRepository
from creator.user.ports import SettingsRepository, UserRepository
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
