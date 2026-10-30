"""Database enums used by the SQLAlchemy models."""

from enum import StrEnum

from sqlalchemy import Enum as SQLEnum

from creator.domain.agent_workflow import (
    AgentWorkflowStatus,
    AgentWorkflowStepRole,
    AgentWorkflowStepStatus,
    HumanReviewMode,
)
from creator.domain.auth import WorkspaceRole
from creator.domain.generation import GenerationJobStatus


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_type]


class GlobalRole(StrEnum):
    ADMIN = "admin"
    GESTOR = "gestor"
    MEMBRO = "membro"


class ContentType(StrEnum):
    IMAGE = "IMAGE"
    TEXT = "TEXT"


class GenerationType(StrEnum):
    IMAGE = "IMAGE"
    TEXT = "TEXT"
    COPY = "COPY"
    CAPTION = "CAPTION"


global_role_enum = SQLEnum(
    GlobalRole,
    name="global_role",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
workspace_role_enum = SQLEnum(
    WorkspaceRole,
    name="workspace_role",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
content_type_enum = SQLEnum(
    ContentType,
    name="content_type",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
generation_type_enum = SQLEnum(
    GenerationType,
    name="generation_type",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
generation_job_status_enum = SQLEnum(
    GenerationJobStatus,
    name="generation_job_status",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
agent_workflow_status_enum = SQLEnum(
    AgentWorkflowStatus,
    name="agent_workflow_status",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
agent_workflow_step_status_enum = SQLEnum(
    AgentWorkflowStepStatus,
    name="agent_workflow_step_status",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
agent_workflow_step_role_enum = SQLEnum(
    AgentWorkflowStepRole,
    name="agent_workflow_step_role",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)
human_review_mode_enum = SQLEnum(
    HumanReviewMode,
    name="human_review_mode",
    native_enum=False,
    create_constraint=True,
    values_callable=enum_values,
    validate_strings=True,
)


class InviteType(StrEnum):
    EMAIL = "EMAIL"
    LINK = "LINK"


class InviteStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REVOKED = "REVOKED"


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    TRIALING = "TRIALING"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class ProviderSubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    FUTURE = "FUTURE"


class PaymentMethodType(StrEnum):
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BOLETO = "BOLETO"
    PIX = "PIX"


class PlanType(StrEnum):
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    STUDIO = "STUDIO"
    ENTERPRISE = "ENTERPRISE"


class CampaignVoice(StrEnum):
    INSPIRATIONAL = "INSPIRATIONAL"
    MOTIVATIONAL = "MOTIVATIONAL"
    PROFESSIONAL = "PROFESSIONAL"
    CASUAL = "CASUAL"
    ELEGANT = "ELEGANT"
    MODERN = "MODERN"
    TRADITIONAL = "TRADITIONAL"
    FUN = "FUN"
    SERIOUS = "SERIOUS"


class PostStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ContentFormat(StrEnum):
    IMAGE = "IMAGE"
    CAROUSEL = "CAROUSEL"
    STORIES = "STORIES"


class ArtRatio(StrEnum):
    RATIO_4_5 = "RATIO_4_5"
    RATIO_1_1 = "RATIO_1_1"
    RATIO_9_16 = "RATIO_9_16"
    RATIO_16_9 = "RATIO_16_9"


class ArtResolution(StrEnum):
    HD_1080X1080 = "HD_1080X1080"
    HD_1080X1350 = "HD_1080X1350"
    FULL_HD_1080X1920 = "FULL_HD_1080X1920"
    FULL_HD_1920X1080 = "FULL_HD_1920X1080"


class ImageStatus(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


__all__ = [
    "ImageStatus",
    "ArtResolution",
    "ArtRatio",
    "ContentFormat",
    "PostStatus",
    "CampaignVoice",
    "PlanType",
    "PaymentMethodType",
    "ProviderSubscriptionStatus",
    "SubscriptionStatus",
    "InviteStatus",
    "InviteType",
    "ContentType",
    "GenerationType",
    "GlobalRole",
    "WorkspaceRole",
    "agent_workflow_status_enum",
    "agent_workflow_step_role_enum",
    "agent_workflow_step_status_enum",
    "content_type_enum",
    "enum_values",
    "generation_job_status_enum",
    "generation_type_enum",
    "global_role_enum",
    "human_review_mode_enum",
    "workspace_role_enum",
]
