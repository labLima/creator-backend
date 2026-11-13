from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self

from creator.activity_event.ports import ActivityEventRepository
from creator.asset.ports import AssetRepository
from creator.auth.ports import AuthSessionRepository
from creator.billing_account.ports import BillingAccountRepository, BillingAddressRepository
from creator.billing_provider.ports import (
    ProviderDisputeRepository,
    ProviderIdempotencyKeyRepository,
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


@dataclass(frozen=True, slots=True)
class UserRepositories:
    users: UserRepository
    settings: SettingsRepository


@dataclass(frozen=True, slots=True)
class WorkspaceRepositories:
    workspaces: WorkspaceRepository
    invites: WorkspaceInviteRepository
    invite_usages: WorkspaceInviteUsageRepository


@dataclass(frozen=True, slots=True)
class BrandRepositories:
    brands: BrandRepository
    assets: BrandAssetRepository
    settings: BrandSettingsRepository
    colors: BrandColorRepository


@dataclass(frozen=True, slots=True)
class GenerationRepositories:
    generations: GenerationRepository
    generated_images: GeneratedImageRepository
    image_jobs: ImageGenerationRepository


@dataclass(frozen=True, slots=True)
class NotificationRepositories:
    devices: UserDeviceRepository
    preferences: NotificationPreferenceRepository
    notifications: NotificationRepository
    recipients: NotificationRecipientRepository


@dataclass(frozen=True, slots=True)
class PlanRepositories:
    plans: PlanRepository
    items: PlanItemRepository


@dataclass(frozen=True, slots=True)
class BillingAccountRepositories:
    accounts: BillingAccountRepository
    addresses: BillingAddressRepository


@dataclass(frozen=True, slots=True)
class BillingProviderRepositories:
    disputes: ProviderDisputeRepository
    idempotency_keys: ProviderIdempotencyKeyRepository
    webhook_events: ProviderWebhookEventRepository


@dataclass(frozen=True, slots=True)
class CouponRepositories:
    coupons: CouponRepository
    redemptions: CouponRedemptionRepository


@dataclass(frozen=True, slots=True)
class SubscriptionRepositories:
    subscriptions: SubscriptionRepository
    history: SubscriptionHistoryRepository


@dataclass(frozen=True, slots=True)
class WorkflowRepositories:
    workflows: AgentWorkflowRepository


class UnitOfWork(Protocol):
    activity_events: ActivityEventRepository
    auth_sessions: AuthSessionRepository
    user: UserRepositories
    workspace: WorkspaceRepositories
    brand: BrandRepositories
    projects: ProjectRepository
    contents: ContentRepository
    generation: GenerationRepositories
    assets: AssetRepository
    agent_workflow: WorkflowRepositories
    campaigns: CampaignRepository
    post_structures: PostStructureRepository
    planning: PlanningRepository
    personas: PersonaRepository
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

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
