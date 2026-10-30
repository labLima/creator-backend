"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.workspace.ports import (
    CreatedWorkspaceRecord,
    WorkspaceInviteRecord,
    WorkspaceInviteRepository,
    WorkspaceMembershipRecord,
    WorkspaceRecord,
    WorkspaceRepository,
)

__all__ = [
    "CreatedWorkspaceRecord",
    "WorkspaceInviteRecord",
    "WorkspaceInviteRepository",
    "WorkspaceMembershipRecord",
    "WorkspaceRecord",
    "WorkspaceRepository",
]
