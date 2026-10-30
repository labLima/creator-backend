"""Response payload mappers.

Moved verbatim from `creator.main`; output is frozen by
`tests/test_serializer_contract.py`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from creator.api.responses import page_payload
from creator.brand.ports import BrandRecord, BrandSettingsRecord
from creator.content.improvement_service import (
    ImprovedContentPreview,
)
from creator.core.pagination import Page
from creator.repositories.content import ContentDetailRecord, ContentRecord
from creator.repositories.core import AssetRecord, GenerationRecord, ProjectRecord
from creator.repositories.image_generation import ImageGenerationStatusRecord, ImageRecord
from creator.user.ports import SettingsRecord, UserRecord
from creator.workspace.ports import WorkspaceMembershipRecord, WorkspaceRecord


def _workspace_data(workspace: WorkspaceRecord) -> dict[str, Any]:
    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
        "deleted_at": workspace.deleted_at.isoformat() if workspace.deleted_at else None,
    }


def _workspace_membership_data(membership: WorkspaceMembershipRecord) -> dict[str, Any]:
    return {
        "id": str(membership.id),
        "workspace_id": str(membership.workspace_id),
        "user_id": str(membership.user_id),
        "role": membership.role,
        "created_at": membership.created_at.isoformat(),
        "updated_at": membership.updated_at.isoformat(),
        "deleted_at": membership.deleted_at.isoformat() if membership.deleted_at else None,
    }


def _user_data(user: UserRecord) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "external_id": user.external_id,
        "email": user.email,
        "display_name": user.display_name,
        "global_role": user.global_role,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
    }


def _settings_data(settings: SettingsRecord) -> dict[str, Any]:
    return {
        "id": str(settings.id),
        "user_id": str(settings.user_id),
        "brand_name": settings.brand_name,
        "segment": settings.segment,
        "tone": settings.tone,
        "voice": settings.voice,
        "visual_style": settings.visual_style,
        "default_preferences": settings.default_preferences,
        "created_at": settings.created_at.isoformat(),
        "updated_at": settings.updated_at.isoformat(),
    }


def _brand_data(brand: BrandRecord) -> dict[str, Any]:
    return {
        "id": str(brand.id),
        "workspace_id": str(brand.workspace_id),
        "created_by_user_id": str(brand.created_by_user_id) if brand.created_by_user_id else None,
        "name": brand.name,
        "description": brand.description,
        "brand_voice": brand.brand_voice,
        "metadata": brand.metadata,
        "created_at": brand.created_at.isoformat(),
        "updated_at": brand.updated_at.isoformat(),
        "deleted_at": brand.deleted_at.isoformat() if brand.deleted_at else None,
    }


def _project_data(project: ProjectRecord) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "workspace_id": str(project.workspace_id),
        "brand_id": str(project.brand_id) if project.brand_id else None,
        "created_by_user_id": str(project.created_by_user_id)
        if project.created_by_user_id
        else None,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "metadata": project.metadata,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
    }


def _campaign_data(campaign: Any) -> dict[str, Any]:
    return {
        "id": str(campaign.id),
        "workspace_id": str(campaign.workspace_id),
        "created_by": str(campaign.created_by),
        "name": campaign.name,
        "description": campaign.description,
        "target_audience": campaign.target_audience,
        "objectives": campaign.objectives,
        "voice": campaign.voice,
        "start_at": campaign.start_at.isoformat() if campaign.start_at else None,
        "end_at": campaign.end_at.isoformat() if campaign.end_at else None,
        "created_at": campaign.created_at.isoformat(),
        "updated_at": campaign.updated_at.isoformat(),
        "deleted_at": campaign.deleted_at.isoformat() if campaign.deleted_at else None,
    }


def _post_structure_data(post_structure: Any) -> dict[str, Any]:
    return {
        "id": str(post_structure.id),
        "workspace_id": str(post_structure.workspace_id),
        "planning_id": str(post_structure.planning_id),
        "created_by": str(post_structure.created_by),
        "title": post_structure.title,
        "objective": post_structure.objective,
        "big_idea": post_structure.big_idea,
        "main_message": post_structure.main_message,
        "headline": post_structure.headline,
        "image_cta": post_structure.image_cta,
        "art_guiding": post_structure.art_guiding,
        "status": post_structure.status,
        "format": post_structure.format,
        "ratio": post_structure.ratio,
        "resolution": post_structure.resolution,
        "created_at": post_structure.created_at.isoformat(),
        "updated_at": post_structure.updated_at.isoformat(),
        "deleted_at": post_structure.deleted_at.isoformat() if post_structure.deleted_at else None,
    }


def _planning_data(planning: Any) -> dict[str, Any]:
    return {
        "id": str(planning.id),
        "brand_id": str(planning.brand_id),
        "campaign_id": str(planning.campaign_id),
        "persona_id": str(planning.persona_id),
        "created_by": str(planning.created_by),
        "info": planning.info,
        "static_amount": planning.static_amount,
        "carousel_amount": planning.carousel_amount,
        "stories_amount": planning.stories_amount,
        "special_dates": planning.special_dates,
        "start_period": planning.start_period.isoformat() if planning.start_period else None,
        "end_period": planning.end_period.isoformat() if planning.end_period else None,
        "created_at": planning.created_at.isoformat(),
        "updated_at": planning.updated_at.isoformat(),
        "deleted_at": planning.deleted_at.isoformat() if planning.deleted_at else None,
    }


def _persona_data(persona: Any) -> dict[str, Any]:
    return {
        "id": str(persona.id),
        "brand_id": str(persona.brand_id),
        "created_by": str(persona.created_by),
        "name": persona.name,
        "age": persona.age,
        "gender": persona.gender,
        "main_goal": persona.main_goal,
        "challenge": persona.challenge,
        "interest": persona.interest,
        "routine": persona.routine,
        "journey": persona.journey,
        "trigger": persona.trigger,
        "created_at": persona.created_at.isoformat(),
        "updated_at": persona.updated_at.isoformat(),
        "deleted_at": persona.deleted_at.isoformat() if persona.deleted_at else None,
    }


def _brand_asset_data(asset: Any) -> dict[str, Any]:
    return {
        "id": str(asset.id),
        "brand_id": str(asset.brand_id),
        "type": asset.type,
        "file_url": asset.file_url,
        "file_name": asset.file_name,
        "description": asset.description,
        "created_at": asset.created_at.isoformat(),
        "updated_at": asset.updated_at.isoformat(),
        "deleted_at": asset.deleted_at.isoformat() if asset.deleted_at else None,
    }


def _user_device_data(device: Any) -> dict[str, Any]:
    return {
        "id": str(device.id),
        "user_id": str(device.user_id),
        "platform": device.platform,
        "fcm_token": device.fcm_token,
        "is_active": device.is_active,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "created_at": device.created_at.isoformat(),
        "updated_at": device.updated_at.isoformat(),
        "deleted_at": device.deleted_at.isoformat() if device.deleted_at else None,
    }


def _notification_preference_data(preference: Any) -> dict[str, Any]:
    return {
        "id": str(preference.id),
        "user_id": str(preference.user_id),
        "type": preference.type,
        "channel": preference.channel,
        "is_enabled": preference.is_enabled,
        "created_at": preference.created_at.isoformat(),
        "updated_at": preference.updated_at.isoformat(),
        "deleted_at": preference.deleted_at.isoformat() if preference.deleted_at else None,
    }


def _notification_data(notification: Any) -> dict[str, Any]:
    return {
        "id": str(notification.id),
        "workspace_id": str(notification.workspace_id),
        "type": notification.type,
        "title": notification.title,
        "body": notification.body,
        "payload": notification.payload,
        "resource_type": notification.resource_type,
        "resource_id": str(notification.resource_id) if notification.resource_id else None,
        "created_by": str(notification.created_by) if notification.created_by else None,
        "created_at": notification.created_at.isoformat(),
        "updated_at": notification.updated_at.isoformat(),
        "deleted_at": notification.deleted_at.isoformat() if notification.deleted_at else None,
    }


def _plan_data(plan: Any) -> dict[str, Any]:
    return {
        "id": str(plan.id),
        "code": plan.code,
        "type": plan.type,
        "name": plan.name,
        "description": plan.description,
        "metadata": plan.metadata,
        "is_active": plan.is_active,
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat(),
        "deleted_at": plan.deleted_at.isoformat() if plan.deleted_at else None,
    }


def _plan_item_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "plan_id": str(item.plan_id),
        "name": item.name,
        "description": item.description,
        "quantity": item.quantity,
        "cycles": item.cycles,
        "pricing_scheme_type": item.pricing_scheme_type,
        "price_cents": item.price_cents,
        "price_brackets": item.price_brackets,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _billing_account_data(account: Any) -> dict[str, Any]:
    return {
        "id": str(account.id),
        "user_id": str(account.user_id),
        "payer_type": account.payer_type,
        "name": account.name,
        "email": account.email,
        "phone": account.phone,
        "document": account.document,
        "document_type": account.document_type,
        "company_name": account.company_name,
        "provider": account.provider,
        "provider_customer_id": account.provider_customer_id,
        "provider_customer_code": account.provider_customer_code,
        "delinquent": account.delinquent,
        "metadata": account.metadata,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
        "deleted_at": account.deleted_at.isoformat() if account.deleted_at else None,
    }


def _billing_address_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "street": item.street,
        "number": item.number,
        "complement": item.complement,
        "neighborhood": item.neighborhood,
        "zip_code": item.zip_code,
        "city": item.city,
        "state": item.state,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _payment_method_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "holder_name": item.holder_name,
        "holder_document": item.holder_document,
        "card_brand": item.card_brand,
        "card_last_four": item.card_last_four,
        "exp_month": item.exp_month,
        "exp_year": item.exp_year,
        "card_type": item.card_type,
        "card_status": item.card_status,
        "is_default": item.is_default,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _subscription_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "workspace_id": str(item.workspace_id),
        "plan_id": str(item.plan_id),
        "status": item.status,
        "payment_method": item.payment_method,
        "billing_day": item.billing_day,
        "start_at": item.start_at.isoformat() if item.start_at else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _invoice_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "subscription_id": str(item.subscription_id) if item.subscription_id else None,
        "amount_cents": item.amount_cents,
        "currency": item.currency,
        "status": item.status,
        "billing_at": item.billing_at.isoformat() if item.billing_at else None,
        "due_at": item.due_at.isoformat() if item.due_at else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _charge_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "invoice_id": str(item.invoice_id) if item.invoice_id else None,
        "amount_cents": item.amount_cents,
        "currency": item.currency,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _coupon_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "code": item.code,
        "type": item.type,
        "discount_percent": item.discount_percent,
        "credits_amount": item.credits_amount,
        "applies_to": item.applies_to,
        "min_purchase_cents": item.min_purchase_cents,
        "max_redemptions": item.max_redemptions,
        "once_per_workspace": item.once_per_workspace,
        "redemptions_count": item.redemptions_count,
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        "is_active": item.is_active,
        "internal_note": item.internal_note,
        "created_by": str(item.created_by) if item.created_by else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _credit_package_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "code": item.code,
        "name": item.name,
        "credits_amount": item.credits_amount,
        "price_cents": item.price_cents,
        "currency": item.currency,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _order_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "workspace_id": str(item.workspace_id),
        "credit_package_id": str(item.credit_package_id) if item.credit_package_id else None,
        "subtotal_cents": item.subtotal_cents,
        "discount_cents": item.discount_cents,
        "amount_cents": item.amount_cents,
        "currency": item.currency,
        "status": item.status,
        "closed": item.closed,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _coupon_redemption_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "coupon_id": str(item.coupon_id),
        "billing_account_id": str(item.billing_account_id),
        "order_id": str(item.order_id) if item.order_id else None,
        "subscription_id": str(item.subscription_id) if item.subscription_id else None,
        "discount_percent_applied": item.discount_percent_applied,
        "discount_amount_cents": item.discount_amount_cents,
        "credits_applied": item.credits_applied,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _workspace_invite_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "workspace_id": str(item.workspace_id),
        "type": item.type,
        "role": item.role,
        "email": item.email,
        "max_uses": item.max_uses,
        "uses_count": item.uses_count,
        "status": item.status,
        "is_active": item.is_active,
        "created_by": str(item.created_by),
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        "last_used_at": item.last_used_at.isoformat() if item.last_used_at else None,
        "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _workspace_credit_transaction_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "workspace_id": str(item.workspace_id),
        "amount": item.amount,
        "transaction_type": item.transaction_type,
        "reference_type": item.reference_type,
        "reference_id": str(item.reference_id) if item.reference_id else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _refund_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "invoice_id": str(item.invoice_id) if item.invoice_id else None,
        "amount_cents": item.amount_cents,
        "currency": item.currency,
        "reason": item.reason,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _provider_dispute_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "charge_id": str(item.charge_id) if item.charge_id else None,
        "code": item.code,
        "reason": item.reason,
        "status": item.status,
        "opened_at": item.opened_at.isoformat() if item.opened_at else None,
        "deadline_at": item.deadline_at.isoformat() if item.deadline_at else None,
        "payload": item.payload,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _provider_customer_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "billing_account_id": str(item.billing_account_id),
        "provider": item.provider,
        "provider_customer_id": item.provider_customer_id,
        "provider_code": item.provider_code,
        "metadata": item.metadata,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _provider_subscription_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "subscription_id": str(item.subscription_id),
        "provider": item.provider,
        "provider_subscription_id": item.provider_subscription_id,
        "provider_status": item.provider_status,
        "payload": item.payload,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _provider_webhook_event_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "provider": item.provider,
        "provider_event_id": item.provider_event_id,
        "dedupe_key": item.dedupe_key,
        "event_type": item.event_type,
        "account_id": item.account_id,
        "resource_type": item.resource_type,
        "resource_id": item.resource_id,
        "payload": item.payload,
        "signature_verified": item.signature_verified,
        "status": item.status,
        "attempts": item.attempts,
        "last_error": item.last_error,
        "received_at": item.received_at.isoformat(),
        "processed_at": item.processed_at.isoformat() if item.processed_at else None,
    }


def _provider_idempotency_key_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "provider": item.provider,
        "idempotency_key": item.idempotency_key,
        "request_hash": item.request_hash,
        "resource_type": item.resource_type,
        "resource_id": item.resource_id,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _design_structure_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "post_structure_id": str(item.post_structure_id),
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _brand_color_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "brand_id": str(item.brand_id),
        "workspace_id": str(item.workspace_id),
        "created_by": str(item.created_by),
        "order": item.order,
        "color_name": item.color_name,
        "hex_code": item.hex_code,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _subscription_history_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "subscription_id": str(item.subscription_id),
        "change_type": item.change_type,
        "previous_plan_id": str(item.previous_plan_id) if item.previous_plan_id else None,
        "plan_id": str(item.plan_id) if item.plan_id else None,
        "previous_status": item.previous_status,
        "status": item.status,
        "reason": item.reason,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _notification_recipient_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "notification_id": str(item.notification_id),
        "user_id": str(item.user_id),
        "workspace_member_id": str(item.workspace_member_id) if item.workspace_member_id else None,
        "channel": item.channel,
        "status": item.status,
        "attempts": item.attempts,
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
        "read_at": item.read_at.isoformat() if item.read_at else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _workspace_invite_usage_data(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "invite_id": str(item.invite_id),
        "user_id": str(item.user_id),
        "workspace_id": str(item.workspace_id),
        "member_id": str(item.member_id) if item.member_id else None,
        "used_at": item.used_at.isoformat(),
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None,
    }


def _generated_image_data(image: Any) -> dict[str, Any]:
    return {
        "id": str(image.id),
        "workspace_id": str(image.workspace_id),
        "design_structure_id": str(image.design_structure_id),
        "signed_url": image.signed_url,
        "size": image.size,
        "resolution": image.resolution,
        "image_ratio": image.image_ratio,
        "status": image.status,
        "created_at": image.created_at.isoformat(),
        "updated_at": image.updated_at.isoformat(),
        "deleted_at": image.deleted_at.isoformat() if image.deleted_at else None,
    }


def _content_data(
    content: ContentRecord,
    *,
    generation_id: UUID | None = None,
    generation_model: str | None = None,
    generation_parameters: dict[str, object] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(content.id),
        "workspace_id": str(content.workspace_id),
        "brand_id": str(content.brand_id) if content.brand_id else None,
        "project_id": str(content.project_id) if content.project_id else None,
        "created_by_user_id": str(content.created_by_user_id)
        if content.created_by_user_id
        else None,
        "type": content.content_type,
        "title": content.title,
        "payload": content.payload,
        "created_at": content.created_at.isoformat(),
        "updated_at": content.updated_at.isoformat(),
        "deleted_at": content.deleted_at.isoformat() if content.deleted_at else None,
    }
    if generation_id is not None:
        data["generation"] = {
            "id": str(generation_id),
            "model": generation_model,
            "parameters": generation_parameters or {},
        }
    return data


def _content_page_data(page: Page[ContentRecord]) -> dict[str, Any]:
    return page_payload(page, _content_data)


def _content_detail_data(detail: ContentDetailRecord) -> dict[str, Any]:
    data = _content_data(detail.content)
    data["images"] = [_image_data(image) for image in detail.images]
    return data


def _improved_content_data(preview: ImprovedContentPreview) -> dict[str, Any]:
    return {
        "text": preview.text,
        "justification": preview.justification,
        "original_text": preview.original_text,
        "objective": preview.objective,
        "persistence": preview.persistence,
        "content_id": str(preview.content_id) if preview.content_id else None,
        "prompt_template": preview.prompt_template,
    }


def _generation_data(generation: GenerationRecord) -> dict[str, Any]:
    return {
        "id": str(generation.id),
        "workspace_id": str(generation.workspace_id),
        "content_id": str(generation.content_id),
        "brand_id": str(generation.brand_id) if generation.brand_id else None,
        "project_id": str(generation.project_id) if generation.project_id else None,
        "requested_by_user_id": str(generation.requested_by_user_id)
        if generation.requested_by_user_id
        else None,
        "type": generation.generation_type,
        "model": generation.model,
        "prompt": generation.prompt,
        "parameters": generation.parameters,
        "created_at": generation.created_at.isoformat(),
        "updated_at": generation.updated_at.isoformat(),
        "deleted_at": generation.deleted_at.isoformat() if generation.deleted_at else None,
    }


def _asset_data(asset: AssetRecord) -> dict[str, Any]:
    return {
        "id": str(asset.id),
        "workspace_id": str(asset.workspace_id),
        "brand_id": str(asset.brand_id) if asset.brand_id else None,
        "project_id": str(asset.project_id) if asset.project_id else None,
        "content_id": str(asset.content_id) if asset.content_id else None,
        "uploaded_by_user_id": str(asset.uploaded_by_user_id)
        if asset.uploaded_by_user_id
        else None,
        "asset_type": asset.asset_type,
        "storage_path": asset.storage_path,
        "public_url": asset.public_url,
        "mime_type": asset.mime_type,
        "byte_size": asset.byte_size,
        "checksum": asset.checksum,
        "metadata": asset.metadata,
        "created_at": asset.created_at.isoformat(),
        "updated_at": asset.updated_at.isoformat(),
        "deleted_at": asset.deleted_at.isoformat() if asset.deleted_at else None,
    }


def _brand_settings_data(settings: BrandSettingsRecord) -> dict[str, Any]:
    return {
        "id": str(settings.id),
        "workspace_id": str(settings.workspace_id),
        "brand_id": str(settings.brand_id),
        "voice_settings": settings.voice_settings,
        "visual_settings": settings.visual_settings,
        "generation_defaults": settings.generation_defaults,
        "metadata": settings.metadata,
        "created_at": settings.created_at.isoformat(),
        "updated_at": settings.updated_at.isoformat(),
        "deleted_at": settings.deleted_at.isoformat() if settings.deleted_at else None,
    }


def _image_data(image: ImageRecord, *, public_url: str | None = None) -> dict[str, Any]:
    return {
        "id": str(image.id),
        "workspace_id": str(image.workspace_id),
        "content_id": str(image.content_id),
        "generation_id": str(image.generation_id),
        "version_number": image.version_number,
        "storage_path": image.storage_path,
        "public_url": public_url or image.public_url,
        "mime_type": image.mime_type,
        "width": image.width,
        "height": image.height,
        "model": image.model,
        "prompt": image.prompt,
        "metadata": image.metadata,
        "created_at": image.created_at.isoformat(),
        "updated_at": image.updated_at.isoformat(),
        "deleted_at": image.deleted_at.isoformat() if image.deleted_at else None,
    }


def _image_generation_status_data(
    status: ImageGenerationStatusRecord,
    *,
    public_url: str | None = None,
) -> dict[str, Any]:
    job = status.job
    return {
        "id": str(job.id),
        "content_id": str(job.content_id),
        "generation_id": str(job.generation_id),
        "status": job.status.value,
        "queued_at": job.queued_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "failed_at": job.failed_at.isoformat() if job.failed_at else None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "failure_code": job.failure_code,
        "image": _image_data(status.image, public_url=public_url) if status.image else None,
    }


def _agent_workflow_data(run: Any) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "workspace_id": str(run.workspace_id),
        "content_id": str(run.content_id),
        "brand_id": str(run.brand_id),
        "status": run.status.value,
        "human_review": run.human_review.value,
        "max_refinements": run.max_refinements,
        "refinement_count": run.refinement_count,
        "current_step": run.current_step,
        "input": run.input,
        "final_image_ids": run.final_image_ids,
        "failure_code": run.failure_code,
        "failure_message": run.failure_message,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _agent_workflow_step_data(step: Any) -> dict[str, Any]:
    return {
        "id": str(step.id),
        "run_id": str(step.run_id),
        "sequence_number": step.sequence_number,
        "role": step.role.value,
        "status": step.status.value,
        "attempt": step.attempt,
        "input": step.input,
        "output": step.output,
        "prompt": step.prompt,
        "prompt_template_id": step.prompt_template_id,
        "prompt_template_version": step.prompt_template_version,
        "input_hash": step.input_hash,
        "provider": step.provider,
        "model": step.model,
        "decision": step.decision,
        "error_code": step.error_code,
        "error_message": step.error_message,
        "started_at": step.started_at.isoformat() if step.started_at else None,
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
    }
