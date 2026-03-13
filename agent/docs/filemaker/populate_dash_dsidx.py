#!/usr/bin/env python3
"""Poblar docSet.dsidx con entradas tipadas (Dash docset) para FileMaker Pro.

Este script:
- Hace backup del docSet.dsidx
- Crea searchIndex si no existe
- Recorre todos los .html bajo Documents y genera entradas (name/type/path)
- Añade aliases para Get(X): GetX y "Get X"
- INSERT OR IGNORE (no borra nada)
- VACUUM al final

Uso recomendado:
  python3 populate_dash_dsidx.py \
    --docset "/Users/marcoperez/Library/Application Support/Dash/Docset Generator/FileMaker Pro 2025/FileMaker Pro 2025.docset"

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

# El docset puede venir de Pro Help o Server Help (y otros podrían heredar el mismo patrón)
TITLE_SUFFIX_RE = re.compile(
    r"\s*\|\s*Claris\s+FileMaker\s+(?:Pro|Server)\s+Help\s*$",
    re.IGNORECASE,
)

RE_GET_TITLE = re.compile(r"^Get\(([^)]+)\)$")
RE_EVENT_TITLE = re.compile(r"^On[A-Z].+")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean_title(raw_title: str) -> str:
    t = (raw_title or "").strip()
    t = TITLE_SUFFIX_RE.sub("", t).strip()
    # Normalización de espacios (incluye NBSP)
    t = " ".join(t.replace("\xa0", " ").split())
    return t


def extract_html_info(html_path: Path) -> tuple[str, str]:
    """Devuelve (clean_title, main_text). main_text procede de #mc-main-content o body."""
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
    if main is not None:
        try:
            main_text = main.get_text("\n", strip=True)
        except Exception:
            main_text = ""

    # Normalizar para búsquedas de heurística
    main_text = main_text.replace("\xa0", " ")
    return title, main_text


def text_has_all(text: str, needles: list[str]) -> bool:
    t = text.lower()
    return all(n.lower() in t for n in needles)


def classify_page(title: str, main_text: str, rel_path: str) -> str:
    """Clasificación por reglas (prioridad a->f)."""
    # Helpers
    filename = Path(rel_path).name
    stem = filename.rsplit(".", 1)[0]

    # a) Function
    # Señales fuertes: secciones Format + Parameters + Data type returned
    if text_has_all(main_text, ["format", "parameters", "data type returned"]):
        # Incluir Get(...)
        if title.startswith("Get("):
            return "Function"
        # Otras funciones: normalmente 1 token como nombre
        # (No forzamos 1 token: dejamos que la presencia de secciones mande.)
        return "Function"

    # b) Command (script steps)
    # Señales: Compatibility + Options + Originated in version
    if text_has_all(main_text, ["compatibility", "options", "originated in version"]):
        return "Command"

    # c) Event (script triggers)
    # Título tipo OnXxx o menciona script trigger al principio
    first_lines = "\n".join(main_text.splitlines()[:10]).lower()
    if RE_EVENT_TITLE.match(title) or re.match(r"^on[a-z0-9-]+$", stem):
        # Muchas páginas conceptuales empiezan por "On..."? en Pro Help suele ser trigger.
        return "Event"
    if "script trigger" in first_lines:
        return "Event"
    if "script-triggers-reference" in main_text.lower():
        return "Event"

    # d) Error
    if "error code" in (title.lower() + "\n" + main_text.lower()) or "error codes" in (title.lower() + "\n" + main_text.lower()):
        return "Error"
    if "error" in filename.lower():
        return "Error"

    # e) Category
    fn_lower = filename.lower()
    if fn_lower.endswith("-script-steps.html") or fn_lower.endswith("-functions.html") or fn_lower.endswith("-reference.html"):
        return "Category"
    if re.search(r"\b(script steps|functions|reference)\b", title, re.IGNORECASE):
        # Algunas páginas de detalle también dicen "script step"; limitamos a títulos que parecen índice
        if any(k in title.lower() for k in ["script steps", "functions", "reference"]):
            # Heurística: si no es "... | ..." ya se limpió; títulos de índice suelen ser cortos.
            return "Category"

    # f) Guide
    return "Guide"


def compute_index_name(title: str, rel_path: str, kind: str) -> str:
    """name para searchIndex."""
    name = title.strip()
    # Fallback si title está vacío: usar filename
    if not name:
        name = Path(rel_path).stem

    # Para Function Get(...) mantener tal cual
    if kind == "Function" and name.startswith("Get("):
        return name

    return name


def get_aliases_for_get_function(name: str) -> list[str]:
    """Para Get(X) -> [GetX, 'Get X']"""
    m = RE_GET_TITLE.match(name)
    if not m:
        return []
    inner = m.group(1).strip()
    if not inner:
        return []
    # GetCurrentDate y "Get CurrentDate"
    return [f"Get{inner}", f"Get {inner}"]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS anchor ON searchIndex (name, type, path);"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Puebla docSet.dsidx con entradas tipadas (Dash).")
    p.add_argument(
        "--docset",
        required=True,
        help="Ruta al .docset (directorio).",
    )
    p.add_argument(
        "--content-subdir",
        default="help.claris.com/en/pro-help/content",
        help="Subdirectorio bajo Documents donde están los HTMLs a indexar.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe en SQLite (solo analiza y muestra stats).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Procesar solo N HTMLs (0 = todos).",
    )
    args = p.parse_args()

    docset = Path(args.docset).expanduser()
    if not docset.exists() or not docset.is_dir():
        print(f"ERROR: docset no encontrado: {docset}", file=sys.stderr)
        return 2

    dsidx = docset / DSIDX_REL
    docs_root = docset / DOCS_REL
    html_root = docs_root / args.content_subdir

    if not dsidx.exists():
        print(f"ERROR: No existe docSet.dsidx: {dsidx}", file=sys.stderr)
        return 2
    if not html_root.exists() or not html_root.is_dir():
        print(f"ERROR: No existe el directorio de HTMLs: {html_root}", file=sys.stderr)
        return 2

    # 1) Backup dsidx
    backup_path = dsidx.with_suffix(dsidx.suffix + f".bak_{now_stamp()}")
    if args.dry_run:
        print(f"Dry-run: no creo backup. (Se habría copiado {dsidx} -> {backup_path})")
    else:
        shutil.copy2(dsidx, backup_path)
        print(f"Backup creado: {backup_path}")

    # Conexión
    conn = sqlite3.connect(str(dsidx))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        ensure_schema(conn)
        conn.commit()

        html_files = sorted(html_root.rglob("*.html"))
        if args.limit and args.limit > 0:
            html_files = html_files[: args.limit]

        total_html = len(html_files)
        if total_html == 0:
            print("No se han encontrado HTMLs.")
            return 0

        print(f"HTMLs a procesar: {total_html}")
        type_counts: Counter[str] = Counter()

        inserts_attempted = 0
        inserts_effective_before = conn.total_changes

        examples_by_type: dict[str, list[tuple[str, str]]] = defaultdict(list)

        # Inserción preparada
        insert_sql = "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?, ?, ?);"

        for i, html_path in enumerate(html_files, start=1):
            rel_to_docs = html_path.relative_to(docs_root).as_posix()

            try:
                title, main_text = extract_html_info(html_path)
                kind = classify_page(title, main_text, rel_to_docs)
                name = compute_index_name(title, rel_to_docs, kind)

                # (4) Insert principal
                if not args.dry_run:
                    conn.execute(insert_sql, (name, kind, rel_to_docs))
                inserts_attempted += 1

                # (5) Aliases Get
                if kind == "Function":
                    aliases = get_aliases_for_get_function(name)
                    for a in aliases:
                        if not args.dry_run:
                            conn.execute(insert_sql, (a, kind, rel_to_docs))
                        inserts_attempted += 1

                type_counts[kind] += 1

                if len(examples_by_type[kind]) < 5:
                    examples_by_type[kind].append((name, rel_to_docs))

                if i == 1 or i % 100 == 0 or i == total_html:
                    print(f"[{i}/{total_html}] {kind:8} {name}")
            except Exception as e:
                # No paramos
                print(
                    f"[{i}/{total_html}] FAIL {html_path.name} -> {type(e).__name__}: {e}",
                    file=sys.stderr,
                )

        if not args.dry_run:
            conn.commit()

        inserts_effective_after = conn.total_changes
        inserted_rows = inserts_effective_after - inserts_effective_before

        # 7) Stats
        print("\n--- Estadísticas ---")
        print(f"Total HTMLs procesados: {total_html}")
        for t in ["Function", "Command", "Event", "Error", "Category", "Guide"]:
            print(f"{t:8}: {type_counts.get(t, 0)}")
        print(f"Entradas intentadas (incl. aliases Get): {inserts_attempted}")
        print(f"Entradas insertadas (nuevas):          {inserted_rows}")

        print("\n--- Muestras (5 primeras por tipo) ---")
        for t in ["Function", "Command", "Event", "Error", "Category", "Guide"]:
            sample = examples_by_type.get(t, [])
            if not sample:
                continue
            print(f"\n{t}:")
            for n, pth in sample[:5]:
                print(f"- {n} -> {pth}")

        # 8) VACUUM
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
