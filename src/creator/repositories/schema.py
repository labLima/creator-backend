"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.brand.ports import BrandAssetRecord, BrandAssetRepository
from creator.campaign.ports import CampaignRecord, CampaignRepository
from creator.generation.ports import GeneratedImageRecord, GeneratedImageRepository
from creator.persona.ports import PersonaRecord, PersonaRepository
from creator.planning.ports import PlanningRecord, PlanningRepository
from creator.post_structure.ports import PostStructureRecord, PostStructureRepository

__all__ = [
    "BrandAssetRecord",
    "BrandAssetRepository",
    "CampaignRecord",
    "CampaignRepository",
    "GeneratedImageRecord",
    "GeneratedImageRepository",
    "PersonaRecord",
    "PersonaRepository",
    "PlanningRecord",
    "PlanningRepository",
    "PostStructureRecord",
    "PostStructureRepository",
]
