#!/usr/bin/env python3
"""Construir manualmente un docset de Dash para la guía OData de FileMaker.

Motivación:
- MadCap Flare puede cargar el TOC por JavaScript, y Dash Docset Generator no siempre descarga subpáginas.

Este script hace 3 pasos:
1) Descarga
   - Backup de Documents -> Documents_backup(_timestamp)
   - Descarga una lista inicial de páginas desde BASE_URL
   - Descubre páginas adicionales buscando enlaces .html dentro de /en/odata-guide/content/
2) Limpieza HTML
   - Deja solo #mc-main-content dentro de <body> (si existe), conservando <title>
   - Inyecta CSS inline
   - Elimina <script>
3) Indexación tipada
   - Backup de docSet.dsidx
   - DROP+CREATE searchIndex
   - Clasifica cada HTML: Endpoint / Error / Category / Guide
   - INSERT OR IGNORE
   - VACUUM

Uso:
  python3 build_odata_docset_manual.py \
    --docset "/Users/marcoperez/Library/Application Support/Dash/Docset Generator/FileMaker OData Guide/FileMaker OData Guide.docset"

Requisitos:
  python3 -m pip install beautifulsoup4
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    print("ERROR: Falta BeautifulSoup (bs4).", file=sys.stderr)
    print("Instala con: python3 -m pip install beautifulsoup4", file=sys.stderr)
    raise


DEFAULT_DOCSET = (
    "/Users/marcoperez/Library/Application Support/Dash/Docset Generator/FileMaker OData Guide/"
    "FileMaker OData Guide.docset"
)
BASE_URL = "https://help.claris.com/en/odata-guide/content/"

SEED_PAGES = [
    "index.html",
    "using-odata-with-filemaker-databases.html",
    "how-odata-calls-are-processed.html",
    "api-solution-comparison.html",
    "odata-filemaker-terminology.html",
    "enable-access.html",
    "odata-standard-conformance.html",
    "write-odata-api-calls.html",
    "database-structure-metadata.html",
    "modifying-data.html",
    "request-data.html",
    "batch-requests.html",
    "webhook-options.html",
    "query-options.html",
    "modify-schema.html",
    "run-scripts.html",
    "work-with-container-data.html",
    "host-databases-for-odata-access.html",
    "test-odata-access.html",
    "monitor-odata-access.html",
]

DSIDX_REL = Path("Contents/Resources/docSet.dsidx")
DOCS_REL = Path("Contents/Resources/Documents")
CONTENT_REL = Path("help.claris.com/en/odata-guide/content")

HTTP_METHOD_RE = re.compile(r"\b(GET|POST|PATCH|DELETE|PUT)\b")

# Limpieza de title
TITLE_SUFFIX_RE = re.compile(
    r"\s*\|\s*Claris\s+FileMaker\s+OData\s+(?:API\s+)?Guide\s*$",
    re.IGNORECASE,
)

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


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for u in units:
        if size < 1024.0:
            return f"{size:.2f} {u}"
        size /= 1024.0
    return f"{size:.2f} PB"


def dir_size_bytes(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except Exception:
            pass
    return total


def safe_backup_dir(src: Path, dst_base: Path) -> Path:
    dst = dst_base
    if dst.exists():
        dst = Path(f"{dst_base}_{now_stamp()}")
    print(f"Backup Documents:\n  ORIG: {src}\n  DEST: {dst}")
    shutil.copytree(src, dst)
    return dst


def safe_backup_file(src: Path) -> Path:
    backup = src.with_suffix(src.suffix + f".bak_{now_stamp()}")
    shutil.copy2(src, backup)
    return backup


def url_for_page(page: str) -> str:
    return urllib.parse.urljoin(BASE_URL, page)


def normalize_discovered_href(href: str) -> str | None:
    if not href:
        return None

    href = href.strip()

    # Quitar fragment/query
    href = href.split("#", 1)[0].split("?", 1)[0]

    if not href.endswith(".html"):
        return None

    def strip_accidental_content_prefix(p: str) -> str:
        # Hemos visto hrefs tipo "content/index.html" dentro de páginas que ya están en /content/.
        # Eso provoca URLs duplicadas /content/content/... (404 o duplicados). Normalizamos aquí.
        while p.startswith("content/"):
            p = p[len("content/") :]
        return p

    # Absolutas
    if href.startswith("http://") or href.startswith("https://"):
        u = urllib.parse.urlparse(href)
        if u.netloc != "help.claris.com":
            return None
        # Queremos solo /en/odata-guide/content/...
        if not u.path.startswith("/en/odata-guide/content/"):
            return None
        rel = u.path.split("/en/odata-guide/content/", 1)[1]
        return strip_accidental_content_prefix(rel)

    # Root-relative
    if href.startswith("/"):
        if not href.startswith("/en/odata-guide/content/"):
            return None
        rel = href.split("/en/odata-guide/content/", 1)[1]
        return strip_accidental_content_prefix(rel)

    # Relative
    # En MadCap, suelen ser relativos al mismo dir, o con ./
    href = href.lstrip("./")
    if ".." in href:
        return None

    return strip_accidental_content_prefix(href)


def fetch_url(url: str, timeout_s: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (DashDocsetBuilder/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def download_pages(content_dir: Path, seed_pages: list[str]) -> set[str]:
    """Descarga páginas seed y descubre páginas adicionales por enlaces internos.

    Devuelve el set total de páginas (paths) descargadas relativo a BASE_URL.
    """

    content_dir.mkdir(parents=True, exist_ok=True)

    discovered: set[str] = set()
    q: deque[str] = deque()

    for p in seed_pages:
        p = p.strip()
        if not p:
            continue
        discovered.add(p)
        q.append(p)

    downloaded_ok = 0
    downloaded_fail = 0

    while q:
        page = q.popleft()
        url = url_for_page(page)
        dst = content_dir / page

        # Evitar re-descargas si el fichero ya existe
        if dst.exists() and dst.stat().st_size > 0:
            # Aun así, intentar descubrir links desde el HTML local.
            try:
                html = dst.read_text(encoding="utf-8", errors="replace")
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a"):
                    new = normalize_discovered_href(a.get("href") or "")
                    if new and new not in discovered:
                        discovered.add(new)
                        q.append(new)
            except Exception:
                pass
            continue

        try:
            data = fetch_url(url)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            downloaded_ok += 1
            print(f"DOWNLOAD OK  {page}")

            # Descubrir enlaces adicionales
            try:
                soup = BeautifulSoup(data, "html.parser")
                for a in soup.find_all("a"):
                    new = normalize_discovered_href(a.get("href") or "")
                    if new and new not in discovered:
                        discovered.add(new)
                        q.append(new)
            except Exception:
                pass

            # Ser amable con el servidor
            time.sleep(0.15)

        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            downloaded_fail += 1
            print(f"DOWNLOAD FAIL {page} -> {type(e).__name__}: {e}", file=sys.stderr)
        except Exception as e:
            downloaded_fail += 1
            print(f"DOWNLOAD FAIL {page} -> {type(e).__name__}: {e}", file=sys.stderr)

    print(f"\nDescarga completada: OK={downloaded_ok}, FAIL={downloaded_fail}, TOTAL={len(discovered)}")
    return discovered


def clean_title(raw_title: str) -> str:
    t = (raw_title or "").strip()
    t = TITLE_SUFFIX_RE.sub("", t).strip()
    t = " ".join(t.replace("\xa0", " ").split())
    return t


def inject_css(soup: BeautifulSoup) -> None:
    head = soup.head
    if head is None:
        html = soup.html
        if html is None:
            html = soup.new_tag("html")
            soup.insert(0, html)
        head = soup.new_tag("head")
        html.insert(0, head)

    existing = head.find("style", attrs={"id": "dash-docset-cleanup"})
    if existing is not None:
        existing.string = "\n" + CSS_INLINE + "\n"
        return

    style = soup.new_tag("style", attrs={"id": "dash-docset-cleanup", "type": "text/css"})
    style.string = "\n" + CSS_INLINE + "\n"
    head.append(style)


def isolate_body_to_main(soup: BeautifulSoup) -> bool:
    try:
        main = soup.select_one("#mc-main-content")
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
        return False

    try:
        body.clear()
    except Exception:
        for c in list(body.contents):
            try:
                c.extract()
            except Exception:
                pass

    body.append(main)
    return True


def clean_html_files(content_dir: Path) -> tuple[int, int, int]:
    # Limpiar recursivamente, pero ignorar el subárbol accidental content/content/
    html_files = []
    for p in sorted(content_dir.rglob("*.html")):
        rel = p.relative_to(content_dir).as_posix()
        if rel.startswith("content/"):
            continue
        html_files.append(p)

    total = len(html_files)

    before = 0
    after = 0
    ok = 0

    for i, p in enumerate(html_files, start=1):
        try:
            b = p.stat().st_size
            html = p.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            # quitar scripts
            for s in list(soup.find_all("script")):
                try:
                    s.decompose()
                except Exception:
                    pass

            isolate_body_to_main(soup)
            inject_css(soup)

            out = str(soup)
            p.write_text(out, encoding="utf-8")
            a = p.stat().st_size

            before += b
            after += a
            ok += 1

            if i == 1 or i % 10 == 0 or i == total:
                print(f"[{i}/{total}] CLEAN OK  {p.name}")
        except Exception as e:
            before += p.stat().st_size if p.exists() else 0
            after += p.stat().st_size if p.exists() else 0
            print(f"[{i}/{total}] CLEAN FAIL {p.name} -> {type(e).__name__}: {e}", file=sys.stderr)

    return total, before, after


def ensure_searchindex_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
    )
    conn.execute(
        "CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);"
    )


def classify_odata_page(title: str, text: str, rel_path: str, link_count: int) -> str:
    filename = Path(rel_path).name.lower()
    title_l = title.lower()
    text_l = text.lower()

    # Endpoint
    has_route = "/fmi/odata/v4" in text_l
    has_method = bool(HTTP_METHOD_RE.search(text))
    if has_route and has_method:
        return "Endpoint"

    # Error
    if "error" in title_l or "error" in filename or "error code" in text_l or "error codes" in text_l:
        return "Error"

    # Category
    if filename in {"index.html", "overview.html", "toc.html"}:
        return "Category"
    if title_l in {"overview", "introduction", "contents", "table of contents"}:
        return "Category"
    if link_count >= 25 and len(text) < 3000:
        return "Category"

    return "Guide"


def index_dsidx(docset: Path, documents_root: Path, content_dir: Path) -> None:
    dsidx = docset / DSIDX_REL
    backup = safe_backup_file(dsidx)
    print(f"Backup dsidx: {backup}")

    conn = sqlite3.connect(str(dsidx))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        # Borrar y recrear (pedido explícito)
        conn.execute("DROP TABLE IF EXISTS searchIndex;")
        conn.execute("DROP INDEX IF EXISTS anchor;")
        ensure_searchindex_schema(conn)
        conn.commit()

        html_files = []
        for p in sorted(content_dir.rglob("*.html")):
            rel = p.relative_to(content_dir).as_posix()
            if rel.startswith("content/"):
                continue
            html_files.append(p)

        total = len(html_files)
        if total == 0:
            print("No hay HTMLs para indexar.")
            return

        insert_sql = "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?, ?, ?);"
        before_changes = conn.total_changes

        counts: Counter[str] = Counter()
        examples: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for i, p in enumerate(html_files, start=1):
            rel_path = p.relative_to(documents_root).as_posix()
            try:
                html = p.read_text(encoding="utf-8", errors="replace")
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

                text = ""
                link_count = 0
                if main is not None:
                    try:
                        text = main.get_text("\n", strip=True)
                    except Exception:
                        text = ""
                    try:
                        link_count = len(main.find_all("a"))
                    except Exception:
                        link_count = 0

                text = text.replace("\xa0", " ")

                kind = classify_odata_page(title, text, rel_path, link_count)
                name = title or Path(rel_path).stem

                conn.execute(insert_sql, (name, kind, rel_path))

                counts[kind] += 1
                if len(examples[kind]) < 5:
                    examples[kind].append((name, rel_path))

                if i == 1 or i % 10 == 0 or i == total:
                    print(f"[{i}/{total}] INDEX {kind:8} {name}")

            except Exception as e:
                print(f"[{i}/{total}] INDEX FAIL {p.name} -> {type(e).__name__}: {e}", file=sys.stderr)

        conn.commit()

        inserted = conn.total_changes - before_changes

        print("\n--- Estadísticas indexación ---")
        print(f"Total HTMLs: {total}")
        for t in ["Endpoint", "Error", "Category", "Guide"]:
            print(f"{t:8}: {counts.get(t, 0)}")
        print(f"Entradas insertadas: {inserted}")

        print("\n--- Muestras (5 primeras por tipo) ---")
        for t in ["Endpoint", "Error", "Category", "Guide"]:
            if not examples.get(t):
                continue
            print(f"\n{t}:")
            for n, rp in examples[t][:5]:
                print(f"- {n} -> {rp}")

        print("\nEjecutando VACUUM...")
        conn.execute("VACUUM;")
        conn.commit()
        print("VACUUM completado.")

    finally:
        conn.close()


def main() -> int:
    global BASE_URL

    ap = argparse.ArgumentParser(description="Construye manualmente el docset OData (descarga + limpieza + dsidx).")
    ap.add_argument("--docset", default=DEFAULT_DOCSET, help="Ruta al .docset existente (directorio).")
    ap.add_argument(
        "--base-url",
        default=BASE_URL,
        help="Base URL de la guía (debe terminar en /content/).",
    )
    ap.add_argument(
        "--seed",
        nargs="*",
        default=SEED_PAGES,
        help="Lista inicial de páginas .html (relativas a base-url).",
    )
    ap.add_argument(
        "--no-discover",
        action="store_true",
        help="No descubrir páginas adicionales por enlaces.",
    )
    args = ap.parse_args()

    BASE_URL = args.base_url

    docset = Path(args.docset).expanduser()
    if not docset.exists() or not docset.is_dir():
        print(f"ERROR: docset no encontrado: {docset}", file=sys.stderr)
        return 2

    dsidx = docset / DSIDX_REL
    documents_root = docset / DOCS_REL
    content_dir = documents_root / CONTENT_REL

    if not documents_root.exists():
        print(f"ERROR: no existe Documents: {documents_root}", file=sys.stderr)
        return 2
    if not dsidx.exists():
        print(f"ERROR: no existe docSet.dsidx: {dsidx}", file=sys.stderr)
        return 2

    # Paso 1: backup Documents
    backup_base = documents_root.parent / "Documents_backup"
    safe_backup_dir(documents_root, backup_base)

    # Paso 1: descarga
    seed_pages = list(args.seed)
    if args.no_discover:
        # Descarga solo seeds
        downloaded: set[str] = set()
        for p in seed_pages:
            downloaded.add(p)
            try:
                data = fetch_url(url_for_page(p))
                (content_dir / p).parent.mkdir(parents=True, exist_ok=True)
                (content_dir / p).write_bytes(data)
                print(f"DOWNLOAD OK  {p}")
            except Exception as e:
                print(f"DOWNLOAD FAIL {p} -> {type(e).__name__}: {e}", file=sys.stderr)
    else:
        download_pages(content_dir, seed_pages)

    # Paso 2: limpieza
    total, before_b, after_b = clean_html_files(content_dir)
    print("\n--- Estadísticas limpieza ---")
    print(f"HTMLs limpiados: {total}")
    print(f"Tamaño antes:  {human_bytes(before_b)}")
    print(f"Tamaño después:{human_bytes(after_b)}")

    # Paso 3: indexación
    index_dsidx(docset, documents_root, content_dir)

    print("\nIMPORTANTE: reinicia Dash para que cargue el nuevo índice (docSet.dsidx) y el contenido descargado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
