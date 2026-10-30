"""Compatibility shim; definitions moved to capability ports."""

from __future__ import annotations

from creator.workflow.ports import OutboxEventRecord, OutboxRepository

__all__ = [
    "OutboxEventRecord",
    "OutboxRepository",
]
