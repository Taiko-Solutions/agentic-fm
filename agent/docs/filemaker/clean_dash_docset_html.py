#!/usr/bin/env python3
"""Limpieza de HTMLs de un docset de Dash (MadCap Flare / help.claris.com).

Objetivo: eliminar elementos de navegación/UI que añaden ruido y dejar el contenido principal.

Uso (ejemplo):
  python3 clean_dash_docset_html.py \
    --root "/Users/marcoperez/Library/Application Support/Dash/Docset Generator/FileMaker Pro 2025/FileMaker Pro 2025.docset/Contents/Resources/Documents"

Requisitos:
  python3 -m pip install beautifulsoup4
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception as e:  # pragma: no cover
    print("ERROR: No puedo importar BeautifulSoup (bs4).", file=sys.stderr)
    print("Instala dependencias con: python3 -m pip install beautifulsoup4", file=sys.stderr)
    raise


CSS_INLINE = """
body {
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  line-height: 1.6;
  color: #333;
}
pre, code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 14px;
}
pre {
  padding: 16px;
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}
th {
  background: #f5f5f5;
}
h1 {
  border-bottom: 2px solid #eee;
  padding-bottom: 10px;
}
""".strip()


# Selectores CSS a eliminar (si existen)
REMOVE_SELECTORS = [
    "nav",
    "#navigation",
    ".sidenav",
    ".side-menu",
    "header",
    ".header",
    "#header",
    "footer",
    ".footer",
    "#footer",
    ".breadcrumbs",
    "div.breadcrumbs",
    ".search-bar",
    "#search-bar",
    "form[role='search']",
    ".login",
    ".account",
]


ACCOUNT_WORDS = ("account", "settings", "logout")
ACCOUNT_TEXT_RE = re.compile(r"\b(?:account|settings|logout)\b", re.IGNORECASE)


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for u in units:
        if size < 1024.0:
            return f"{size:.2f} {u}"
        size /= 1024.0
    return f"{size:.2f} PB"


def safe_copytree(src: Path, dst: Path) -> Path:
    """Copia el directorio src a dst. Si dst existe, crea un sufijo timestamp."""
    target = dst
    if target.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path(f"{dst}_{ts}")
    print(f"Backup: copiando\n  ORIG: {src}\n  DEST: {target}")
    shutil.copytree(src, target)
    return target


def remove_by_selectors(soup: BeautifulSoup, selectors: list[str]) -> int:
    removed = 0
    for sel in selectors:
        try:
            matches = soup.select(sel)
        except Exception:
            # Por robustez: si un selector falla por alguna razón, seguimos.
            continue
        for el in matches:
            try:
                el.decompose()
                removed += 1
            except Exception:
                # Si algo raro ocurre con ese nodo, seguimos.
                continue
    return removed


def remove_search_inputs_and_containers(soup: BeautifulSoup) -> int:
    removed = 0
    for inp in soup.find_all("input"):
        try:
            t = (inp.get("type") or "").strip().lower()
        except Exception:
            continue
        if t != "search":
            continue

        # Quitar el contenedor más razonable (form si existe)
        container = inp.find_parent("form")
        if container is None:
            container = inp.find_parent(["div", "section", "nav", "header", "aside"]) or inp.parent

        if container is None:
            continue

        try:
            container.decompose()
            removed += 1
        except Exception:
            try:
                inp.decompose()
                removed += 1
            except Exception:
                pass
    return removed


def remove_account_links_and_buttons(soup: BeautifulSoup) -> int:
    removed = 0
    for tag in soup.find_all(["a", "button"]):
        try:
            text = tag.get_text(" ", strip=True) or ""
        except Exception:
            continue
        if not text:
            continue
        if ACCOUNT_TEXT_RE.search(text):
            try:
                tag.decompose()
                removed += 1
            except Exception:
                pass
    return removed


def remove_scripts(soup: BeautifulSoup) -> int:
    removed = 0
    for s in soup.find_all("script"):
        try:
            s.decompose()
            removed += 1
        except Exception:
            pass
    return removed


def remove_external_stylesheets(soup: BeautifulSoup) -> int:
    removed = 0
    for link in soup.find_all("link"):
        try:
            rel = link.get("rel")
            href = (link.get("href") or "").strip()
        except Exception:
            continue

        # rel puede ser lista o string
        rel_values: list[str] = []
        if isinstance(rel, list):
            rel_values = [str(x).lower() for x in rel]
        elif isinstance(rel, str):
            rel_values = [rel.lower()]

        if "stylesheet" not in rel_values:
            continue

        # Externo = http(s) o //
        if href.lower().startswith("http://") or href.lower().startswith("https://") or href.startswith("//"):
            try:
                link.decompose()
                removed += 1
            except Exception:
                pass
    return removed


def inject_inline_css(soup: BeautifulSoup) -> bool:
    head = soup.head
    if head is None:
        # Crear estructura mínima si viene muy roto
        html = soup.html
        if html is None:
            html = soup.new_tag("html")
            soup.insert(0, html)
        head = soup.new_tag("head")
        html.insert(0, head)

    # Evitar duplicados en re-ejecuciones
    existing = head.find("style", attrs={"id": "dash-docset-cleanup"})
    if existing is not None:
        existing.string = CSS_INLINE
        return True

    style = soup.new_tag("style", attrs={"id": "dash-docset-cleanup", "type": "text/css"})
    style.string = "\n" + CSS_INLINE + "\n"
    head.append(style)
    return True


def isolate_body_to_main_content(soup: BeautifulSoup, selector: str = "#mc-main-content") -> bool:
    """Reemplaza el <body> dejando solo el nodo principal (por defecto #mc-main-content).

    Esto es especialmente eficaz en HTMLs de MadCap Flare: evita que Dash/MCP indexe
    el TOC/menús gigantes y otros elementos de UI.

    Mantiene el <head> intacto (incluyendo <title>).
    """
    try:
        main = soup.select_one(selector)
    except Exception:
        main = None

    if main is None:
        return False

    body = soup.body
    if body is None:
        html = soup.html
        if html is None:
            html = soup.new_tag("html")
            soup.insert(0, html)
        body = soup.new_tag("body")
        html.append(body)

    try:
        main.extract()
    except Exception:
        # Si no se puede extraer, no tocamos el body.
        return False

    try:
        body.clear()
    except Exception:
        # Fallback: si BeautifulSoup no soporta clear en algún caso raro
        for c in list(body.contents):
            try:
                c.extract()
            except Exception:
                pass

    body.append(main)
    return True


def process_html_file(path: Path) -> tuple[int, int]:
    """Devuelve (bytes_before, bytes_after). Lanza excepción si no se puede procesar."""
    bytes_before = path.stat().st_size

    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    # 1) Limpieza global: evita JS y CSS remotos innecesarios (manteniendo <title>)
    remove_scripts(soup)
    remove_external_stylesheets(soup)

    # 2) Estrategia principal: quedarnos solo con el contenido útil
    # Si existe #mc-main-content, reconstruimos el body con SOLO ese nodo.
    has_main = isolate_body_to_main_content(soup, "#mc-main-content")

    # 3) Limpiezas adicionales (sobre el contenido que queda)
    # (Si no hay #mc-main-content, aplicamos también el barrido por selectores de UI.)
    if not has_main:
        remove_by_selectors(soup, REMOVE_SELECTORS)

    remove_search_inputs_and_containers(soup)
    remove_account_links_and_buttons(soup)

    # 4) CSS de legibilidad
    inject_inline_css(soup)

    # Guardar
    out = str(soup)
    path.write_text(out, encoding="utf-8")
    bytes_after = path.stat().st_size

    return bytes_before, bytes_after


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpia HTMLs de un docset de Dash (MadCap Flare).")
    parser.add_argument(
        "--root",
        default=str(
            Path.home()
            / "Library/Application Support/Dash/Docset Generator/FileMaker Pro 2025/FileMaker Pro 2025.docset/Contents/Resources/Documents"
        ),
        help="Directorio raíz donde están los HTMLs del docset (Documents).",
    )
    parser.add_argument(
        "--backup-name",
        default="Documents_backup",
        help="Nombre del directorio backup (se crea como hermano de Documents).",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="No crear backup (NO recomendado).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe cambios (solo informa).",
    )

    args = parser.parse_args()

    root = Path(args.root).expanduser()
    if not root.exists() or not root.is_dir():
        print(f"ERROR: No existe el directorio: {root}", file=sys.stderr)
        return 2

    backup_dst = root.parent / args.backup_name

    # Backup
    if not args.no_backup:
        if args.dry_run:
            print(f"Dry-run: NO copio backup. (Se habría copiado {root} -> {backup_dst})")
        else:
            safe_copytree(root, backup_dst)
    else:
        print("Aviso: ejecutando SIN backup (--no-backup).")

    # Recopilar ficheros
    html_files: list[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".html"):
                html_files.append(Path(dirpath) / fn)

    html_files.sort()
    total = len(html_files)
    if total == 0:
        print("No se han encontrado archivos .html. Nada que hacer.")
        return 0

    total_before = 0
    total_after = 0
    ok = 0
    failed = 0

    print(f"Procesando {total} archivos .html en:\n  {root}\n")

    for i, f in enumerate(html_files, start=1):
        rel = f.relative_to(root)
        try:
            if args.dry_run:
                b = f.stat().st_size
                total_before += b
                total_after += b
                ok += 1
                print(f"[{i}/{total}] (dry-run) OK  {rel}")
                continue

            b, a = process_html_file(f)
            total_before += b
            total_after += a
            ok += 1

            if i == 1 or i % 50 == 0 or i == total:
                # Progreso periódico para no spamear demasiado
                print(f"[{i}/{total}] OK  {rel}")
        except Exception as e:
            failed += 1
            try:
                total_before += f.stat().st_size
                total_after += f.stat().st_size
            except Exception:
                pass
            print(f"[{i}/{total}] FAIL {rel} -> {type(e).__name__}: {e}", file=sys.stderr)

    print("\n--- Estadísticas ---")
    print(f"Archivos encontrados:  {total}")
    print(f"Procesados OK:         {ok}")
    print(f"Fallidos:              {failed}")
    print(f"Tamaño total (antes):  {human_bytes(total_before)}")
    print(f"Tamaño total (después): {human_bytes(total_after)}")
    if total_before > 0:
        delta = total_after - total_before
        pct = (delta / total_before) * 100.0
        print(f"Diferencia:            {human_bytes(delta)} ({pct:+.2f}%)")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
