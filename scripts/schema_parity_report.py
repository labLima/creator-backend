#!/usr/bin/env python3
"""Render the Creator_DB_final.sql parity report.

The parsing and comparison live in
``creator.infrastructure.database.final_schema`` so the parity tests use the
exact same logic. This script only loads the metadata, runs the comparison and
renders the markdown report.

Usage:
    python scripts/schema_parity_report.py            # write the markdown report
    python scripts/schema_parity_report.py --check    # exit 1 when drift exists
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from creator.infrastructure.database import metadata as _models  # noqa: E402, F401
from creator.infrastructure.database.db import Base  # noqa: E402
from creator.infrastructure.database.final_schema import (  # noqa: E402
    ADR_EXTENSIONS,
    LEGACY_RETENTION,
    NO_TARGET,
    RENAME_MAP,
    FinalSchema,
    Gap,
    compare,
    gap_counts,
    gap_digest,
    parse_final,
    parse_models,
    sha256_file,
)

FINAL_SQL = ROOT / "docs" / "migration" / "Creator_DB_final.sql"
REPORT = ROOT / "docs" / "migration" / "schema-final-alignment.md"


def render(final: FinalSchema, gap: Gap, dump_hash: str, model_count: int) -> str:
    counts = gap_counts(gap)
    new_tables = sorted(gap.details.get("table_missing", []))
    lines: list[str] = [
        "# Alinhamento ao Creator_DB_final.sql",
        "",
        "> Gerado por `scripts/schema_parity_report.py` a partir de",
        "> `docs/migration/Creator_DB_final.sql` contra `Base.metadata`.",
        "> Não edite à mão: regenere o arquivo.",
        "",
        "## Resumo",
        "",
        f"- Dump: `sha256 {dump_hash}`",
        f"- Tabelas no modelo final: **{len(final.tables)}**",
        f"- Tabelas no metadata atual: **{model_count}**",
        f"- Tipos ENUM: **{len(final.enums)}**",
        f"- Índices: **{len(final.indexes)}** "
        f"({sum(1 for index in final.indexes if index.name)} nomeados, "
        f"{sum(1 for index in final.indexes if not index.name)} anônimos)",
        f"- Foreign keys: **{len(final.foreign_keys)}** "
        f"({sum(1 for fk in final.foreign_keys if len(fk.columns) > 1)} compostas)",
        f"- Funções/triggers/views: **{len(final.storage_objects)}**",
        f"- Divergências: **{gap.total()}**",
        "",
        "## Divergências por categoria",
        "",
        "| Categoria | Ocorrências |",
        "| --- | --- |",
    ]
    for category, count in counts.items():
        lines.append(f"| `{category}` | {count} |")

    lines += [
        "",
        "## 1. Tabelas com nome divergente",
        "",
        "O mapa é aplicado uma vez na comparação, então a tabela renomeada não conta",
        "como ausente nem excedente. Nenhum caso é `ALTER TABLE ... RENAME` puro:",
        "`role` muda de vocabulário, entra `status` e sai `deleted_at`.",
        "",
        "| Final | Metadata |",
        "| --- | --- |",
    ]
    for final_name, model_name in sorted(RENAME_MAP.items()):
        lines.append(f"| `{final_name}` | `{model_name}` |")

    lines += ["", "## 2. Tabelas do modelo final ausentes no ORM", ""]
    if new_tables:
        for name in new_tables:
            table = final.tables[name]
            columns = ", ".join(f"`{column}`" for column in table.columns)
            lines.append(
                f"- **`{name}`** ({len(table.columns)} colunas, "
                f"{len(table.checks)} CHECKs): {columns}"
            )
    else:
        lines.append("Nenhuma.")
    lines.append("")

    sections = [
        (
            "3. Colunas, tipos e nullability",
            (
                "column_missing",
                "column_extra",
                "pk_mismatch",
                "nullability",
                "width",
                "default_missing",
            ),
        ),
        ("4. Enums", ("enum",)),
        ("5. Índices", ("index_missing", "index_extra", "index_name")),
        ("6. Foreign keys", ("fk_missing", "fk_extra", "fk_ondelete")),
        ("7. CHECK constraints", ("check_missing", "check_extra")),
    ]
    for title, categories in sections:
        total = sum(counts.get(category, 0) for category in categories)
        lines += [f"## {title}", "", f"Total: **{total}**.", ""]
        if not total:
            lines += ["Sem divergência.", ""]
            continue
        for category in categories:
            items = gap.details.get(category, [])
            if not items:
                continue
            lines += [f"### `{category}` ({len(items)})", ""]
            lines += [f"- `{item}`" for item in items]
            lines.append("")

    lines += [
        "## 8. Funções, triggers e views",
        "",
        "Objetos com regra de negócio no banco. A decisão é objeto a objeto na tarefa",
        "T20 (`SHC-21`), que classifica cada um em trigger SQLite, guarda de aplicação",
        "com teste, ou fora de escopo justificado.",
        "",
        "| Tipo | Nome |",
        "| --- | --- |",
    ]
    for kind, name in final.storage_objects:
        lines.append(f"| {kind} | `{name}` |")
    lines.append("")

    lines += [
        "## 9. Tabelas fora do modelo final",
        "",
        "| Tabela | Categoria |",
        "| --- | --- |",
    ]
    for name in ADR_EXTENSIONS:
        lines.append(f"| `{name}` | extensão de ADR (preservada) |")
    for name in LEGACY_RETENTION:
        lines.append(f"| `{name}` | legado com consumidores (ADR-029 decide) |")
    for name in NO_TARGET:
        lines.append(f"| `{name}` | sem alvo no modelo final (ADR-029 decide) |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 when drift exists")
    parser.add_argument("--json", type=Path, help="also write the raw gap here")
    parser.add_argument("--sql", type=Path, default=FINAL_SQL, help="final modeling dump")
    args = parser.parse_args()

    final = parse_final(args.sql.read_text(encoding="utf-8"))
    models = parse_models(Base.metadata)
    gap = compare(final, models)
    dump_hash = sha256_file(args.sql)
    REPORT.write_text(render(final, gap, dump_hash, len(models)), encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)} — {gap.total()} divergences")
    if args.json:
        payload = {
            "counts": gap_counts(gap),
            "digest": gap_digest(gap),
            "details": gap.details,
        }
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {args.json}")

    if args.check and gap.total():
        print("schema drift detected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
