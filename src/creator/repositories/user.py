"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.user.ports import UserRecord, UserRepository

__all__ = [
    "UserRecord",
    "UserRepository",
]
