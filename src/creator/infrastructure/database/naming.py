"""Naming helpers for indexes created from the final modeling.

The final modeling has 50 explicitly named indexes (``idx_m8_*``, ``uq_*``) and
123 anonymous ones. SQLite requires a name on ``CREATE INDEX``, so anonymous
indexes get a deterministic name here; explicit names are preserved as they are.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Final

MAX_IDENTIFIER_LENGTH: Final[int] = 63
_SUFFIX_LENGTH: Final[int] = 8


def _join(prefix: str, table: str, columns: Sequence[str]) -> str:
    name = f"{prefix}_{table}_{'_'.join(columns)}"
    if len(name) <= MAX_IDENTIFIER_LENGTH:
        return name

    suffix = hashlib.sha1(name.encode("utf-8")).hexdigest()[:_SUFFIX_LENGTH]
    head = f"{prefix}_{table}"
    room = MAX_IDENTIFIER_LENGTH - len(head) - len(suffix) - 2
    tail = "_".join(columns)[: max(room, 1)]
    return f"{head}_{tail}_{suffix}"


def index_name(table: str, columns: Sequence[str]) -> str:
    """Name a non-unique index as ``ix_<table>_<columns>``."""
    return _join("ix", table, columns)


def unique_index_name(table: str, columns: Sequence[str]) -> str:
    """Name a unique index as ``uq_<table>_<columns>``."""
    return _join("uq", table, columns)


__all__ = ["index_name", "unique_index_name"]
