#!/usr/bin/env python3
"""Unified session-start check for agentic-fm.

Runs every once-per-session startup check in a single command and prints a
compact, one-line-per-check summary the agent (or a human) can act on:

  1. git       — pending commits on the relevant upstream branch
                 (origin/taiko for Taiko-based repos, origin/main otherwise)
  2. env       — platform + AppleScript availability (sandbox detection)
  3. embedded  — freshness of the agentic-fm code embedded in the solution
                 (delegates to check_embedded_agfm.py; SKIP if no explode)
  4. companion — companion server health on :8765 + AgenticFM plug-in block
                 (usable / installed / absent)
  5. proofkit  — ProofKit bridge on :1365, connected FileMaker files
  6. project   — PROJECT.md presence (local-only context)
  7. context   — CONTEXT.json presence, age, and task description

Replaces six separate round-trips at session start with one:

  python3 agent/scripts/session_start.py           # human summary
  python3 agent/scripts/session_start.py --json    # machine-readable

Every check is isolated and failure-tolerant: network being down or a
service being absent yields WARN/SKIP, never a crash. Exit code is 0
unless --strict is passed (then 1 if any check FAILs).

Standard library only.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

OK, WARN, FAIL, SKIP = "OK", "WARN", "FAIL", "SKIP"


def _run(cmd, timeout=15):
    """Run a command from the repo root; returns (rc, stdout) — never raises."""
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True,
                              text=True, timeout=timeout)
        return proc.returncode, (proc.stdout or "").strip()
    except Exception as exc:  # noqa: BLE001 — any failure is a soft-skip
        return -1, str(exc)


def _http_json(url, timeout=4):
    """GET a URL and parse JSON; returns dict or None — never raises."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Checks — each returns (status, message, data)
# ---------------------------------------------------------------------------

def check_git():
    rc, _ = _run(["git", "rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        return SKIP, "no es un repo git", {}
    _run(["git", "fetch", "--all", "--quiet"], timeout=30)

    # Prefer the Taiko propagation model when an origin/taiko branch exists;
    # fall back to the upstream origin/main check otherwise.
    data = {}
    for ref, label in (("origin/taiko", "taiko"), ("origin/main", "main")):
        rc, out = _run(["git", "rev-list", f"HEAD..{ref}", "--count"])
        if rc == 0 and out.isdigit():
            data[label] = int(out)

    if "taiko" in data:
        behind, branch = data["taiko"], "origin/taiko"
    elif "main" in data:
        behind, branch = data["main"], "origin/main"
    else:
        return SKIP, "sin remoto comparable (offline o repo aislado)", data

    if behind > 0:
        return WARN, f"{behind} commit(s) por detrás de {branch} — considera actualizar antes de seguir", data
    return OK, f"al día con {branch}", data


def check_env():
    system = platform.system()
    osascript = shutil.which("osascript") is not None
    data = {"system": system, "osascript": osascript}
    if system != "Darwin" or not osascript:
        return WARN, (f"{system}, osascript={'sí' if osascript else 'no'} — entorno "
                      f"sandbox/no-macOS: lee agent/docs/SANDBOXED_ENVIRONMENT.md"), data
    return OK, "macOS nativo con osascript", data


def check_embedded():
    if not (REPO_ROOT / "agent" / "xml_parsed").is_dir():
        return SKIP, "sin solución explotada", {}
    script = REPO_ROOT / "agent" / "scripts" / "check_embedded_agfm.py"
    if not script.exists():
        return SKIP, "check_embedded_agfm.py no disponible", {}
    rc, out = _run([sys.executable, str(script)], timeout=60)
    stale = [l for l in out.splitlines() if "STALE" in l or "MISSING" in l]
    if rc != 0 or stale:
        head = "; ".join(stale[:3]) or out.splitlines()[-1] if out else "fallo"
        return WARN, f"código agentic-fm embebido desactualizado: {head} — redeploy desde filemaker/", {"stale": stale}
    if "nothing to check" in out.lower():
        return SKIP, "nada que comprobar", {}
    return OK, "código embebido al día", {}


def check_companion():
    health = None
    for base in ("http://127.0.0.1:8765", "http://local.hub:8765"):
        health = _http_json(base + "/health")
        if health:
            break
    if not health:
        return WARN, "companion no responde en :8765 — automatización Tier 2/3 no disponible (paste manual)", {}
    plugin = health.get("plugin") or {}
    data = {"version": health.get("version"), "plugin": plugin}
    if plugin.get("usable"):
        return OK, (f"companion v{health.get('version', '?')} · plug-in AgenticFM USABLE → "
                    f"modo plugin-preferred (lee agent/docs/PLUGIN_INTEGRATION.md)"), data
    if plugin.get("installed"):
        return OK, (f"companion v{health.get('version', '?')} · plug-in instalado pero no usable "
                    f"(licencia/servidor) → ruta OSS"), data
    return OK, f"companion v{health.get('version', '?')} · sin plug-in → ruta OSS", data


def check_proofkit():
    payload = _http_json("http://127.0.0.1:1365/connectedFiles")
    if payload is None:
        return SKIP, "bridge ProofKit no responde en :1365 — flujo estático (explode/CONTEXT.json)", {}
    files = payload if isinstance(payload, list) else payload.get("files", [])
    if files:
        return OK, f"ProofKit conectado: {', '.join(str(f) for f in files[:4])}", {"files": files}
    return WARN, "bridge ProofKit activo pero SIN archivo conectado — corre 'Connect to MCP' en FileMaker", {"files": []}


def check_project_md():
    if (REPO_ROOT / "PROJECT.md").exists():
        return OK, "PROJECT.md presente — léelo (contexto local del meta-proyecto)", {"exists": True}
    return SKIP, "sin PROJECT.md (normal en clones de colaboradores)", {"exists": False}


def check_context():
    ctx_path = REPO_ROOT / "agent" / "CONTEXT.json"
    if not ctx_path.exists():
        return WARN, "CONTEXT.json ausente — pide Push Context antes de generar código", {"exists": False}
    try:
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return FAIL, f"CONTEXT.json ilegible: {exc}", {"exists": True}
    age_h = (time.time() - ctx_path.stat().st_mtime) / 3600
    task = (data.get("task") or "")[:80]
    layout = (data.get("current_layout") or {}).get("name", "?")
    info = {"exists": True, "age_hours": round(age_h, 1), "task": task, "layout": layout}
    msg = f'layout "{layout}" · task "{task}" · {age_h:.1f} h'
    if age_h > 24:
        return WARN, msg + " — posiblemente rancio; valora un Push Context fresco", info
    return OK, msg, info


CHECKS = [
    ("git", check_git),
    ("env", check_env),
    ("embedded", check_embedded),
    ("companion", check_companion),
    ("proofkit", check_proofkit),
    ("project", check_project_md),
    ("context", check_context),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 si algún check FAIL")
    args = parser.parse_args()

    results = {}
    for name, fn in CHECKS:
        try:
            status, msg, data = fn()
        except Exception as exc:  # noqa: BLE001 — un check jamás tumba el resto
            status, msg, data = FAIL, f"check reventó: {exc}", {}
        results[name] = {"status": status, "message": msg, "data": data}

    counts = {s: sum(1 for r in results.values() if r["status"] == s)
              for s in (OK, WARN, FAIL, SKIP)}

    if args.json:
        print(json.dumps({"timestamp": datetime.now().isoformat(timespec="seconds"),
                          "results": results, "counts": counts},
                         ensure_ascii=False, indent=2))
    else:
        print(f"agentic-fm session start — {datetime.now():%Y-%m-%d %H:%M}")
        for name, r in results.items():
            print(f"  [{r['status']:>4}] {name:<10} {r['message']}")
        verdict = "listo"
        if counts[FAIL]:
            verdict = "con FALLOS"
        elif counts[WARN]:
            verdict = f"listo ({counts[WARN]} aviso/s)"
        print(f"Veredicto: {verdict}")

    return 1 if (args.strict and counts[FAIL]) else 0


if __name__ == "__main__":
    sys.exit(main())
