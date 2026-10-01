#!/usr/bin/env python3
"""Reglas de rutas de agentic-fm (Taiko) — una sola implementación.

La usan el hook pre-push, agentic-fm-safe-push y la GitHub Action para decidir
si un conjunto de ficheros puede subir en una rama dada:

  1. [forbidden] menos [whitelist]  → bloqueo en cualquier rama y repo
  2. En un CLON (sin remote upstream): push a `taiko` o `trabajo` → bloqueo
  3. En un CLON, cualquier otra rama (mejora/*, claude/*, …): todo fichero
     debe casar con [allow] (capa herramientas)
  4. En un CLON: tocar [changelog-trigger] sin TAIKO-UPDATES.md → aviso

El repo base (el único con remote `upstream`) solo pasa la capa 1.

Uso:
  python3 agent/scripts/check_pushed_paths.py --branch mejora/x --revs "origin/taiko..HEAD"
  python3 agent/scripts/check_pushed_paths.py --branch mejora/x --revs "HEAD --not --remotes"   # rama nueva
  git diff --name-only … | python3 agent/scripts/check_pushed_paths.py --branch mejora/x          # lista por stdin

Con --revs los ficheros se calculan POR COMMIT (y en los merges contra cada padre, -m),
no como diff de árboles: un fichero añadido y borrado dentro del rango sigue en el
historial y se detecta. Los borrados puros no cuentan (no filtran datos).

Exit: 0 ok · 2 ficheros prohibidos · 3 fuera de la allowlist o rama bloqueada.
Solo librería estándar.
"""
import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_RULES = Path(__file__).resolve().parent / "hooks" / "paths.conf"
SECTIONS = ("forbidden", "whitelist", "allow", "changelog_trigger")
CHANGELOG = "TAIKO-UPDATES.md"
LOCKED_BRANCHES = ("taiko", "trabajo")


@dataclass
class Result:
    blocked: list = field(default_factory=list)   # (fichero, motivo)
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blocked


def load_rules(path) -> dict:
    """Lee paths.conf → {sección: [re.Pattern, ...]}. Ignora vacías y comentarios."""
    rules = {s: [] for s in SECTIONS}
    section = None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].replace("-", "_")
            if section not in rules:
                raise ValueError(f"sección desconocida en {path}: [{line[1:-1]}]")
            continue
        if section is None:
            raise ValueError(f"regla fuera de sección en {path}: {line}")
        rules[section].append(re.compile(line))
    return rules


def changed_files(repo, revs: str) -> list:
    """Ficheros añadidos/modificados en los commits de `revs` (sintaxis de git rev-list)."""
    cmd = ["git", "-C", str(repo), "log", "-m", "--pretty=format:", "--name-only",
           "--diff-filter=d", *revs.split()]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git log {revs}: {proc.stderr.strip()}")
    return sorted({line.strip() for line in proc.stdout.splitlines() if line.strip()})


def _matches(patterns, path: str) -> bool:
    return any(p.search(path) for p in patterns)


def classify(files, branch: str, is_base: bool, rules: dict) -> Result:
    res = Result()
    files = [f.strip() for f in files if f and f.strip()]

    # 1. Prohibidos (todas las ramas, todos los repos)
    for f in files:
        if _matches(rules["forbidden"], f) and not _matches(rules["whitelist"], f):
            res.blocked.append((f, "prohibido: datos de cliente/credenciales (paths.conf [forbidden])"))

    if is_base:
        return res

    # 2. Ramas bloqueadas en clones
    if branch in LOCKED_BRANCHES:
        res.blocked.append((f"(rama {branch})",
                            f"rama {branch} bloqueada desde un clon: sube la mejora en una rama "
                            f"mejora/<tema> y abre una PR a taiko"))
        return res

    # 3. Allowlist en cualquier otra rama de un clon (sin repetir los ya prohibidos)
    already = {f for f, _ in res.blocked}
    for f in files:
        if f not in already and not _matches(rules["allow"], f):
            res.blocked.append((f, "fuera de la capa herramientas (paths.conf [allow])"))

    # 4. Aviso de changelog
    touches_rules = any(_matches(rules["changelog_trigger"], f) for f in files)
    if touches_rules and CHANGELOG not in files:
        res.warnings.append(f"la rama toca reglas/herramientas pero no añade entrada en {CHANGELOG}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--branch", required=True, help="rama destino (sin refs/heads/)")
    ap.add_argument("--base-repo", action="store_true", help="repo base (tiene remote upstream)")
    ap.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--revs", help="rango de commits (git rev-list) en vez de la lista por stdin")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    args = ap.parse_args()
    if args.revs:
        try:
            files = changed_files(args.repo, args.revs)
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return 3
    else:
        files = [line.rstrip("\n") for line in sys.stdin]
    res = classify(files, args.branch, args.base_repo, load_rules(args.rules))
    for w in res.warnings:
        print(f"⚠️  {w}")
    if res.ok:
        return 0
    forbidden = any("prohibido" in why for _, why in res.blocked)
    print("❌ PUSH BLOQUEADO — reglas de rutas agentic-fm (agent/scripts/hooks/paths.conf)")
    for f, why in res.blocked:
        print(f"   {f}\n      → {why}")
    return 2 if forbidden else 3


if __name__ == "__main__":
    sys.exit(main())
