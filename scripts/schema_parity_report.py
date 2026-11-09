#!/usr/bin/env python3
"""Compare ``docs/migration/Creator_DB_final.sql`` with the live ORM metadata.

The final modeling is a PostgreSQL-flavoured dump. This script parses it without
a PostgreSQL server and reports, table by table, what the SQLAlchemy metadata
still lacks: missing tables, columns, nullability, sizes, enums, constraints and
indexes.

Usage:
    python scripts/schema_parity_report.py            # write the markdown report
    python scripts/schema_parity_report.py --check    # exit 1 when drift exists
    python scripts/schema_parity_report.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FINAL_SQL = ROOT / "docs" / "migration" / "Creator_DB_final.sql"
REPORT = ROOT / "docs" / "migration" / "schema-final-alignment.md"

# Same entity, different name in the final modeling.
RENAMES = {
    "workspace_memberships": "workspace_members",
    "planning": "content_plans",
    "post_structure": "posts",
    "design_structure": "post_designs",
    "generated_image": "generated_images",
}

# Deliberate extensions that the final modeling does not contain.
EXTENSIONS = ("activity_events", "auth_sessions", "content_text_versions", "outbox_events")

# Tables still required by live consumers but absent from the final modeling.
LEGACY = (
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

COL_KEYWORDS = {
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


def split_top_level(text: str) -> list[str]:
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
    return [p.strip() for p in parts if p.strip()]


def statements(sql: str) -> list[str]:
    out: list[str] = []
    cur: list[str] = []
    in_quote = False
    depth = 0
    for ch in sql:
        if ch == '"':
            in_quote = not in_quote
        if not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
        if ch == ";" and not in_quote and depth == 0:
            if "".join(cur).strip():
                out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())

    cleaned: list[str] = []
    for stmt in out:
        while stmt.startswith("--"):
            newline = stmt.find("\n")
            if newline == -1:
                break
            stmt = stmt[newline + 1 :].lstrip()
        if stmt:
            cleaned.append(stmt)
    return cleaned


def norm_type(raw: str) -> str:
    t = raw.strip().lower()
    if t == "uuid":
        return "uuid"
    if t.startswith("varchar") or t.startswith("char"):
        m = re.search(r"\((\d+)\)", t)
        return f"varchar({m.group(1)})" if m else "varchar"
    if t == "text":
        return "text"
    if t in {"jsonb", "json"}:
        return "json"
    if t in {"timestamptz", "timestamp", "timestamp with time zone", "timestamp without time zone"}:
        return "timestamp"
    if t in {"boolean", "bool"}:
        return "bool"
    if t in {"int", "integer", "int4"}:
        return "int"
    if t in {"bigint", "int8"}:
        return "bigint"
    if t in {"numeric", "decimal"} or t.startswith("numeric"):
        return "numeric"
    if t == "bytea":
        return "bytes"
    return "enum" if re.fullmatch(r"[a-z_]+", t) else t


def parse_final(sql: str) -> dict[str, Any]:
    tables: dict[str, Any] = {}
    indexes: list[dict[str, Any]] = []
    enums: list[str] = []
    for stmt in statements(sql):
        em = re.match(r'CREATE TYPE "([^"]+)"', stmt)
        if em:
            enums.append(em.group(1))
            continue

        m = re.match(r'CREATE TABLE "([^"]+)"\s*\(', stmt, re.S)
        if m:
            name = m.group(1)
            body = stmt[m.end() : stmt.rindex(")")]
            cols: dict[str, Any] = {}
            cons: list[str] = []
            for part in split_top_level(body):
                if re.match(r"^(CONSTRAINT|PRIMARY KEY|UNIQUE|CHECK|FOREIGN KEY)\b", part):
                    cons.append(re.sub(r"\s+", " ", part))
                    continue
                cm = re.match(r'"([^"]+)"\s+(.*)$', part, re.S)
                if not cm:
                    cons.append(re.sub(r"\s+", " ", part))
                    continue
                cname, rest = cm.group(1), cm.group(2)
                tokens = rest.split()
                ttype: list[str] = []
                i = 0
                while i < len(tokens) and tokens[i].upper() not in COL_KEYWORDS:
                    ttype.append(tokens[i])
                    i += 1
                tail = " ".join(tokens[i:])
                cols[cname] = {
                    "type": norm_type(" ".join(ttype)),
                    "raw_type": " ".join(ttype),
                    "not_null": "NOT NULL" in tail.upper(),
                    "pk": bool(re.search(r"PRIMARY KEY", tail, re.I)),
                    "unique": bool(re.search(r"\bUNIQUE\b", tail, re.I)),
                    "default": None,
                    "check": None,
                }
                dm = re.search(
                    r"\bDEFAULT\s+(\(?[^)]*?\)?)(?=\s+(?:CHECK|UNIQUE|PRIMARY|REFERENCES|CONSTRAINT|NOT)\b|$)",
                    tail,
                    re.I,
                )
                if dm:
                    cols[cname]["default"] = dm.group(1).strip()
                ckm = re.search(r"\bCHECK\s*\((.*)$", tail, re.I)
                if ckm:
                    cols[cname]["check"] = ckm.group(1).strip()
            tables[name] = {"columns": cols, "constraints": cons}
            continue

        im = re.match(
            r'CREATE (UNIQUE )?INDEX(?:\s+"([^"]+)")?\s+ON\s+"([^"]+)"',
            stmt,
            re.S,
        )
        if im:
            indexes.append(
                {
                    "unique": bool(im.group(1)),
                    "name": im.group(2),
                    "table": im.group(3),
                    "definition": re.sub(r"\s+", " ", stmt),
                }
            )
    return {"tables": tables, "indexes": indexes, "enums": enums}


def parse_models() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from creator.infrastructure.database import metadata  # noqa: F401
    from creator.infrastructure.database.db import Base

    out: dict[str, Any] = {}
    for name, table in Base.metadata.tables.items():
        cols: dict[str, Any] = {}
        for col in table.columns:
            cols[col.name] = {
                "type": str(col.type),
                "nullable": bool(col.nullable),
                "pk": bool(col.primary_key),
                "unique": bool(col.unique),
                "default": None if col.default is None else str(col.default.arg)[:80],
                "fk": sorted(str(fk.target_fullname) for fk in col.foreign_keys),
            }
        out[name] = {
            "columns": cols,
            "constraints": sorted(
                {type(c).__name__ + ":" + (c.name or "") for c in table.constraints}
            ),
            "indexes": sorted({i.name for i in table.indexes if i.name}),
        }
    return out


def model_category(t: str) -> str:
    t = t.upper()
    if "CHAR(32)" in t or "UUID" in t:
        return "uuid"
    if "DATETIME" in t:
        return "timestamp"
    if "BOOLEAN" in t:
        return "bool"
    if "BIGINT" in t:
        return "bigint"
    if "INTEGER" in t or "SMALLINT" in t:
        return "int"
    if "NUMERIC" in t:
        return "numeric"
    if "TEXT" in t:
        return "text"
    if "JSON" in t:
        return "json"
    if m := re.search(r"VARCHAR\((\d+)\)", t):
        return f"varchar({m.group(1)})"
    if "VARCHAR" in t:
        return "varchar"
    if "BLOB" in t or "LARGEBINARY" in t:
        return "bytes"
    return "other"


def compare(final: dict[str, Any], models: dict[str, Any]) -> dict[str, Any]:
    ft = final["tables"]
    gap: dict[str, Any] = {
        "only_in_final": sorted(set(ft) - set(models)),
        "only_in_models": sorted(set(models) - set(ft)),
        "common": {},
    }
    for name in sorted(set(ft) & set(models)):
        fcols, mcols = ft[name]["columns"], models[name]["columns"]
        gap["common"][name] = {
            "columns_only_in_final": sorted(set(fcols) - set(mcols)),
            "columns_only_in_model": sorted(set(mcols) - set(fcols)),
            "nullability_diff": [
                {"column": c, "final": "NOT NULL", "model": "nullable"}
                for c in sorted(set(fcols) & set(mcols))
                if fcols[c]["not_null"] and mcols[c]["nullable"]
            ],
            "enum_columns": [
                c for c in sorted(set(fcols) & set(mcols)) if fcols[c]["type"] == "enum"
            ],
            "length_diff": [
                (c, fcols[c]["type"], model_category(mcols[c]["type"]))
                for c in sorted(set(fcols) & set(mcols))
                if (
                    fcols[c]["type"].startswith("varchar(")
                    and model_category(mcols[c]["type"]).startswith("varchar(")
                    and fcols[c]["type"] != model_category(mcols[c]["type"])
                )
                or (fcols[c]["type"] == "bigint" and model_category(mcols[c]["type"]) == "int")
            ],
        }
    return gap


def render(final: dict[str, Any], models: dict[str, Any], gap: dict[str, Any]) -> str:
    ft = final["tables"]
    new_tables = [t for t in gap["only_in_final"] if t not in RENAMES.values()]
    preserved = [t for t in EXTENSIONS if t in models]
    legacy = [t for t in LEGACY if t in models]
    dropped = [
        t
        for t in gap["only_in_models"]
        if t not in preserved and t not in legacy and t not in RENAMES
    ]
    unnamed = [i for i in final["indexes"] if not i["name"]]

    def is_simple_rename(old: str, new: str) -> bool:
        removed = set(models[old]["columns"]) - set(ft[new]["columns"])
        added = set(ft[new]["columns"]) - set(models[old]["columns"])
        return len(removed) <= 1 and len(added) <= 2

    simple_renames = sum(1 for old, new in RENAMES.items() if is_simple_rename(old, new))

    lines: list[str] = [
        "# Alinhamento ao Creator_DB_final.sql",
        "",
        "> Documento gerado por análise read-only de `docs/migration/Creator_DB_final.sql`",
        "> contra `Base.metadata`. Reproduza com:",
        ">",
        "> ```sh",
        "> python scripts/schema_parity_report.py",
        "> ```",
        "",
        "## Resumo",
        "",
        f"- Tabelas no modelo final: **{len(ft)}**",
        f"- Tabelas no metadata atual: **{len(models)}**",
        f"- Tipos ENUM no modelo final: **{len(final['enums'])}**",
        f"- Índices no modelo final: **{len(final['indexes'])}** "
        f"({len({i['table'] for i in final['indexes']})} tabelas; "
        f"{len(unnamed)} sem nome explícito; "
        f"{sum(1 for i in final['indexes'] if i['unique'])} UNIQUE)",
        f"- Tabelas novas a criar: **{len(new_tables)}**",
        f"- Nome divergente: **{len(RENAMES)}** "
        f"({simple_renames} rename simples, "
        f"{len(RENAMES) - simple_renames} redesenhos)",
        f"- Extensões de ADR preservadas: **{len(preserved)}**",
        f"- Tabelas legadas a decidir: **{len(legacy)}**",
        f"- Tabelas sem alvo no modelo final: **{len(dropped)}**",
        "",
        "## 1. Tabelas com nome divergente",
        "",
        "O nome muda, mas isso **não** implica `ALTER TABLE ... RENAME`: a maioria dos casos é",
        "redesenho de modelo, com colunas redistribuídas para as tabelas satélite novas.",
        "A coluna Veredito separa rename simples de substituição com migração de consumidores.",
        "",
        "| Atual | Final | Colunas | Veredito |",
        "| --- | --- | --- | --- |",
    ]
    for old, new in RENAMES.items():
        removed = len(set(models[old]["columns"]) - set(ft[new]["columns"]))
        added = len(set(ft[new]["columns"]) - set(models[old]["columns"]))
        verdict = (
            "renomear + alinhar"
            if is_simple_rename(old, new)
            else f"substituir: {added} colunas novas, {removed} removidas"
        )
        n_old = len(models[old]["columns"])
        n_new = len(ft[new]["columns"])
        lines.append(f"| `{old}` | `{new}` | {n_old} → {n_new} | {verdict} |")

    lines += ["", "## 2. Tabelas do modelo final ausentes no ORM", ""]
    for t in new_tables:
        cols = ", ".join(f"`{c}`" for c in ft[t]["columns"])
        n_cols = len(ft[t]["columns"])
        n_cons = len(ft[t]["constraints"])
        lines.append(f"- **`{t}`** ({n_cols} colunas, {n_cons} constraints): {cols}")

    lines += [
        "",
        "## 3. Divergências nas tabelas comuns",
        "",
        "Legenda: `+` exigida pelo modelo final e ausente no ORM; `-` presente no ORM e ausente",
        "no modelo final; `!` nullability divergente. `uuid`→`CHAR(32)` e `timestamptz`→`DATETIME`",
        "são conversões portáveis esperadas (ADR-021) e não aparecem como divergência.",
        "",
    ]
    for name in sorted(gap["common"]):
        info = gap["common"][name]
        if not (
            info["columns_only_in_final"]
            or info["columns_only_in_model"]
            or info["nullability_diff"]
            or info["enum_columns"]
            or info["length_diff"]
        ):
            continue
        lines.append(f"### `{name}`")
        if info["columns_only_in_final"]:
            lines.append(f"- `+` {', '.join('`' + c + '`' for c in info['columns_only_in_final'])}")
        if info["columns_only_in_model"]:
            lines.append(f"- `-` {', '.join('`' + c + '`' for c in info['columns_only_in_model'])}")
        if info["nullability_diff"]:
            cols = ", ".join(f"`{n['column']}`" for n in info["nullability_diff"])
            lines.append(f"- `!` NOT NULL no modelo final: {cols}")
        if info["length_diff"]:
            lines.append(
                "- tamanho/tipo: "
                + ", ".join(f"`{c}` final `{f}` vs ORM `{m}`" for c, f, m in info["length_diff"])
            )
        if info["enum_columns"]:
            lines.append(f"- enums: {', '.join('`' + c + '`' for c in info['enum_columns'])}")
        lines.append("")

    lines += [
        "## 4. Índices por tabela",
        "",
        f"O modelo final declara {len(final['indexes'])} índices. `SQLite` aceita nomes",
        "automáticos, mas a paridade precisa ser decidida tabela a tabela:",
        "nome, colunas, UNIQUE e predicado parcial.",
        "",
    ]
    by_table: dict[str, list[dict[str, Any]]] = {}
    for idx in final["indexes"]:
        by_table.setdefault(idx["table"], []).append(idx)
    for table in sorted(by_table):
        lines.append(f"### `{table}`")
        for idx in by_table[table]:
            lines.append(f"- `{idx['definition']}`")
        lines.append("")

    lines += ["## 5. Constraints CHECK/UNIQUE/REFERENCES", ""]
    for table in sorted(ft):
        if ft[table]["constraints"]:
            lines.append(f"**`{table}`**")
            for con in ft[table]["constraints"]:
                lines.append(f"- `{con}`")
            lines.append("")

    lines += [
        "## 6. Tabelas fora do modelo final",
        "",
        "| Tabela | Categoria | Ação |",
        "| --- | --- | --- |",
    ]
    for t in preserved:
        lines.append(f"| `{t}` | extensão de ADR | manter |")
    for t in legacy:
        lines.append(f"| `{t}` | legado com consumidores | decidir em issue própria |")
    for t in dropped:
        lines.append(f"| `{t}` | sem alvo no modelo final | remover após migrar consumidores |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when drift exists")
    parser.add_argument("--json", type=Path, help="also write the raw comparison here")
    parser.add_argument("--sql", type=Path, default=FINAL_SQL, help="final modeling dump")
    args = parser.parse_args()

    final = parse_final(args.sql.read_text())
    models = parse_models()
    gap = compare(final, models)
    REPORT.write_text(render(final, models, gap))
    print(f"wrote {REPORT.relative_to(ROOT)}")
    if args.json:
        args.json.write_text(json.dumps(gap, indent=2, ensure_ascii=False))
        print(f"wrote {args.json}")

    drift = bool(gap["only_in_final"] or gap["only_in_models"]) or any(
        info["columns_only_in_final"]
        or info["columns_only_in_model"]
        or info["nullability_diff"]
        or info["length_diff"]
        for info in gap["common"].values()
    )
    if args.check and drift:
        print("schema drift detected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
