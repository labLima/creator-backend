"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.auth.ports import AuthSessionRecord, AuthSessionRepository

__all__ = [
    "AuthSessionRecord",
    "AuthSessionRepository",
]
