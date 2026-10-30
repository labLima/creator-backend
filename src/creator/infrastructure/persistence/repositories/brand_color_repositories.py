"""Compatibility shim; implementations moved to capability repositories."""

from __future__ import annotations

from creator.brand.repository import SqlAlchemyBrandColorRepository

__all__ = [
    "SqlAlchemyBrandColorRepository",
]
