#!/usr/bin/env python3
"""Construir manualmente un docset de Dash para la FileMaker Data API Guide.

Problema:
- MadCap Flare puede cargar navegación/TOC por JavaScript y el Docset Generator no siempre descarga todas las subpáginas.

Este script hace TODO en secuencia:
1) Backup Documents
2) Descarga seed + discovery de enlaces internos
3) Limpieza HTML (solo #mc-main-content, CSS inline, sin <script>)
4) Indexación tipada (DROP+CREATE searchIndex)
5) Reparar Info.plist si está malformado
6) Instalación en Dash/DocSets evitando duplicados (renombra primero el generator)

Uso:
  python3 build_data_api_docset_manual.py

Requisitos:
  python3 -m pip install beautifulsoup4
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import subprocess
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


# --- Config ---
DOCSET_GEN = Path(
    "/Users/marcoperez/Library/Application Support/Dash/Docset Generator/FileMaker Data API Guide/"
    "FileMaker Data API Guide.docset"
)
DOCSET_DEST = Path(
    "/Users/marcoperez/Library/Application Support/Dash/DocSets/FileMaker Data API Guide.docset"
)

BASE_URL = "https://help.claris.com/en/data-api-guide/content/"

SEED_PAGES = [
    "index.html",
    "how-data-api-call-is-processed.html",
    "web-integration-alternatives.html",
    "prepare-databases-for-access.html",
    "design-app.html",
    "write-data-api-calls.html",
    "connect-disconnect-database.html",
    "log-in-database-session.html",
    "log-in-external-data-source.html",
    "log-in-database-session-oauth.html",
    "log-in-database-session-claris-id.html",
    "log-out-database-session.html",
    "validate-database-session.html",
    "get-metadata.html",
    "work-with-records.html",
    "create-record.html",
    "edit-record.html",
    "duplicate-record.html",
    "delete-record.html",
    "get-single-record.html",
    "get-range-of-records.html",
    "upload-container-data.html",
    "perform-find-request.html",
    "set-global-field-values.html",
    "run-filemaker-scripts.html",
    "run-a-script.html",
    "run-script-with-another-request.html",
    "error-responses.html",
    "host-data-api-app.html",
    "test-data-api-app.html",
    "monitor-data-api-app.html",
]

DSIDX_REL = Path("Contents/Resources/docSet.dsidx")
DOCS_REL = Path("Contents/Resources/Documents")
CONTENT_REL = Path("help.claris.com/en/data-api-guide/content")

# Tipado/Detección
HTTP_METHOD_RE = re.compile(r"\b(GET|POST|PATCH|DELETE|PUT)\b")
DATA_API_ROUTE_RE = re.compile(r"/fmi/data/v[^\s)\]>'\"]+", re.IGNORECASE)

TITLE_SUFFIX_RE = re.compile(
    r"\s*\|\s*Claris\s+FileMaker\s+Data\s+API\s+Guide\s*$",
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


def strip_accidental_content_prefix(p: str) -> str:
    # Evita el bug /content/content/ cuando href trae prefijo content/
    while p.startswith("content/"):
        p = p[len("content/") :]
    return p


def normalize_discovered_href(href: str) -> str | None:
    if not href:
        return None
    href = href.strip()

    # quitar fragment/query
    href = href.split("#", 1)[0].split("?", 1)[0]

    if not href.endswith(".html"):
        return None

    # Absoluta
    if href.startswith("http://") or href.startswith("https://"):
        u = urllib.parse.urlparse(href)
        if u.netloc != "help.claris.com":
            return None
        if not u.path.startswith("/en/data-api-guide/content/"):
            return None
        rel = u.path.split("/en/data-api-guide/content/", 1)[1]
        return strip_accidental_content_prefix(rel)

    # Root-relative
    if href.startswith("/"):
        if not href.startswith("/en/data-api-guide/content/"):
            return None
        rel = href.split("/en/data-api-guide/content/", 1)[1]
        return strip_accidental_content_prefix(rel)

    # Relative
    href = href.lstrip("./")
    if ".." in href:
        return None

    return strip_accidental_content_prefix(href)


def url_for_page(page: str) -> str:
    return urllib.parse.urljoin(BASE_URL, page)


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


def download_seed_and_discover(content_dir: Path) -> set[str]:
    content_dir.mkdir(parents=True, exist_ok=True)

    discovered: set[str] = set()
    q: deque[str] = deque()

    for p in SEED_PAGES:
        p = p.strip()
        if not p:
            continue
        p = strip_accidental_content_prefix(p)
        discovered.add(p)
        q.append(p)

    ok = 0
    fail = 0

    while q:
        page = q.popleft()
        url = url_for_page(page)
        dst = content_dir / page

        # Descargar siempre seeds (y discovered) para asegurar contenido completo
        try:
            data = fetch_url(url)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            ok += 1
            print(f"DOWNLOAD OK  {page}")

            # descubrir enlaces internos
            try:
                soup = BeautifulSoup(data, "html.parser")
                for a in soup.find_all("a"):
                    new = normalize_discovered_href(a.get("href") or "")
                    if new and new not in discovered:
                        discovered.add(new)
                        q.append(new)
            except Exception:
                pass

            time.sleep(0.12)

        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            fail += 1
            print(f"DOWNLOAD FAIL {page} -> {type(e).__name__}: {e}", file=sys.stderr)
        except Exception as e:
            fail += 1
            print(f"DOWNLOAD FAIL {page} -> {type(e).__name__}: {e}", file=sys.stderr)

    print(f"\nDescarga completada: OK={ok}, FAIL={fail}, TOTAL={len(discovered)}")
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


def clean_html_recursive(content_dir: Path) -> tuple[int, int, int]:
    html_files: list[Path] = []
    for p in sorted(content_dir.rglob("*.html")):
        rel = p.relative_to(content_dir).as_posix()
        # ignorar subárbol accidental content/...
        if rel.startswith("content/"):
            continue
        html_files.append(p)

    total = len(html_files)
    before = 0
    after = 0

    for i, p in enumerate(html_files, start=1):
        try:
            b = p.stat().st_size
            html = p.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            for s in list(soup.find_all("script")):
                try:
                    s.decompose()
                except Exception:
                    pass

            isolate_body_to_main(soup)
            inject_css(soup)

            p.write_text(str(soup), encoding="utf-8")
            a = p.stat().st_size

            before += b
            after += a

            if i == 1 or i % 10 == 0 or i == total:
                print(f"[{i}/{total}] CLEAN OK  {p.name}")
        except Exception as e:
            try:
                before += p.stat().st_size
                after += p.stat().st_size
            except Exception:
                pass
            print(f"[{i}/{total}] CLEAN FAIL {p.name} -> {type(e).__name__}: {e}", file=sys.stderr)

    return total, before, after


def ensure_searchindex_schema(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);")
    conn.execute("CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);")


def classify_data_api_page(title: str, text: str, rel_path: str, link_count: int) -> str:
    filename = Path(rel_path).name.lower()
    stem = Path(rel_path).stem.lower()
    title_l = title.lower()
    text_l = text.lower()

    # Error (más estricto: no marcar como Error solo por mencionar "error" en ejemplos)
    if stem in {"error-responses", "error-responses-details"} or "error" in filename:
        return "Error"
    if title_l.startswith("error") or title_l == "error responses":
        return "Error"

    # Endpoint (prioridad alta): páginas de endpoint conocidas por nombre de fichero
    endpoint_stems = {
        "connect-disconnect-database",
        "log-in-database-session",
        "log-in-external-data-source",
        "log-in-database-session-oauth",
        "log-in-database-session-claris-id",
        "log-out-database-session",
        "validate-database-session",
        "get-metadata",
        "create-record",
        "edit-record",
        "duplicate-record",
        "delete-record",
        "get-single-record",
        "get-range-of-records",
        "upload-container-data",
        "perform-find-request",
        "set-global-field-values",
        "run-a-script",
        "run-script-with-another-request",
    }
    if stem in endpoint_stems:
        return "Endpoint"

    # Endpoint por heurística (ruta + método)
    has_route = "/fmi/data/" in text_l or bool(DATA_API_ROUTE_RE.search(text))
    has_method = bool(HTTP_METHOD_RE.search(text))
    if has_route and has_method:
        return "Endpoint"

    # Category
    if filename in {"index.html", "overview.html", "toc.html"}:
        return "Category"
    if title in {
        "Connect to or disconnect from a database",
        "Work with records",
        "Run FileMaker scripts",
        "Write FileMaker Data API calls",
    }:
        return "Category"
    if link_count >= 25 and len(text) < 3500:
        return "Category"

    return "Guide"


def rebuild_searchindex(docset: Path, documents_root: Path, content_dir: Path) -> None:
    dsidx = docset / DSIDX_REL
    backup = safe_backup_file(dsidx)
    print(f"Backup dsidx: {backup}")

    conn = sqlite3.connect(str(dsidx))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        conn.execute("DROP TABLE IF EXISTS searchIndex;")
        conn.execute("DROP INDEX IF EXISTS anchor;")
        ensure_searchindex_schema(conn)
        conn.commit()

        html_files: list[Path] = []
        for p in sorted(content_dir.rglob("*.html")):
            rel = p.relative_to(content_dir).as_posix()
            if rel.startswith("content/"):
                continue
            html_files.append(p)

        insert_sql = "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?, ?, ?);"
        before_changes = conn.total_changes

        counts: Counter[str] = Counter()
        examples: dict[str, list[tuple[str, str]]] = defaultdict(list)

        total = len(html_files)
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

                kind = classify_data_api_page(title, text, rel_path, link_count)
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


def write_fixed_info_plist(info_plist: Path) -> None:
    info_plist.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
	<key>CFBundleIdentifier</key>
	<string>docgenfmda</string>
	<key>CFBundleName</key>
	<string>FileMaker Data API Guide</string>
	<key>DashDocSetDefaultFTSEnabled</key>
	<true/>
	<key>DashDocSetFallbackURL</key>
	<string>https://help.claris.com/en/data-api-guide/content/index.html</string>
	<key>DashDocSetFamily</key>
	<string>dashtoc</string>
	<key>DashDocSetKeyword</key>
	<string>fmda</string>
	<key>dashIndexFilePath</key>
	<string>help.claris.com/en/data-api-guide/content/index.html</string>
	<key>DashWebSearchKeyword</key>
	<string>FileMaker Data API Guide</string>
	<key>DocSetPlatformFamily</key>
	<string>docgenfmda</string>
	<key>isDashDocset</key>
	<true/>
	<key>isJavaScriptEnabled</key>
	<true/>
</dict>
</plist>
""",
        encoding="utf-8",
    )


def repair_info_plist(docset: Path) -> None:
    plist = docset / "Contents/Info.plist"
    if not plist.exists():
        plist.parent.mkdir(parents=True, exist_ok=True)
        write_fixed_info_plist(plist)
        return

    # Validar con plutil; si falla, reescribir
    try:
        r = subprocess.run(["plutil", "-lint", str(plist)], capture_output=True, text=True)
        if r.returncode == 0:
            return
    except Exception:
        pass

    write_fixed_info_plist(plist)


def install_to_docsets_avoiding_duplicates(docset_gen: Path, docset_dest: Path) -> Path:
    ts = now_stamp()

    # 1) Si ya existe destino, hacer backup
    if docset_dest.exists():
        bak = Path(str(docset_dest) + f".bak_{ts}")
        docset_dest.rename(bak)

    # 2) Renombrar el generator .docset para evitar duplicado
    gen_parent = docset_gen.parent
    gen_src = docset_gen
    gen_renamed = gen_parent / f"{docset_gen.name}_src_{ts}"
    gen_src.rename(gen_renamed)

    # 3) Copiar a DocSets
    subprocess.check_call(["ditto", str(gen_renamed), str(docset_dest)])

    # 4) Asegurar Info.plist válido también en el instalado
    repair_info_plist(docset_dest)

    return gen_renamed


def restart_dash() -> None:
    # reiniciar Dash para recargar docsets
    subprocess.run(["osascript", "-e", 'tell application "Dash" to quit'], check=False)
    time.sleep(2)
    subprocess.run(["open", "-a", "Dash"], check=False)
    time.sleep(2)


def main() -> int:
    if not DOCSET_GEN.exists():
        print(f"ERROR: No existe el docset en Docset Generator: {DOCSET_GEN}", file=sys.stderr)
        return 2

    documents_root = DOCSET_GEN / DOCS_REL
    content_dir = documents_root / CONTENT_REL
    dsidx = DOCSET_GEN / DSIDX_REL

    if not documents_root.exists():
        print(f"ERROR: No existe Documents: {documents_root}", file=sys.stderr)
        return 2
    if not dsidx.exists():
        print(f"ERROR: No existe docSet.dsidx: {dsidx}", file=sys.stderr)
        return 2

    # Paso 4 (parcial): reparar Info.plist del generator antes de instalar
    repair_info_plist(DOCSET_GEN)

    # Paso 1: backup Documents
    backup_base = documents_root.parent / "Documents_backup"
    safe_backup_dir(documents_root, backup_base)

    # Paso 1: descarga
    download_seed_and_discover(content_dir)

    # Paso 2: limpieza
    total, before_b, after_b = clean_html_recursive(content_dir)
    print("\n--- Estadísticas limpieza ---")
    print(f"HTMLs limpiados: {total}")
    print(f"Tamaño antes:  {human_bytes(before_b)}")
    print(f"Tamaño después:{human_bytes(after_b)}")

    # Paso 3: indexación
    rebuild_searchindex(DOCSET_GEN, documents_root, content_dir)

    # Paso 5: instalación evitando duplicados
    renamed_copy = install_to_docsets_avoiding_duplicates(DOCSET_GEN, DOCSET_DEST)
    print(f"\nInstalado en DocSets: {DOCSET_DEST}")
    print(f"Copia del generator renombrada (para evitar duplicados): {renamed_copy}")

    # Reiniciar Dash
    restart_dash()

    print("\nIMPORTANTE: Dash ya se ha reiniciado. Si no ves el docset, espera 10-20s y vuelve a abrir Dash.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
