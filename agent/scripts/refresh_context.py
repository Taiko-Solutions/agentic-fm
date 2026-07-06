#!/usr/bin/env python3
"""Refresh agent/CONTEXT.json without leaving the agent session.

Chains the documented automation flow (agent/docs/AUTOMATION.md §"Switch
layout context and refresh CONTEXT.json") into one command:

  1. (optional) AGFMGoToLayout  { "layout": "<name>" }   — switch FM context
  2. Push Context               { "task", "repo_path", "companion_url" }
  3. Poll agent/CONTEXT.json until it is rewritten, then summarize it.

Dispatch routes (--via):
  odata      — AGFMScriptBridge on FileMaker Server (Tier 3, fully headless).
               Requires an `odata` block in automation.json for the solution.
  companion  — companion server /trigger (Tier 2, local FM Pro via
               AppleScript). Parameter passing to FM scripts over this route
               is best-effort: if the embedded Push Context prompts, the
               developer just confirms the dialog — still no manual
               navigation needed.
  auto       — odata when configured, else companion. (default)

Per AUTOMATION.md, triggering FM scripts requires developer approval: the
command prints what it is about to run and asks for confirmation unless
--yes is passed (agents: get the developer's OK in conversation, then use
--yes).

Usage:
  python3 agent/scripts/refresh_context.py --task "944.9 F1 audit" \
      --layout "Utility_Peticiones" [--solution "Borneo"] [--via auto] [--yes]

Standard library only.
"""

import argparse
import base64
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_PATH = REPO_ROOT / "agent" / "CONTEXT.json"
AUTOMATION_PATH = REPO_ROOT / "agent" / "config" / "automation.json"
DEFAULT_COMPANION = "http://127.0.0.1:8765"


def load_automation():
    if not AUTOMATION_PATH.exists():
        return {}
    try:
        return json.loads(AUTOMATION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"⚠️  automation.json ilegible: {exc}", file=sys.stderr)
        return {}


def resolve_solution(auto_cfg, requested):
    solutions = auto_cfg.get("solutions", {})
    if requested:
        if requested not in solutions:
            sys.exit(f"❌ Solución '{requested}' no está en automation.json "
                     f"(disponibles: {', '.join(solutions) or 'ninguna'})")
        return requested, solutions[requested]
    # Infer from CONTEXT.json, else single-entry automation.json
    if CONTEXT_PATH.exists():
        try:
            name = json.loads(CONTEXT_PATH.read_text(encoding="utf-8")).get("solution")
            if name and name in solutions:
                return name, solutions[name]
        except (json.JSONDecodeError, OSError):
            pass
    if len(solutions) == 1:
        name = next(iter(solutions))
        return name, solutions[name]
    return None, {}


def http_post_json(url, payload, headers=None, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# Dispatch routes
# ---------------------------------------------------------------------------

def via_odata(odata, script, parameter_obj):
    """Call a named FM script through AGFMScriptBridge (AUTOMATION.md §61)."""
    base = odata["base_url"].rstrip("/")
    db = urllib.parse.quote(odata["database"])
    bridge = odata.get("script_bridge", "AGFMScriptBridge")
    url = f"{base}/{db}/Script.{bridge}"
    auth = base64.b64encode(
        f"{odata['username']}:{odata['password']}".encode()).decode()
    inner = json.dumps({"script": script,
                        "parameter": json.dumps(parameter_obj, ensure_ascii=False)})
    resp = http_post_json(url, {"scriptParameterValue": inner},
                          headers={"Authorization": f"Basic {auth}"})
    code = (resp.get("scriptResult") or {}).get("code")
    if code not in (0, "0", None):
        raise RuntimeError(f"{script} devolvió code={code}: {resp}")
    return resp


def via_companion(companion_url, script, parameter_obj, target_file=""):
    """Trigger a named FM script in local FM Pro via the companion (/trigger).

    Parameter passing over AppleScript is best-effort (FM Pro 22 quirk); if
    the FM-side script prompts, the developer confirms the dialog.
    """
    payload = {"script": script}
    if parameter_obj:
        payload["parameter"] = json.dumps(parameter_obj, ensure_ascii=False)
    if target_file:
        payload["target_file"] = target_file
    resp = http_post_json(companion_url.rstrip("/") + "/trigger", payload)
    if not resp.get("success"):
        raise RuntimeError(f"/trigger {script} falló: {resp.get('error') or resp.get('stderr')}")
    return resp


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", required=True, help="descripción de la tarea para Push Context")
    parser.add_argument("--layout", default="", help="layout al que navegar antes (AGFMGoToLayout)")
    parser.add_argument("--solution", default="", help="clave de automation.json (si hay varias)")
    parser.add_argument("--via", choices=("auto", "odata", "companion"), default="auto")
    parser.add_argument("--timeout", type=int, default=45, help="segundos de espera del CONTEXT.json fresco")
    parser.add_argument("--yes", action="store_true", help="no pedir confirmación (el desarrollador ya aprobó)")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    args = parser.parse_args()

    auto_cfg = load_automation()
    sol_name, sol = resolve_solution(auto_cfg, args.solution)
    odata = sol.get("odata") or {}
    explode = sol.get("explode_xml") or {}

    route = args.via
    if route == "auto":
        route = "odata" if odata.get("base_url") else "companion"
    if route == "odata" and not odata.get("base_url"):
        sys.exit("❌ Vía odata solicitada pero la solución no tiene bloque odata en automation.json")

    repo_path = explode.get("repo_path") or str(REPO_ROOT)
    if route == "odata":
        companion_url_for_fm = explode.get("companion_url") or "http://host.docker.internal:8765"
    else:
        companion_url_for_fm = explode.get("companion_url") or DEFAULT_COMPANION
    companion_local = DEFAULT_COMPANION
    target_file = sol.get("target_file", "") or (f"{sol_name}.fmp12" if sol_name else "")

    plan = []
    if args.layout:
        plan.append(f'AGFMGoToLayout {{"layout": "{args.layout}"}}')
    plan.append(f'Push Context {{"task": "{args.task[:50]}…", "repo_path": …, "companion_url": …}}')
    print(f"Refresh de contexto — solución: {sol_name or '(sin resolver)'} · vía: {route}")
    for step in plan:
        print(f"  → {step}")
    if not args.yes:
        answer = input("¿Disparar estos scripts en FileMaker? [s/N] ").strip().lower()
        if answer not in ("s", "si", "sí", "y", "yes"):
            print("Cancelado.")
            return 1

    mtime_before = CONTEXT_PATH.stat().st_mtime if CONTEXT_PATH.exists() else 0

    try:
        if args.layout:
            if route == "odata":
                via_odata(odata, "AGFMGoToLayout", {"layout": args.layout})
            else:
                via_companion(companion_local, "AGFMGoToLayout",
                              {"layout": args.layout}, target_file)
            time.sleep(1.0)
        push_param = {"task": args.task, "repo_path": repo_path,
                      "companion_url": companion_url_for_fm}
        if route == "odata":
            via_odata(odata, "Push Context", push_param)
        else:
            via_companion(companion_local, "Push Context", push_param, target_file)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Disparo fallido vía {route}: {exc}", file=sys.stderr)
        print("Fallback manual: navega en FM al layout y corre 'Push Context'.",
              file=sys.stderr)
        return 1

    # Wait for the fresh CONTEXT.json
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if CONTEXT_PATH.exists() and CONTEXT_PATH.stat().st_mtime > mtime_before:
            break
        time.sleep(1.0)
    else:
        print(f"⚠️  CONTEXT.json no se refrescó en {args.timeout}s. Si FM mostró un "
              f"diálogo (vía companion), confírmalo y reintenta el poll.", file=sys.stderr)
        return 1

    try:
        ctx = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"❌ CONTEXT.json fresco pero ilegible: {exc}", file=sys.stderr)
        return 1

    summary = {
        "solution": ctx.get("solution"),
        "layout": (ctx.get("current_layout") or {}).get("name"),
        "task": ctx.get("task"),
        "generated_at": ctx.get("generated_at"),
        "route": route,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"✅ CONTEXT.json fresco — solución {summary['solution']} · "
              f"layout \"{summary['layout']}\" · task \"{(summary['task'] or '')[:70]}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
