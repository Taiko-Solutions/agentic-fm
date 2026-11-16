#!/usr/bin/env python3
"""Run a FileMaker script of any file of a solution over OData.

The call always enters through AGFMScriptBridge of the main file. For a secondary
file (an `odata` block with `via` + `data_source` in agent/config/automation.json)
the Bridge performs `<data_source>::<script>` in that file; this needs the add-on
1.5.0 in the main file, so its version is checked before anything is sent.

A script that shows dialogs does not work over OData. `success` only says the
script was launched: what fails inside it is the script's own business and comes
back in its result.

The developer must approve the run: the script asks for confirmation unless --yes
is passed (agents: get the developer's OK in conversation, then use --yes).

Usage:
  python3 agent/scripts/run_script.py --script "My Script" [--solution "SolutionData"]
      [--param '{"id": 9}'] [--yes] [--json] [--timeout 60] [--repo /path/to/clone]

Exit codes: 0 the script ran; 1 it did not run or the Bridge reported a failure;
2 configuration or precondition (unknown solution, main file's add-on too old).

Standard library only.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from agent.fmlint.odata import (  # noqa: E402
    BridgeError, ODataConfigError, ScriptMissing, bridge_call, find_key,
    load_solutions, resolve)

MIN_ADDON = (1, 5, 0)
VERSION_SCRIPT = "AGFM Version"
_SEMVER = re.compile(r'^"?(\d+)\.(\d+)\.(\d+)"?$')
_YES = ("s", "si", "sí", "y", "yes")


def parse_version(text):
    """'1.5.0' or '"1.5.0"' -> (1, 5, 0); anything else -> None."""
    match = _SEMVER.match(text.strip()) if isinstance(text, str) else None
    return tuple(int(part) for part in match.groups()) if match else None


def main_addon_version(odata, timeout):
    """Add-on version of the main file, or None if it has no AGFM Version script."""
    try:
        answer = bridge_call(odata, VERSION_SCRIPT, "", timeout=timeout, peel=False)
    except ScriptMissing:
        return None
    return parse_version(answer.get("result")) if isinstance(answer, dict) else None


def _fail(message, code):
    print(f"❌ {message}", file=sys.stderr)
    return code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--script", required=True, help="nombre del guion a ejecutar")
    parser.add_argument("--solution", default="", help="clave de automation.json (si hay varias)")
    parser.add_argument("--param", default="", help="parámetro del guion; viaja tal cual, como texto")
    parser.add_argument("--yes", action="store_true", help="no pedir confirmación (el desarrollador ya aprobó)")
    parser.add_argument("--json", action="store_true", help="imprimir la respuesta completa del Bridge")
    parser.add_argument("--timeout", type=int, default=60, help="segundos de espera por petición")
    parser.add_argument("--repo", default=str(REPO_ROOT),
                        help="raíz del clon cuyo agent/config/automation.json se usa")
    args = parser.parse_args(argv)

    try:
        solutions = load_solutions(args.repo)
        target = resolve(solutions, args.solution)
    except ODataConfigError as exc:
        return _fail(str(exc), 2)
    name = find_key(solutions, args.solution) or args.solution or target.main
    data_source = target.data_source

    print(f"Ejecutar «{args.script}» en {name}")
    if data_source:
        print(f"  a través de {target.main} (fuente de datos «{data_source}»)")
    if not args.yes:
        if input("¿Ejecutar este guion en FileMaker? [s/N] ").strip().lower() not in _YES:
            print("Cancelado.")
            return 1

    try:
        if data_source:
            # An older Bridge ignores data_source and would run a script of the same name in the main file.
            version = main_addon_version(target.odata, args.timeout)
            if version is None or version < MIN_ADDON:
                found = ".".join(map(str, version)) if version else "anterior a 1.4"
                return _fail(
                    f"El add-on de {target.main} es {found}; hace falta 1.5.0 para ejecutar guiones "
                    "en archivos secundarios. Actualiza el add-on del principal.", 2)
        answer = bridge_call(target.odata, args.script, args.param, timeout=args.timeout,
                             data_source=data_source, peel=False)
    except ScriptMissing as exc:
        return _fail(f"{name} no tiene el guion «{exc.script}»", 1)
    except ODataConfigError as exc:
        return _fail(str(exc), 2)
    except BridgeError as exc:
        return _fail(exc.reason, 1)

    if not isinstance(answer, dict):
        return _fail(f"Respuesta inesperada del Bridge: {answer!r}", 1)
    if data_source and answer.get("data_source") != data_source:
        return _fail(f"El Bridge no confirmó que el guion se ejecutara en «{data_source}»", 2)
    if not answer.get("success"):
        code = answer.get("error_code")
        detail = f" (código FileMaker {code})" if code not in (None, "") else ""
        return _fail(f"{answer.get('error') or 'el Bridge no ejecutó el guion'}{detail}", 1)

    if args.json:
        print(json.dumps(answer, ensure_ascii=False, indent=2))
    else:
        print(answer.get("result", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
