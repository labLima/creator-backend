"""Compatibility shim; implementations moved to capability repositories."""

from __future__ import annotations

from creator.auth.repository import SqlAlchemyAuthSessionRepository

__all__ = [
    "SqlAlchemyAuthSessionRepository",
]
