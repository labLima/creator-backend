"""Equivalence tests for the portable CHECK helpers.

Each helper must accept and reject exactly the same values as the PostgreSQL
predicate it replaces (``~`` regex and ``num_nonnulls``), otherwise the schema
would silently allow data the final modeling forbids.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from creator.infrastructure.database.constraints import (
    at_most_one_of,
    currency_code_check,
    exactly_one_of,
    hex_color_check,
    uf_check,
    zip_code_check,
)


def _accepts(expression: str, column_sql: dict[str, str], row: dict[str, object]) -> bool:
    """Create a throwaway table with the CHECK and report whether the row fits."""
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    columns = [sa.Column("id", sa.Integer, primary_key=True)]
    columns += [sa.Column(name, sa.Text) for name in column_sql]
    table = sa.Table(
        "probe",
        metadata,
        *columns,
        sa.CheckConstraint(expression, name="ck_probe"),
    )
    metadata.create_all(engine)
    try:
        with engine.begin() as connection:
            connection.execute(table.insert().values(**row))
        return True
    except IntegrityError:
        return False
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        ("BRL", True),
        ("USD", True),
        ("brl", False),
        ("BR", False),
        ("BRLL", False),
        ("BR1", False),
        ("", False),
    ],
)
def test_currency_code_matches_the_postgres_regex(value: str, valid: bool) -> None:
    expression = currency_code_check("currency")
    assert _accepts(expression, {"currency": "TEXT"}, {"currency": value}) is valid


@pytest.mark.parametrize(
    ("value", "valid"), [("SP", True), ("RJ", True), ("sp", False), ("S", False), ("SPX", False)]
)
def test_uf_matches_the_postgres_regex(value: str, valid: bool) -> None:
    expression = uf_check("state")
    assert _accepts(expression, {"state": "TEXT"}, {"state": value}) is valid


@pytest.mark.parametrize(
    ("value", "valid"),
    [("01310100", True), ("0131010", False), ("013101000", False), ("0131O100", False)],
)
def test_zip_code_matches_the_postgres_regex(value: str, valid: bool) -> None:
    expression = zip_code_check("zip_code")
    assert _accepts(expression, {"zip_code": "TEXT"}, {"zip_code": value}) is valid


@pytest.mark.parametrize(
    ("value", "valid"),
    [("#A1B2C3", True), ("#ffffff", True), ("#FFF", False), ("A1B2C3", False), ("#GGGGGG", False)],
)
def test_hex_color_matches_the_postgres_regex(value: str, valid: bool) -> None:
    expression = hex_color_check("hex")
    assert _accepts(expression, {"hex": "TEXT"}, {"hex": value}) is valid


@pytest.mark.parametrize(
    ("row", "valid"),
    [
        ({"a": 1, "b": None}, True),
        ({"a": None, "b": 1}, True),
        ({"a": None, "b": None}, False),
        ({"a": 1, "b": 1}, False),
    ],
)
def test_exactly_one_of_matches_num_nonnulls(row: dict[str, object], valid: bool) -> None:
    expression = exactly_one_of("a", "b")
    assert _accepts(expression, {"a": "INTEGER", "b": "INTEGER"}, row) is valid


@pytest.mark.parametrize(
    ("row", "valid"),
    [
        ({"a": None, "b": None}, True),
        ({"a": 1, "b": None}, True),
        ({"a": 1, "b": 1}, False),
    ],
)
def test_at_most_one_of_matches_num_nonnulls(row: dict[str, object], valid: bool) -> None:
    expression = at_most_one_of("a", "b")
    assert _accepts(expression, {"a": "INTEGER", "b": "INTEGER"}, row) is valid


def test_helpers_reject_empty_input() -> None:
    with pytest.raises(ValueError):
        currency_code_check("")
    with pytest.raises(ValueError):
        exactly_one_of()
    with pytest.raises(ValueError):
        at_most_one_of()


def test_rendered_expressions_avoid_postgres_only_syntax() -> None:
    expressions = [
        currency_code_check("currency"),
        uf_check("state"),
        zip_code_check("zip_code"),
        hex_color_check("hex"),
        exactly_one_of("a", "b"),
        at_most_one_of("a", "b"),
    ]
    for expression in expressions:
        assert " ~ " not in expression
        assert "num_nonnulls" not in expression
