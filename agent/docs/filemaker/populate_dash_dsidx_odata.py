#!/usr/bin/env python3
"""Poblar docSet.dsidx con entradas tipadas para FileMaker OData Guide (Dash docset).

Tipos objetivo (Dash searchIndex.type):
- Endpoint
- Error
- Category
- Guide

Este script:
- Hace backup del docSet.dsidx
- Crea searchIndex si no existe
- Recorre todos los .html bajo Documents (excluye Documents_backup si existiera dentro)
- Clasifica por heurísticas específicas de OData (endpoints HTTP / rutas /fmi/odata/v4)
- INSERT OR IGNORE (no borra entradas existentes)
- VACUUM

Uso:
  python3 populate_dash_dsidx_odata.py \
    --docset "/Users/marcoperez/Library/Application Support/Dash/Docset Generator/FileMaker OData Guide/FileMaker OData Guide.docset"

Requisitos:
  python3 -m pip install beautifulsoup4
"""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    print("ERROR: Falta BeautifulSoup (bs4).", file=sys.stderr)
    print("Instala con: python3 -m pip install beautifulsoup4", file=sys.stderr)
    raise


DSIDX_REL = Path("Contents/Resources/docSet.dsidx")
DOCS_REL = Path("Contents/Resources/Documents")

# Quitar sufijos típicos de title
TITLE_SUFFIX_RE = re.compile(
    r"\s*\|\s*Claris\s+FileMaker\s+OData\s+(?:API\s+)?Guide\s*$",
    re.IGNORECASE,
)

HTTP_METHOD_RE = re.compile(r"\b(GET|POST|PATCH|DELETE|PUT)\b")
ODATA_ROUTE_RE = re.compile(r"/fmi/odata/v4/[^\s)\]>'\"]+")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean_title(raw_title: str) -> str:
    t = (raw_title or "").strip()
    t = TITLE_SUFFIX_RE.sub("", t).strip()
    t = " ".join(t.replace("\xa0", " ").split())
    return t


def extract_html_info(html_path: Path) -> tuple[str, str, int]:
    """Devuelve (title_limpio, main_text, link_count)."""
    html = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    raw_title = ""
    if soup.title and soup.title.string:
        raw_title = str(soup.title.string)
    title = clean_title(raw_title)

    main = None
    try:
        main = soup.select_one("#mc-main-content")
    except Exception:
        main = None
    if main is None:
        main = soup.body

    main_text = ""
    link_count = 0
    if main is not None:
        try:
            main_text = main.get_text("\n", strip=True)
        except Exception:
            main_text = ""
        try:
            link_count = len(main.find_all("a"))
        except Exception:
            link_count = 0

    main_text = main_text.replace("\xa0", " ")
    return title, main_text, link_count


def classify_page(title: str, main_text: str, rel_path: str, link_count: int) -> str:
    """Clasifica por reglas (prioridad): Endpoint, Error, Category, Guide."""
    filename = Path(rel_path).name.lower()
    title_l = title.lower()
    text_l = main_text.lower()

    # a) Endpoint
    # Señal: ruta /fmi/odata/v4 y presencia de método HTTP
    has_route = "/fmi/odata/v4" in text_l
    has_method = bool(HTTP_METHOD_RE.search(main_text))
    if has_route and has_method:
        return "Endpoint"

    # b) Error
    if "error" in title_l or "error" in filename or "error code" in text_l or "error codes" in text_l:
        return "Error"

    # c) Category
    if filename in {"index.html", "overview.html", "toc.html"}:
        return "Category"
    if title_l in {"overview", "introduction", "contents", "table of contents"}:
        return "Category"

    # Heurística: muchos links y poco texto => índice
    if link_count >= 30 and len(main_text) < 2500:
        return "Category"

    # d) Guide
    return "Guide"


def compute_name(title: str, main_text: str, kind: str) -> str:
    """Obtiene name para searchIndex."""
    if title:
        return title

    # Fallback si no hay title: intentar construir desde endpoint
    if kind == "Endpoint":
        method = HTTP_METHOD_RE.search(main_text)
        route = ODATA_ROUTE_RE.search(main_text)
        if method and route:
            return f"{method.group(1)} {route.group(0)}"

    return "(untitled)"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS anchor ON searchIndex (name, type, path);"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Puebla docSet.dsidx (Dash) para FileMaker OData Guide.")
    p.add_argument("--docset", required=True, help="Ruta al .docset (directorio).")
    p.add_argument("--dry-run", action="store_true", help="No escribe en SQLite.")
    p.add_argument("--limit", type=int, default=0, help="Procesar solo N HTMLs (0=todos).")
    args = p.parse_args()

    docset = Path(args.docset).expanduser()
    if not docset.exists() or not docset.is_dir():
        print(f"ERROR: docset no encontrado: {docset}", file=sys.stderr)
        return 2

    dsidx = docset / DSIDX_REL
    docs_root = docset / DOCS_REL

    if not dsidx.exists():
        print(f"ERROR: No existe docSet.dsidx: {dsidx}", file=sys.stderr)
        return 2
    if not docs_root.exists() or not docs_root.is_dir():
        print(f"ERROR: No existe Documents: {docs_root}", file=sys.stderr)
        return 2

    # Backup
    backup_path = dsidx.with_suffix(dsidx.suffix + f".bak_{now_stamp()}")
    if args.dry_run:
        print(f"Dry-run: no creo backup. (Se habría copiado {dsidx} -> {backup_path})")
    else:
        shutil.copy2(dsidx, backup_path)
        print(f"Backup creado: {backup_path}")

    conn = sqlite3.connect(str(dsidx))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        ensure_schema(conn)
        conn.commit()

        html_files = sorted([p for p in docs_root.rglob("*.html") if "Documents_backup" not in str(p)])
        if args.limit and args.limit > 0:
            html_files = html_files[: args.limit]

        total = len(html_files)
        print(f"HTMLs a procesar: {total}")
        if total == 0:
            return 0

        type_counts: Counter[str] = Counter()
        examples: dict[str, list[tuple[str, str]]] = defaultdict(list)

        insert_sql = "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?, ?, ?);"
        inserts_attempted = 0
        before = conn.total_changes

        for i, html_path in enumerate(html_files, start=1):
            rel_path = html_path.relative_to(docs_root).as_posix()
            try:
                title, text, link_count = extract_html_info(html_path)
                kind = classify_page(title, text, rel_path, link_count)
                name = compute_name(title, text, kind)

                if not args.dry_run:
                    conn.execute(insert_sql, (name, kind, rel_path))
                inserts_attempted += 1

                type_counts[kind] += 1
                if len(examples[kind]) < 5:
                    examples[kind].append((name, rel_path))

                if i == 1 or i % 50 == 0 or i == total:
                    print(f"[{i}/{total}] {kind:8} {name}")
            except Exception as e:
                print(f"[{i}/{total}] FAIL {html_path.name} -> {type(e).__name__}: {e}", file=sys.stderr)

        if not args.dry_run:
            conn.commit()

        inserted = conn.total_changes - before

        print("\n--- Estadísticas ---")
        print(f"Total HTMLs procesados: {total}")
        for t in ["Endpoint", "Error", "Category", "Guide"]:
            print(f"{t:8}: {type_counts.get(t, 0)}")
        print(f"Entradas intentadas:   {inserts_attempted}")
        print(f"Entradas insertadas:   {inserted}")

        print("\n--- Muestras (5 primeras por tipo) ---")
        for t in ["Endpoint", "Error", "Category", "Guide"]:
            if not examples.get(t):
                continue
            print(f"\n{t}:")
            for n, pth in examples[t][:5]:
                print(f"- {n} -> {pth}")

        if not args.dry_run:
            print("\nEjecutando VACUUM...")
            conn.execute("VACUUM;")
            conn.commit()
            print("VACUUM completado.")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
