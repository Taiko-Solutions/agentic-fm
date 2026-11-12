"""OData resolution and transport for the AGFMScriptBridge.

Shared by the live-evaluation lint rules and the context refresh script.
Standard library only.
"""

import base64
import http.client
import json
import urllib.error
import urllib.request
from collections import namedtuple
from pathlib import Path

Target = namedtuple("Target", "odata data_source main")


class ODataConfigError(Exception):
    """Configuration problem; the message is Spanish, ready to show."""


class BridgeError(Exception):
    """Transport failure. status is the HTTP code, or None for network/timeout/unreadable body."""

    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status
        self.reason = reason


class ScriptMissing(BridgeError):
    """The Bridge answered 200 but the inner script does not exist in the file."""

    def __init__(self, script):
        super().__init__(None, f"Script not found: {script}")
        self.script = script


def _norm(name):
    n = str(name or "").strip()
    if n.lower().endswith(".fmp12"):
        n = n[: -len(".fmp12")]
    return n.lower()


def same_name(a, b):
    """True if two solution names match (ignoring .fmp12 and case)."""
    return _norm(a) == _norm(b)


def find_key(solutions, name):
    """Key of `solutions` matching `name` (ignoring .fmp12 and case), or None."""
    wanted = _norm(name)
    for key in solutions:
        if _norm(key) == wanted:
            return key
    return None


def load_solutions(project_root):
    """Return automation.json["solutions"], or {} if absent."""
    path = Path(project_root) / "agent" / "config" / "automation.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ODataConfigError(f"No se pudo leer automation.json: {exc}") from exc
    sols = data.get("solutions", {}) if isinstance(data, dict) else {}
    return sols if isinstance(sols, dict) else {}


def resolve(solutions, name):
    """Resolve the OData target for a solution (with or without .fmp12)."""
    key = find_key(solutions, name) if name else None
    if key is None:
        if len(solutions) == 1:
            key = next(iter(solutions))
        else:
            raise ODataConfigError(
                f"Solución '{name or ''}' no encontrada en automation.json "
                "y hay varias configuradas."
            )
    entry = solutions[key]
    odata = entry.get("odata") if isinstance(entry, dict) else None
    if not isinstance(odata, dict) or not odata:
        raise ODataConfigError(f"sin configuración OData para {key}")

    via = odata.get("via")
    if not via:
        return Target(odata, None, key)

    main_key = find_key(solutions, via)
    if main_key is None:
        raise ODataConfigError(f"'via' de {key} apunta a '{via}', que no existe en automation.json")
    main_entry = solutions[main_key]
    main_odata = main_entry.get("odata") if isinstance(main_entry, dict) else None
    if not isinstance(main_odata, dict):
        raise ODataConfigError(f"el archivo principal {main_key} no tiene configuración OData")
    if main_odata.get("via"):
        raise ODataConfigError(f"'via' encadenado: {main_key} también usa 'via'")
    if not main_odata.get("base_url"):
        raise ODataConfigError(f"el archivo principal {main_key} no tiene base_url")
    return Target(main_odata, odata.get("data_source"), main_key)


NOT_FOUND_PREFIX = "Script not found: "


def _envelope(body):
    """scriptResult -> resultParameter: the AGFMScriptBridge layer (parsed if JSON)."""
    result = body.get("scriptResult", body) if isinstance(body, dict) else body
    if isinstance(result, dict):
        rp = result.get("resultParameter", "")
        if isinstance(rp, str) and rp:
            try:
                result = json.loads(rp)
            except json.JSONDecodeError:
                pass
    return result


def _is_verdict(d):
    """A dict that already looks like AGFM Agent's answer, not a Bridge envelope."""
    return "error_code" in d or "expression" in d or "solution" in d


def _peel(result):
    """Peel the Bridge layer once ({script, result: "<json>"}); never the evaluated value."""
    if (isinstance(result, dict) and "script" in result
            and isinstance(result.get("result"), str) and not _is_verdict(result)):
        stripped = result["result"].strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                inner = json.loads(stripped)
            except json.JSONDecodeError:
                return result
            if isinstance(inner, dict):
                return inner
    return result


def unwrap(body):
    """Peel scriptResult -> resultParameter -> the Bridge's `result` (once)."""
    return _peel(_envelope(body))


def bridge_call(odata, script, parameter, timeout=30):
    """Call a FileMaker script through AGFMScriptBridge over OData."""
    base_url = odata.get("base_url", "")
    database = odata.get("database", "")
    username = odata.get("username", "")
    password = odata.get("password", "")
    bridge = odata.get("script_bridge", "AGFMScriptBridge")
    if not all([base_url, database, username, password]):
        raise ODataConfigError(
            "Faltan credenciales OData (base_url, database, username, password) en automation.json"
        )

    url = f"{base_url}/{urllib.request.quote(database, safe='')}/Script.{bridge}"
    inner = json.dumps({"script": script, "parameter": parameter})
    payload = json.dumps({"scriptParameterValue": inner})
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {credentials}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        exc.close()
        raise BridgeError(exc.code, f"HTTP {exc.code} del servidor OData") from exc
    except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
        raise BridgeError(None, f"No se pudo conectar con OData: {exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BridgeError(None, "Respuesta de OData ilegible (no es JSON)") from exc
    if not isinstance(body, dict):
        raise BridgeError(None, "Respuesta de OData ilegible (no es un objeto JSON)")
    env = _envelope(body)
    if (isinstance(env, dict) and env.get("success") is False
            and str(env.get("error", "")).startswith(NOT_FOUND_PREFIX)):
        raise ScriptMissing(str(env["error"])[len(NOT_FOUND_PREFIX):].strip())
    return _peel(env)
