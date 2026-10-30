"""Request payloads for the auth capability.

Moved from `creator.api.dtos`; field definitions are unchanged.
"""

from __future__ import annotations

from pydantic import Field

from creator.core.schemas import CreatorDTO
from creator.modules.workspace.schemas import WorkspaceCreateRequest


class AuthLoginRequest(CreatorDTO):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=4096, repr=False)


class AuthSignupRequest(CreatorDTO):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=4096, repr=False)
    workspace: WorkspaceCreateRequest
