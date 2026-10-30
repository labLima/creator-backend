"""Request payloads for the design_structure capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class DesignStructureCreateRequest(BaseModel):
    post_structure_id: UUID
