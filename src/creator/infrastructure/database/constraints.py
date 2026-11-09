"""Portable CHECK expressions for the final modeling constraints.

``Creator_DB_final.sql`` uses PostgreSQL-only operators that SQLite does not
implement: regular-expression matching (``~``) and ``num_nonnulls(...)``. The
helpers here render the same predicates with constructs SQLite supports
(``GLOB`` and ``CASE WHEN``) so the constraint can live in the models and still
be created by ``Base.metadata.create_all()``.

Every helper returns SQL text to be wrapped in ``CheckConstraint``; the
equivalence with the PostgreSQL predicate is asserted in
``tests/test_portable_constraints.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

UPPER_LETTER: Final[str] = "[A-Z]"
DIGIT: Final[str] = "[0-9]"
HEX_DIGIT: Final[str] = "[0-9A-Fa-f]"


def _require_column(column: str) -> str:
    if not column:
        raise ValueError("column name is required")
    return column


def _glob(column: str, *patterns: str) -> str:
    return f"{_require_column(column)} GLOB '{''.join(patterns)}'"


def currency_code_check(column: str) -> str:
    """``currency ~ '^[A-Z]{3}$'`` for SQLite: exactly three uppercase letters."""
    return _glob(column, *[UPPER_LETTER] * 3)


def uf_check(column: str) -> str:
    """``state ~ '^[A-Z]{2}$'``: exactly two uppercase letters."""
    return _glob(column, *[UPPER_LETTER] * 2)


def zip_code_check(column: str) -> str:
    """``zip_code ~ '^[0-9]{8}$'``: exactly eight digits."""
    return _glob(column, *[DIGIT] * 8)


def hex_color_check(column: str) -> str:
    """``hex ~ '^#[0-9A-Fa-f]{6}$'``: hash followed by six hex digits."""
    return _glob(column, "#", *[HEX_DIGIT] * 6)


def _non_null_count(columns: Sequence[str]) -> str:
    if not columns:
        raise ValueError("at least one column is required")
    terms = [
        f"(CASE WHEN {_require_column(column)} IS NOT NULL THEN 1 ELSE 0 END)" for column in columns
    ]
    return " + ".join(terms)


def exactly_one_of(*columns: str) -> str:
    """``num_nonnulls(a, b, ...) = 1``: exactly one of the columns is not null."""
    return f"{_non_null_count(columns)} = 1"


def at_most_one_of(*columns: str) -> str:
    """``num_nonnulls(a, b, ...) <= 1``: at most one of the columns is not null."""
    return f"{_non_null_count(columns)} <= 1"


__all__ = [
    "at_most_one_of",
    "currency_code_check",
    "exactly_one_of",
    "hex_color_check",
    "uf_check",
    "zip_code_check",
]
