"""Parity analysis between ``Creator_DB_final.sql`` and the SQLAlchemy metadata.

Pure functions shared by ``scripts/schema_parity_report.py`` and the frozen-schema
tests. This module must not import ``Base``, must not mutate ``sys.path`` and must
not import anything from ``tests`` or ``scripts``.

The final modeling is PostgreSQL-flavoured DDL. Nothing here executes SQL: the
dump is parsed as text and compared structurally with the metadata, so the same
comparison runs in CI without a PostgreSQL server.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import sqlalchemy as sa
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.schema import CreateIndex, CreateTable, MetaData

# Final modeling name -> current metadata name. Applied once, so a renamed table
# is neither "missing" nor "extra".
RENAME_MAP: Final[dict[str, str]] = {}

# Deliberate extensions that the final modeling does not contain.
ADR_EXTENSIONS: Final[tuple[str, ...]] = (
    "auth_sessions",
    "outbox_events",
    "activity_events",
    "content_text_versions",
)

# Tables still required by live consumers and absent from the final modeling.
# ADR-029 decides their retirement; until then they are part of the target set.
LEGACY_RETENTION: Final[tuple[str, ...]] = (
    "agent_workflow_runs",
    "agent_workflow_steps",
    "assets",
    "brand_settings",
    "contents",
    "generation_job_status_events",
    "generation_jobs",
    "generations",
    "images",
    "projects",
    "settings",
)

# Tables that exist only in the metadata and are not covered by an ADR yet.
NO_TARGET: Final[tuple[str, ...]] = ("provider_customers", "provider_subscriptions")

# Final (table, constraint) -> (metadata table.constraint, expected portable SQL).
# Filled as CHECKs are ported; an entry missing here counts as unmapped debt, and a
# mapped entry also asserts the portable expression, not just the constraint name.
CHECK_MAP: Final[dict[str, tuple[str, str]]] = {
    "notifications.chk_notifications_resource_pair": (
        "notifications.chk_notifications_resource_pair",
        "(resource_type is null) = (resource_id is null)",
    ),
    "charge_transactions.chk_charge_transactions_amount_nonnegative": (
        "charge_transactions.chk_charge_transactions_amount_nonnegative",
        "amount_cents >= 0",
    ),
    "workspace_credit_lots.chk_credit_lots_amounts": (
        "workspace_credit_lots.chk_credit_lots_amounts",
        "original_amount > 0 and remaining_amount >= 0 and remaining_amount <= original_amount",
    ),
    "content_plans.chk_content_plans_period_order": (
        "content_plans.chk_content_plans_period_order",
        "start_date is null or end_date is null or end_date >= start_date",
    ),
    "posts.chk_posts_approval_pair": (
        "posts.chk_posts_approval_pair",
        "(approved_at is null) = (approved_by is null)",
    ),
    "posts.chk_posts_rejected_reason": (
        "posts.chk_posts_rejected_reason",
        "approval_status <> 'rejected' or rejection_reason is not null",
    ),
    "posts.chk_posts_approved_metadata": (
        "posts.chk_posts_approved_metadata",
        "approval_status <> 'approved' or (approved_by is not null and approved_at is not null)",
    ),
    "posts.chk_posts_scheduled_at": (
        "posts.chk_posts_scheduled_at",
        "publication_status <> 'scheduled' or scheduled_at is not null",
    ),
    "posts.chk_posts_published_at": (
        "posts.chk_posts_published_at",
        "publication_status <> 'published' or published_at is not null",
    ),
    "posts.chk_posts_publish_requires_approval": (
        "posts.chk_posts_publish_requires_approval",
        "publication_status = 'draft' or approval_status = 'approved'",
    ),
    "post_designs.chk_post_designs_stories_ratio": (
        "post_designs.chk_post_designs_stories_ratio",
        "format <> 'stories' or ratio = 'ratio_9_16'",
    ),
    "generated_images.chk_generated_images_current_complete": (
        "generated_images.chk_generated_images_current_complete",
        "not is_current or (generation_status = 'succeeded' and deleted_at is null)",
    ),
    "generated_images.chk_generated_images_size_bytes": (
        "generated_images.chk_generated_images_size_bytes",
        "size_bytes is null or size_bytes >= 0",
    ),
    "generated_images.chk_generated_images_dimensions": (
        "generated_images.chk_generated_images_dimensions",
        "width is null or height is null or (width > 0 and height > 0)",
    ),
    "generated_images.chk_generated_images_approval_pair": (
        "generated_images.chk_generated_images_approval_pair",
        "(approved_at is null) = (approved_by is null)",
    ),
    "generated_images.chk_generated_images_rejected_reason": (
        "generated_images.chk_generated_images_rejected_reason",
        "approval_status <> 'rejected' or rejection_reason is not null",
    ),
    "generated_images.chk_generated_images_approved_metadata": (
        "generated_images.chk_generated_images_approved_metadata",
        "approval_status <> 'approved' or (approved_by is not null and approved_at is not null)",
    ),
    "generated_images.chk_generated_images_approval_after_generation": (
        "generated_images.chk_generated_images_approval_after_generation",
        "approval_status = 'pending' or generation_status = 'succeeded'",
    ),
    "generated_images.chk_generated_images_file_by_status": (
        "generated_images.chk_generated_images_file_by_status",
        "generation_status <> 'succeeded' or (storage_bucket is not null and "
        "storage_key is not null and size_bytes is not null and width is not null "
        "and height is not null)",
    ),
    "generated_images.chk_generated_images_failed_message": (
        "generated_images.chk_generated_images_failed_message",
        "generation_status <> 'failed' or error_message is not null",
    ),
    "image_resizes.chk_image_resizes_file": (
        "image_resizes.chk_image_resizes_file",
        "status <> 'succeeded' or (storage_bucket is not null and storage_key is not null "
        "and size_bytes is not null and width is not null and height is not null)",
    ),
    "image_resizes.chk_image_resizes_failed": (
        "image_resizes.chk_image_resizes_failed",
        "status <> 'failed' or error_message is not null",
    ),
    "image_resizes.chk_image_resizes_size": (
        "image_resizes.chk_image_resizes_size",
        "size_bytes is null or size_bytes > 0",
    ),
    "image_resizes.chk_image_resizes_dimensions": (
        "image_resizes.chk_image_resizes_dimensions",
        "(width is null or width > 0) and (height is null or height > 0)",
    ),
    "fiscal_invoices.chk_fiscal_invoices_one_origin": (
        "fiscal_invoices.chk_fiscal_invoices_one_origin",
        "(case when order_id is not null then 1 else 0 end) + "
        "(case when invoice_id is not null then 1 else 0 end) + "
        "(case when subscription_id is not null then 1 else 0 end) = 1",
    ),
    "fiscal_invoices.chk_fiscal_invoices_amount_nonnegative": (
        "fiscal_invoices.chk_fiscal_invoices_amount_nonnegative",
        "amount_cents >= 0",
    ),
    "fiscal_invoices.chk_fiscal_invoices_currency_format": (
        "fiscal_invoices.chk_fiscal_invoices_currency_format",
        "currency glob '[a-z][a-z][a-z]'",
    ),
    "workspace_invites.chk_workspace_invites_email_by_type": (
        "workspace_invites.chk_workspace_invites_email_by_type",
        "(type = 'EMAIL') = (email IS NOT NULL)",
    ),
    "workspace_invites.chk_workspace_invites_max_uses_by_type": (
        "workspace_invites.chk_workspace_invites_max_uses_by_type",
        "(type = 'LINK') = (max_uses IS NOT NULL)",
    ),
    "workspace_invites.chk_workspace_invites_max_uses_positive": (
        "workspace_invites.chk_workspace_invites_max_uses_positive",
        "max_uses IS NULL OR max_uses >= 1",
    ),
    "design_slides.design_slides.position": (
        "design_slides.ck_design_slides_position",
        "position >= 0",
    ),
    "captions.captions.version": ("captions.ck_captions_version", "version >= 1"),
    "content_plan_items.content_plan_items.quantity": (
        "content_plan_items.ck_content_plan_items_quantity",
        "quantity >= 0",
    ),
    "plan_payment_methods.plan_payment_methods.max_installments": (
        "plan_payment_methods.chk_plan_payment_methods_max_installments",
        "max_installments >= 1",
    ),
    "workspace_credit_lot_consumptions.workspace_credit_lot_consumptions.amount": (
        "workspace_credit_lot_consumptions.chk_lot_consumptions_amount",
        "amount > 0",
    ),
    "billing_accounts.chk_billing_accounts_company_name": (
        "billing_accounts.chk_billing_accounts_company_name",
        "(payer_type = 'company') = (company_name is not null)",
    ),
    "billing_accounts.chk_billing_accounts_document_pair": (
        "billing_accounts.chk_billing_accounts_document_pair",
        "(document is null) = (document_hash is null)",
    ),
    "billing_addresses.chk_billing_addresses_zip_code": (
        "billing_addresses.chk_billing_addresses_zip_code",
        "country <> 'br' or zip_code glob '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'",
    ),
    "billing_addresses.chk_billing_addresses_state_uf": (
        "billing_addresses.chk_billing_addresses_state_uf",
        "country <> 'br' or state glob '[a-z][a-z]'",
    ),
    "billing_payment_methods.chk_billing_payment_methods_exp_month": (
        "billing_payment_methods.chk_billing_payment_methods_exp_month",
        "exp_month is null or exp_month between 1 and 12",
    ),
    "plans.chk_plans_cents_nonnegative": (
        "plans.chk_plans_cents_nonnegative",
        "price_cents >= 0 and (minimum_price_cents is null or minimum_price_cents >= 0)",
    ),
    "plans.chk_plans_currency_format": (
        "plans.chk_plans_currency_format",
        "currency glob '[a-z][a-z][a-z]'",
    ),
    "plan_items.chk_plan_items_price_nonnegative": (
        "plan_items.chk_plan_items_price_nonnegative",
        "price_cents is null or price_cents >= 0",
    ),
    "plan_items.chk_plan_items_currency_format": (
        "plan_items.chk_plan_items_currency_format",
        "currency glob '[a-z][a-z][a-z]'",
    ),
    "billing_payment_methods.chk_billing_payment_methods_exp_year": (
        "billing_payment_methods.chk_billing_payment_methods_exp_year",
        "exp_year is null or exp_year between 2000 and 2100",
    ),
    "brand_colors.chk_brand_colors_hex": (
        "brand_colors.chk_brand_colors_hex",
        "hex glob '#[0-9a-fa-f][0-9a-fa-f][0-9a-fa-f][0-9a-fa-f][0-9a-fa-f][0-9a-fa-f]'",
    ),
}

GAP_CATEGORIES: Final[tuple[str, ...]] = (
    "table_missing",
    "table_extra",
    "allowlisted",
    "rename_collision",
    "pk_mismatch",
    "column_missing",
    "column_extra",
    "nullability",
    "width",
    "kind",
    "enum",
    "unique_missing",
    "unique_extra",
    "index_missing",
    "index_extra",
    "index_name",
    "fk_missing",
    "fk_extra",
    "fk_ondelete",
    "check_missing",
    "check_extra",
    "default_missing",
    "default_value",
)

COLUMN_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "NOT",
        "NULL",
        "DEFAULT",
        "CHECK",
        "UNIQUE",
        "PRIMARY",
        "REFERENCES",
        "CONSTRAINT",
        "GENERATED",
        "COLLATE",
    }
)


@dataclass(frozen=True)
class FinalColumn:
    name: str
    kind: str
    raw_type: str
    not_null: bool
    primary_key: bool
    unique: bool
    default: str | None
    inline_check: str | None


@dataclass(frozen=True)
class FinalTable:
    name: str
    columns: dict[str, FinalColumn]
    checks: tuple[tuple[str, str], ...]
    uniques: tuple[tuple[str, ...], ...]
    primary_key: tuple[str, ...]
    foreign_keys: tuple[ForeignKey, ...]


@dataclass(frozen=True)
class IndexSignature:
    table: str
    columns: tuple[str, ...]
    unique: bool
    predicate: str | None
    name: str | None = None

    def sort_key(self) -> tuple[str, str, bool, str]:
        return (self.table, ",".join(self.columns), self.unique, self.predicate or "")


@dataclass(frozen=True)
class ForeignKey:
    table: str
    columns: tuple[str, ...]
    ref_table: str
    ref_columns: tuple[str, ...]
    ondelete: str


@dataclass(frozen=True)
class FinalSchema:
    tables: dict[str, FinalTable]
    indexes: tuple[IndexSignature, ...]
    enums: dict[str, tuple[str, ...]]
    foreign_keys: tuple[ForeignKey, ...]
    storage_objects: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ModelColumn:
    name: str
    nullable: bool
    primary_key: bool
    kind: str
    length: int | None
    enum_values: tuple[str, ...] | None
    unique: bool
    has_default: bool
    default_text: str | None


@dataclass(frozen=True)
class ModelTable:
    name: str
    columns: dict[str, ModelColumn]
    indexes: tuple[IndexSignature, ...]
    foreign_keys: tuple[ForeignKey, ...]
    checks: tuple[tuple[str | None, str], ...]
    uniques: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Gap:
    """Deterministic, category-keyed list of schema divergences."""

    details: dict[str, list[str]]

    def counts(self) -> dict[str, int]:
        return {category: len(self.details.get(category, [])) for category in GAP_CATEGORIES}

    def total(self) -> int:
        return sum(self.counts().values())


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    in_quote = False
    for ch in text:
        if ch == '"':
            in_quote = not in_quote
            cur.append(ch)
        elif in_quote:
            cur.append(ch)
        elif ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [part.strip() for part in parts if part.strip()]


def split_statements(sql: str) -> list[str]:
    """Split a PostgreSQL dump, respecting strings, identifiers and dollar quotes.

    ``str.split(";")`` breaks on semicolons inside string literals, comments and
    ``$$``-quoted function bodies. This scanner keeps every statement intact.
    """
    out: list[str] = []
    cur: list[str] = []
    depth = 0
    i = 0
    length = len(sql)

    while i < length:
        ch = sql[i]

        if ch == "-" and sql.startswith("--", i):
            newline = sql.find("\n", i)
            if newline == -1:
                break
            i = newline + 1
            cur.append("\n")
            continue

        if ch == "'":
            end = i + 1
            while end < length:
                if sql[end] == "'":
                    if end + 1 < length and sql[end + 1] == "'":
                        end += 2
                        continue
                    break
                end += 1
            cur.append(sql[i : end + 1])
            i = end + 1
            continue

        if ch == '"':
            end = sql.find('"', i + 1)
            if end == -1:
                end = length - 1
            cur.append(sql[i : end + 1])
            i = end + 1
            continue

        if ch == "$":
            tag_match = re.match(r"\$[A-Za-z_0-9]*\$", sql[i:])
            if tag_match:
                tag = tag_match.group(0)
                end = sql.find(tag, i + len(tag))
                if end == -1:
                    cur.append(sql[i:])
                    i = length
                    continue
                cur.append(sql[i : end + len(tag)])
                i = end + len(tag)
                continue

        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1

        if ch == ";" and depth == 0:
            text = "".join(cur).strip()
            if text:
                out.append(text)
            cur = []
        else:
            cur.append(ch)
        i += 1

    tail = "".join(cur).strip()
    if tail:
        out.append(tail)

    cleaned: list[str] = []
    for statement in out:
        while statement.startswith("--"):
            newline = statement.find("\n")
            if newline == -1:
                break
            statement = statement[newline + 1 :].lstrip()
        if statement:
            cleaned.append(statement)
    return cleaned


def normalize_kind(raw: str, enum_names: frozenset[str]) -> str:
    """Collapse a PostgreSQL type into a comparable category."""
    text = raw.strip().lower()
    if text == "uuid":
        return "uuid"
    if text.startswith("varchar") or text.startswith("char"):
        size = re.search(r"\((\d+)\)", text)
        return f"varchar({size.group(1)})" if size else "varchar"
    if text == "text":
        return "text"
    if text in {"jsonb", "json"}:
        return "json"
    if text in {
        "timestamptz",
        "timestamp",
        "timestamp with time zone",
        "timestamp without time zone",
    }:
        return "timestamp"
    if text in {"boolean", "bool"}:
        return "bool"
    if text in {"int", "integer", "int4"}:
        return "int"
    if text in {"bigint", "int8"}:
        return "bigint"
    if text in {"numeric", "decimal"} or text.startswith("numeric"):
        return "numeric"
    if text == "bytea":
        return "bytes"
    if text in enum_names:
        return "enum"
    return text


def parse_final(sql: str) -> FinalSchema:
    """Parse the final modeling dump into comparable structures."""
    statements = split_statements(sql)

    enums: dict[str, tuple[str, ...]] = {}
    for statement in statements:
        enum_match = re.match(r'CREATE TYPE "([^"]+)" AS ENUM \((.*)\)\s*$', statement, re.S)
        if enum_match:
            enums[enum_match.group(1)] = tuple(re.findall(r"'([^']*)'", enum_match.group(2)))

    enum_names = frozenset(enums)
    tables: dict[str, FinalTable] = {}
    indexes: list[IndexSignature] = []
    foreign_keys: list[ForeignKey] = []
    storage_objects: list[tuple[str, str]] = []

    for statement in statements:
        created = re.match(r'CREATE TABLE "([^"]+)"\s*\(', statement, re.S)
        if created:
            table = _parse_table(created.group(1), statement, created.end(), enum_names)
            tables[table.name] = table
            foreign_keys.extend(table.foreign_keys)
            continue

        object_match = re.match(
            r"CREATE (?:OR REPLACE )?(FUNCTION|TRIGGER|VIEW)\s+\"?([^\"\s(]+)", statement
        )
        if object_match:
            storage_objects.append((object_match.group(1), object_match.group(2)))
            continue

        index = _parse_index(statement)
        if index is not None:
            indexes.append(index)
            continue

        added = _parse_foreign_key(statement)
        if added is not None:
            foreign_keys.append(added)

    return FinalSchema(
        tables=tables,
        indexes=tuple(indexes),
        enums=enums,
        foreign_keys=tuple(foreign_keys),
        storage_objects=tuple(storage_objects),
    )


def _parse_table(
    name: str,
    statement: str,
    body_start: int,
    enum_names: frozenset[str],
) -> FinalTable:
    body = statement[body_start : statement.rindex(")")]
    columns: dict[str, FinalColumn] = {}
    checks: list[tuple[str, str]] = []
    uniques: set[tuple[str, ...]] = set()
    primary_key: tuple[str, ...] = ()
    inline_foreign_keys: list[ForeignKey] = []

    for part in _split_top_level(body):
        if re.match(r"^(CONSTRAINT|PRIMARY KEY|UNIQUE|CHECK|FOREIGN KEY)\b", part):
            named = re.match(r'CONSTRAINT "([^"]+)"\s+CHECK\s*(\(.*\))', part, re.S)
            if named:
                checks.append((named.group(1), _normalize_sql(named.group(2))))
                continue
            unique = re.match(r"UNIQUE\s*\((.*)\)\s*$", part, re.S)
            if unique:
                uniques.add(_column_tuple(unique.group(1)))
                continue
            primary = re.match(r"PRIMARY KEY\s*\((.*)\)\s*$", part, re.S)
            if primary:
                primary_key = _column_tuple(primary.group(1))
                continue
            inline = _parse_inline_foreign_key(name, part)
            if inline is not None:
                inline_foreign_keys.append(inline)
            continue

        column_match = re.match(r'"([^"]+)"\s+(.*)$', part, re.S)
        if not column_match:
            continue

        column_name, rest = column_match.group(1), column_match.group(2)
        tokens = rest.split()
        type_tokens: list[str] = []
        index = 0
        while index < len(tokens) and tokens[index].upper() not in COLUMN_KEYWORDS:
            type_tokens.append(tokens[index])
            index += 1
        raw_type = " ".join(type_tokens)
        tail = " ".join(tokens[index:])

        default_text = _extract_default(tail)
        inline_check = re.search(r"\bCHECK\s*(\(.*)$", tail, re.I)

        columns[column_name] = FinalColumn(
            name=column_name,
            kind=normalize_kind(raw_type, enum_names),
            raw_type=raw_type,
            not_null="NOT NULL" in tail.upper(),
            primary_key=bool(re.search(r"PRIMARY KEY", tail, re.I)),
            unique=bool(re.search(r"\bUNIQUE\b", tail, re.I)),
            default=default_text,
            inline_check=inline_check.group(1).strip() if inline_check else None,
        )
        if inline_check:
            checks.append((f"{name}.{column_name}", _normalize_sql(inline_check.group(1))))

    return FinalTable(
        name=name,
        columns=columns,
        checks=tuple(checks),
        uniques=tuple(sorted(uniques)),
        primary_key=primary_key,
        foreign_keys=tuple(inline_foreign_keys),
    )


def _extract_default(tail: str) -> str | None:
    """Read a DEFAULT expression, balancing parentheses and quotes.

    PostgreSQL wraps function defaults as ``DEFAULT (now())``; a flat regex stops
    at the first ``)`` and silently drops the requirement.
    """
    match = re.search(r"\bDEFAULT\b", tail, re.I)
    if match is None:
        return None
    rest = tail[match.end() :].lstrip()
    if rest.startswith("("):
        depth = 0
        for index, char in enumerate(rest):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return rest[: index + 1].strip()
        return rest.strip()
    if rest.startswith("'"):
        end = rest.find("'", 1)
        while end != -1 and rest[end + 1 : end + 2] == "'":
            end = rest.find("'", end + 2)
        return rest[: end + 1].strip() if end != -1 else rest.strip()
    token = re.match(r"[^\s,]+", rest)
    return token.group(0) if token else None


def _column_tuple(text: str) -> tuple[str, ...]:
    return tuple(column.strip().strip('"') for column in _split_top_level(text))


def _parse_inline_foreign_key(table: str, part: str) -> ForeignKey | None:
    match = re.match(
        r'(?:CONSTRAINT "[^"]+" )?FOREIGN KEY\s*\(([^)]+)\)\s*'
        r'REFERENCES\s+"([^"]+)"\s*\(([^)]+)\)(?:\s+ON DELETE ([A-Z ]+?))?\s*$',
        part,
        re.S,
    )
    if match is None:
        return None
    return ForeignKey(
        table=table,
        columns=_column_tuple(match.group(1)),
        ref_table=match.group(2),
        ref_columns=_column_tuple(match.group(3)),
        ondelete=(match.group(4) or "NO ACTION").strip().upper(),
    )


def _parse_index(statement: str) -> IndexSignature | None:
    match = re.match(r'CREATE (UNIQUE )?INDEX(?:\s+"([^"]+)")?\s+ON\s+"([^"]+)"', statement, re.S)
    if match is None:
        return None
    columns_match = re.search(r"\((.*?)\)", statement[match.end() :], re.S)
    if columns_match is None:
        return None
    columns = tuple(_index_column(column) for column in _split_top_level(columns_match.group(1)))
    predicate_match = re.search(r"\bWHERE\b(.*)$", statement, re.S | re.I)
    return IndexSignature(
        table=match.group(3),
        columns=columns,
        unique=bool(match.group(1)),
        predicate=_normalize_sql(predicate_match.group(1)) if predicate_match else None,
        name=match.group(2),
    )


def _index_column(part: str) -> str:
    """Extract the identifier from an index column, ignoring ordering and NULLS."""
    quoted = re.match(r'"([^"]+)"', part.strip())
    if quoted:
        return quoted.group(1)
    bare = re.match(r"([A-Za-z_][A-Za-z_0-9]*)", part.strip())
    return bare.group(1) if bare else part.strip()


def _parse_foreign_key(statement: str) -> ForeignKey | None:
    match = re.match(
        r'ALTER TABLE "([^"]+)" ADD (?:CONSTRAINT "[^"]+" )?FOREIGN KEY\s*\(([^)]+)\)\s*'
        r'REFERENCES\s+"([^"]+)"\s*\(([^)]+)\)(?:\s+ON DELETE ([A-Z ]+?))?(?:\s+DEFERRABLE|$)',
        statement,
        re.S,
    )
    if match is None:
        return None
    return ForeignKey(
        table=match.group(1),
        columns=tuple(column.strip().strip('"') for column in match.group(2).split(",")),
        ref_table=match.group(3),
        ref_columns=tuple(column.strip().strip('"') for column in match.group(4).split(",")),
        ondelete=(match.group(5) or "NO ACTION").strip().upper(),
    )


def _normalize_sql(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip().lower().replace('"', "")
    return collapsed


def _sqlite_where(index: sa.Index) -> str | None:
    sqlite_options = index.dialect_options.get("sqlite")
    if not sqlite_options:
        return None
    where = sqlite_options.get("where")
    return _normalize_sql(str(where)) if where is not None else None


def _base_type(column_type: sa.types.TypeEngine[Any]) -> sa.types.TypeEngine[Any]:
    """Unwrap ``TypeDecorator`` so wrappers compare by their implementation."""
    current: Any = column_type
    seen: set[int] = set()
    while isinstance(current, sa.types.TypeDecorator) and id(current) not in seen:
        seen.add(id(current))
        current = current.impl
    return current if isinstance(current, sa.types.TypeEngine) else column_type


def model_kind(
    column_type: sa.types.TypeEngine[Any],
) -> tuple[str, int | None, tuple[str, ...] | None]:
    """Return ``(kind, string length, enum vocabulary)`` for a model column type."""
    column_type = _base_type(column_type)
    if isinstance(column_type, sa.Enum):
        return "enum", column_type.length, tuple(str(value) for value in column_type.enums)
    if isinstance(column_type, sa.Uuid):
        return "uuid", None, None
    if isinstance(column_type, sa.BigInteger):
        return "bigint", None, None
    if isinstance(column_type, sa.Integer):
        return "int", None, None
    if isinstance(column_type, sa.Boolean):
        return "bool", None, None
    if isinstance(column_type, sa.JSON):
        return "json", None, None
    if isinstance(column_type, sa.Text):
        return "text", None, None
    if isinstance(column_type, sa.String):
        return "varchar", column_type.length, None
    if isinstance(column_type, sa.DateTime):
        return "timestamp", None, None
    if isinstance(column_type, sa.Numeric):
        return "numeric", None, None
    if isinstance(column_type, sa.LargeBinary):
        return "bytes", None, None
    return "other", None, None


def parse_models(metadata: MetaData) -> dict[str, ModelTable]:
    """Build the comparable view of the live metadata."""
    result: dict[str, ModelTable] = {}

    for table in metadata.tables.values():
        columns: dict[str, ModelColumn] = {}
        for column in table.columns:
            kind, length, enum_values = model_kind(column.type)
            columns[column.name] = ModelColumn(
                name=column.name,
                nullable=bool(column.nullable),
                primary_key=bool(column.primary_key),
                kind=kind,
                length=length,
                enum_values=enum_values,
                unique=bool(column.unique),
                has_default=column.default is not None or column.server_default is not None,
                default_text=_model_default_text(column),
            )

        indexes: list[IndexSignature] = []
        for index in table.indexes:
            indexes.append(
                IndexSignature(
                    table=table.name,
                    columns=tuple(column.name for column in index.columns),
                    unique=bool(index.unique),
                    predicate=_sqlite_where(index),
                    name=index.name,
                )
            )

        unique_columns: set[tuple[str, ...]] = {
            tuple(column.name for column in unique_constraint.columns)
            for unique_constraint in table.constraints
            if isinstance(unique_constraint, sa.UniqueConstraint)
        }
        unique_columns.update((column.name,) for column in table.columns if column.unique)

        foreign_keys: list[ForeignKey] = []
        for fk_constraint in table.foreign_key_constraints:
            local = tuple(column.name for column in fk_constraint.columns)
            elements = list(fk_constraint.elements)
            if not elements:
                continue
            ref_table = elements[0].column.table.name
            ref_columns = tuple(element.column.name for element in elements)
            foreign_keys.append(
                ForeignKey(
                    table=table.name,
                    columns=local,
                    ref_table=ref_table,
                    ref_columns=ref_columns,
                    ondelete=(fk_constraint.ondelete or "NO ACTION").strip().upper(),
                )
            )

        checks: list[tuple[str | None, str]] = []
        for check_constraint in table.constraints:
            if (
                not isinstance(check_constraint, sa.CheckConstraint)
                or check_constraint.sqltext is None
            ):
                continue
            name = check_constraint.name if isinstance(check_constraint.name, str) else None
            checks.append((name, _normalize_sql(str(check_constraint.sqltext))))

        result[table.name] = ModelTable(
            name=table.name,
            columns=columns,
            indexes=tuple(indexes),
            foreign_keys=tuple(foreign_keys),
            checks=tuple(checks),
            uniques=tuple(sorted(unique_columns)),
        )

    return result


def _model_default_text(column: sa.Column[Any]) -> str | None:
    if isinstance(column.default, sa.ColumnDefault):
        argument: Any = column.default.arg
        if callable(argument):
            return str(getattr(argument, "__name__", repr(argument)))
        return str(argument)
    if column.server_default is not None:
        return str(getattr(column.server_default, "arg", column.server_default))
    return None


def _default_signature(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    text = re.sub(r"^\((.*)\)$", r"\1", text)
    if text in {"gen_random_uuid()", "uuid_generate_v4()", "uuid4", "uuid"}:
        return "uuid"
    if text in {"now()", "current_timestamp", "current_timestamp()"}:
        return "now"
    if text in {"false", "0"}:
        return "false"
    if text in {"true", "1"}:
        return "true"
    return text


def _kind_family(kind: str) -> str:
    if kind == "text" or kind.startswith("varchar"):
        return "string"
    if kind in {"int", "bigint"}:
        return "int"
    return kind


def _model_name(final_name: str) -> str:
    return RENAME_MAP.get(final_name, final_name)


def _final_name(model_name: str) -> str | None:
    for final, model in RENAME_MAP.items():
        if model == model_name:
            return final
    return None


def compare(final: FinalSchema, models: dict[str, ModelTable]) -> Gap:
    """Return every divergence between the dump and the live metadata."""
    details: dict[str, list[str]] = {category: [] for category in GAP_CATEGORIES}

    expected_models: dict[str, str] = {}
    for final_name in final.tables:
        model_name = _model_name(final_name)
        if model_name in expected_models:
            details["rename_collision"].append(
                f"{expected_models[model_name]} and {final_name} both map to {model_name}"
            )
        expected_models[model_name] = final_name

    for model_name in models:
        if model_name in ADR_EXTENSIONS:
            details["allowlisted"].append(f"adr_extension:{model_name}")
        elif model_name in LEGACY_RETENTION:
            details["allowlisted"].append(f"legacy:{model_name}")
        elif model_name in NO_TARGET:
            details["allowlisted"].append(f"no_target:{model_name}")

    for model_name, final_name in expected_models.items():
        if model_name not in models:
            details["table_missing"].append(final_name)

    for model_name in models:
        if model_name in expected_models:
            continue
        if model_name in ADR_EXTENSIONS or model_name in LEGACY_RETENTION:
            continue
        if model_name in NO_TARGET:
            continue
        details["table_extra"].append(model_name)

    for model_name, final_name in sorted(expected_models.items()):
        table = final.tables[final_name]
        model = models.get(model_name)
        if model is None:
            continue
        _compare_table(final_name, table, model, final.enums, details)

    _compare_indexes(final, models, expected_models, details)
    _compare_foreign_keys(final, models, expected_models, details)
    _compare_checks(final, models, expected_models, details)

    return Gap(details={category: sorted(items) for category, items in details.items() if items})


def _compare_table(
    final_name: str,
    table: FinalTable,
    model: ModelTable,
    enums: dict[str, tuple[str, ...]],
    details: dict[str, list[str]],
) -> None:
    final_columns = table.columns
    model_columns = model.columns

    for name in sorted(set(final_columns) - set(model_columns)):
        details["column_missing"].append(f"{final_name}.{name}")
    for name in sorted(set(model_columns) - set(final_columns)):
        details["column_extra"].append(f"{final_name}.{name}")

    final_pk = tuple(sorted(name for name, column in final_columns.items() if column.primary_key))
    model_pk = tuple(sorted(name for name, column in model_columns.items() if column.primary_key))
    if final_pk != model_pk:
        details["pk_mismatch"].append(
            f"{final_name}: final={list(final_pk)} model={list(model_pk)}"
        )

    for name in sorted(set(final_columns) & set(model_columns)):
        expected = final_columns[name]
        actual = model_columns[name]

        if expected.not_null and actual.nullable:
            details["nullability"].append(f"{final_name}.{name}: final NOT NULL, model nullable")

        if expected.kind == "enum":
            expected_values = enums.get(expected.raw_type.strip().strip('"'), ())
            if actual.enum_values is None:
                expected_list = list(expected_values)
                details["enum"].append(
                    f"{final_name}.{name}: model has no vocabulary (expected {expected_list})"
                )
            elif tuple(sorted(expected_values)) != tuple(sorted(actual.enum_values)):
                missing = sorted(set(expected_values) - set(actual.enum_values))
                extra = sorted(set(actual.enum_values) - set(expected_values))
                details["enum"].append(f"{final_name}.{name}: missing={missing} extra={extra}")
            continue

        if _kind_family(expected.kind) != _kind_family(actual.kind):
            details["kind"].append(
                f"{final_name}.{name}: final {expected.kind}, model {actual.kind}"
            )
            continue

        if expected.kind == "bigint" and actual.kind == "int":
            details["width"].append(f"{final_name}.{name}: final bigint, model integer")
        elif expected.kind == "int" and actual.kind == "bigint":
            details["width"].append(f"{final_name}.{name}: final integer, model bigint")
        elif expected.kind.startswith("varchar(") and actual.kind.startswith("varchar"):
            size = int(expected.kind.removeprefix("varchar(").rstrip(")"))
            if actual.length != size:
                details["width"].append(
                    f"{final_name}.{name}: final varchar({size}), model varchar({actual.length})"
                )
        elif expected.kind == "text" and actual.kind.startswith("varchar"):
            details["width"].append(
                f"{final_name}.{name}: final text, model varchar({actual.length})"
            )
        elif expected.kind == "varchar" and actual.kind == "varchar" and actual.length is not None:
            details["width"].append(
                f"{final_name}.{name}: final unbounded varchar, model varchar({actual.length})"
            )

        if expected.default is not None:
            if not actual.has_default:
                details["default_missing"].append(
                    f"{final_name}.{name}: final default {expected.default}"
                )
            elif _default_signature(expected.default) != _default_signature(actual.default_text):
                details["default_value"].append(
                    f"{final_name}.{name}: final {expected.default!r}, "
                    f"model {actual.default_text!r}"
                )

    final_uniques = {tuple(sorted(unique)) for unique in table.uniques} | {
        (name,) for name, column in final_columns.items() if column.unique
    }
    model_uniques = {tuple(sorted(unique)) for unique in model.uniques} | {
        (name,) for name, column in model_columns.items() if column.unique
    }
    final_primary_key = tuple(
        sorted(name for name, column in final_columns.items() if column.primary_key)
    )
    if final_primary_key:
        final_uniques.add(final_primary_key)
    if table.primary_key:
        final_uniques.add(tuple(sorted(table.primary_key)))
    model_primary_key = tuple(
        sorted(name for name, column in model_columns.items() if column.primary_key)
    )
    if model_primary_key:
        model_uniques.add(model_primary_key)
    for unique in sorted(final_uniques - model_uniques):
        details["unique_missing"].append(f"{final_name}{list(unique)}")
    for unique in sorted(model_uniques - final_uniques):
        details["unique_extra"].append(f"{final_name}{list(unique)}")


def _compare_indexes(
    final: FinalSchema,
    models: dict[str, ModelTable],
    expected_models: dict[str, str],
    details: dict[str, list[str]],
) -> None:
    final_by_model: dict[str, list[IndexSignature]] = {}
    for index in final.indexes:
        final_by_model.setdefault(_model_name(index.table), []).append(index)

    for model_name, expected_indexes in sorted(final_by_model.items()):
        model = models.get(model_name)
        if model is None:
            continue
        expected_counter = Counter(_index_signature(index) for index in expected_indexes)
        actual_counter = Counter(_index_signature(index) for index in model.indexes)
        for signature, count in sorted(
            (expected_counter - actual_counter).items(),
            key=lambda item: _signature_sort_key(item[0]),
        ):
            suffix = f" x{count}" if count > 1 else ""
            details["index_missing"].append(
                f"{model_name}: {_describe_signature(signature)}{suffix}"
            )
        for signature, count in sorted(
            (actual_counter - expected_counter).items(),
            key=lambda item: _signature_sort_key(item[0]),
        ):
            suffix = f" x{count}" if count > 1 else ""
            details["index_extra"].append(f"{model_name}: {_describe_signature(signature)}{suffix}")
        actual_names = {index.name for index in model.indexes if index.name}
        for index in expected_indexes:
            if index.name and index.name not in actual_names:
                details["index_name"].append(f"{model_name}: missing index name {index.name}")


def _index_signature(index: IndexSignature) -> tuple[tuple[str, ...], bool, str | None]:
    return (index.columns, index.unique, index.predicate)


def _signature_sort_key(
    signature: tuple[tuple[str, ...], bool, str | None],
) -> tuple[str, bool, str]:
    columns, unique, predicate = signature
    return (",".join(columns), unique, predicate or "")


def _describe_signature(signature: tuple[tuple[str, ...], bool, str | None]) -> str:
    columns, unique, predicate = signature
    text = ("UNIQUE " if unique else "") + "(" + ", ".join(columns) + ")"
    return text + (f" WHERE {predicate}" if predicate else "")


def _compare_foreign_keys(
    final: FinalSchema,
    models: dict[str, ModelTable],
    expected_models: dict[str, str],
    details: dict[str, list[str]],
) -> None:
    expected: Counter[tuple[str, tuple[str, ...], str, tuple[str, ...], str]] = Counter()
    for fk in final.foreign_keys:
        expected[
            (
                _model_name(fk.table),
                fk.columns,
                _model_name(fk.ref_table),
                fk.ref_columns,
                fk.ondelete,
            )
        ] += 1

    actual: Counter[tuple[str, tuple[str, ...], str, tuple[str, ...], str]] = Counter()
    for model_name, model in models.items():
        if model_name not in expected_models:
            continue
        for fk in model.foreign_keys:
            actual[(fk.table, fk.columns, fk.ref_table, fk.ref_columns, fk.ondelete)] += 1

    actual_shapes = {key[:4] for key in actual}
    for (table, columns, ref_table, ref_columns, ondelete), count in sorted(
        (expected - actual).items()
    ):
        suffix = f" x{count}" if count > 1 else ""
        if (table, columns, ref_table, ref_columns) in actual_shapes:
            model_actions = sorted(
                key[4] for key in actual if key[:4] == (table, columns, ref_table, ref_columns)
            )
            details["fk_ondelete"].append(
                f"{table}{list(columns)}->{ref_table}{list(ref_columns)}: "
                f"final {ondelete} vs model {model_actions}"
            )
            continue
        details["fk_missing"].append(
            f"{table}{list(columns)}->{ref_table}{list(ref_columns)} [{ondelete}]{suffix}"
        )

    for (table, columns, ref_table, ref_columns, ondelete), count in sorted(
        (actual - expected).items()
    ):
        suffix = f" x{count}" if count > 1 else ""
        details["fk_extra"].append(
            f"{table}{list(columns)}->{ref_table}{list(ref_columns)} [{ondelete}]{suffix}"
        )


def _compare_checks(
    final: FinalSchema,
    models: dict[str, ModelTable],
    expected_models: dict[str, str],
    details: dict[str, list[str]],
) -> None:
    for final_name, table in sorted(final.tables.items()):
        model_name = _model_name(final_name)
        model = models.get(model_name)
        if model is None:
            continue
        model_checks = {name: sqltext for name, sqltext in model.checks if name}
        for check_name, _expression in table.checks:
            key = f"{final_name}.{check_name}"
            mapped = CHECK_MAP.get(key)
            if mapped is None:
                details["check_missing"].append(f"unmapped:{key}")
                continue
            target, expected_sql = mapped
            target_table, _, target_name = target.partition(".")
            if target_table != model_name or target_name not in model_checks:
                details["check_missing"].append(f"{key}->{target}")
            elif _normalize_sql(expected_sql) != model_checks[target_name]:
                details["check_extra"].append(
                    f"{key}: expected {_normalize_sql(expected_sql)!r}, "
                    f"model has {model_checks[target_name]!r}"
                )

        mapped_names = {
            target.partition(".")[2]
            for final_key, (target, _sql) in CHECK_MAP.items()
            if final_key.startswith(f"{final_name}.")
        }
        for name, _sqltext in model.checks:
            if name and name not in mapped_names:
                details["check_extra"].append(f"{model_name}.{name}")


def gap_counts(gap: Gap) -> dict[str, int]:
    """Count divergences per category, including the zeroed categories."""
    return gap.counts()


def gap_digest(gap: Gap) -> str:
    """Stable digest of every divergence, used by the parity budget."""
    payload = json.dumps(gap.details, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_schema_ddl(metadata: MetaData, *, include_indexes: bool = True) -> str:
    """Canonical SQLite DDL for the metadata, deterministic and whitespace-free."""
    dialect = sqlite_dialect.dialect()
    statements: list[str] = []
    for table in sorted(metadata.tables.values(), key=lambda item: item.name):
        statement = str(CreateTable(table).compile(dialect=dialect)).strip()
        statements.append(_strip_trailing_whitespace(statement))

    if include_indexes:
        for table in sorted(metadata.tables.values(), key=lambda item: item.name):
            for index in sorted(
                table.indexes,
                key=lambda item: (item.name or "", tuple(c.name for c in item.columns)),
            ):
                statement = str(CreateIndex(index).compile(dialect=dialect)).strip()
                statements.append(_strip_trailing_whitespace(statement))

    return "\n\n".join(statements) + "\n"


def _strip_trailing_whitespace(statement: str) -> str:
    return "\n".join(line.rstrip() for line in statement.splitlines())


__all__ = [
    "ADR_EXTENSIONS",
    "CHECK_MAP",
    "GAP_CATEGORIES",
    "LEGACY_RETENTION",
    "NO_TARGET",
    "RENAME_MAP",
    "FinalColumn",
    "FinalSchema",
    "FinalTable",
    "ForeignKey",
    "Gap",
    "IndexSignature",
    "ModelColumn",
    "ModelTable",
    "compare",
    "gap_counts",
    "gap_digest",
    "model_kind",
    "normalize_kind",
    "parse_final",
    "parse_models",
    "render_schema_ddl",
    "sha256_file",
    "split_statements",
]
