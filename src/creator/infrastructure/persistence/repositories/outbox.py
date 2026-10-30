"""Compatibility shim; implementations moved to capability repositories."""

from __future__ import annotations

from creator.workflow.repository import SqlAlchemyOutboxRepository

__all__ = [
    "SqlAlchemyOutboxRepository",
]
