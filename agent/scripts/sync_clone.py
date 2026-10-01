#!/usr/bin/env python3
"""Actualiza un clon agentic-fm de cliente desde origin/taiko (Taiko).

Modelo de ramas del clon: `taiko` = espejo de origin/taiko (sin commits propios),
`trabajo` = rama local del cliente (nunca se sube), `mejora/*` = mejoras para PR.

  python3 agent/scripts/sync_clone.py            # fetch · taiko ff · merge en trabajo · novedades
  python3 agent/scripts/sync_clone.py --migrar   # además: mueve commits locales de taiko a trabajo,
                                                 #   quita el remote upstream y reinstala el hook
  python3 agent/scripts/sync_clone.py --json     # salida máquina (para Agentic-FM-APP)

En el repo base (con remote upstream) no aplica. Solo librería estándar.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

CHANGELOG = "TAIKO-UPDATES.md"


def _git(repo, *args, check=True):
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def is_base_repo(repo) -> bool:
    """El repo base es el único con remote `upstream` (petrowsky)."""
    rc, _, _ = _git(repo, "remote", "get-url", "upstream", check=False)
    return rc == 0


def updates_between(repo, old_sha: str, new_sha: str) -> list:
    """Títulos `## …` añadidos a TAIKO-UPDATES.md entre dos commits (sin el `## `)."""
    if not old_sha or old_sha == new_sha:
        return []
    rc, out, _ = _git(repo, "diff", f"{old_sha}..{new_sha}", "--", CHANGELOG, check=False)
    if rc != 0:
        return []
    return [line[4:].strip() for line in out.splitlines() if line.startswith("+## ")]


def _branch_exists(repo, name) -> bool:
    rc, _, _ = _git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}", check=False)
    return rc == 0


def sync(repo, migrar: bool = False) -> dict:
    repo = Path(repo)
    res = {"mode": "clone", "taiko_before": None, "taiko_after": None, "updates": [],
           "merged": False, "conflicts": [], "migrated": False, "messages": []}
    # Con --migrar el desarrollador afirma que esto es un clon: un remote `upstream`
    # residual (anomalía) no lo convierte en repo base, se elimina más abajo.
    if not migrar and is_base_repo(repo):
        res["mode"] = "base"
        res["messages"].append("repo base (remote upstream): aquí se actualiza con git pull; sync no aplica")
        return res

    _, status, _ = _git(repo, "status", "--porcelain")
    if status:
        res["messages"].append("hay cambios sin commit: haz commit o stash antes de sincronizar")
        return res

    _git(repo, "fetch", "--quiet", "origin")
    _, current, _ = _git(repo, "branch", "--show-current")
    _, remote_taiko, _ = _git(repo, "rev-parse", "origin/taiko")
    res["taiko_before"] = _git(repo, "rev-parse", "taiko")[1] if _branch_exists(repo, "taiko") else None

    if migrar:
        if current == "taiko" and res["taiko_before"] != remote_taiko and not _branch_exists(repo, "trabajo"):
            # commits locales en taiko → trabajo (taiko se realinea más abajo)
            _git(repo, "branch", "trabajo", "taiko")
            res["messages"].append("commits locales de taiko movidos a trabajo")
        rc, _, _ = _git(repo, "remote", "get-url", "upstream", check=False)
        if rc == 0:
            _git(repo, "remote", "remove", "upstream")
            res["messages"].append("remote upstream eliminado (un solo remote en clones)")
        res["migrated"] = True

    # taiko = espejo exacto de origin/taiko
    _git(repo, "checkout", "--quiet", "-B", "taiko", "origin/taiko")
    res["taiko_after"] = remote_taiko
    res["updates"] = updates_between(repo, res["taiko_before"], remote_taiko)

    # trabajo: crear si no existe; merge de taiko
    if not _branch_exists(repo, "trabajo"):
        _git(repo, "branch", "trabajo", "taiko")
        res["messages"].append("rama trabajo creada desde taiko")
    _git(repo, "checkout", "--quiet", "trabajo")
    rc, _, _ = _git(repo, "merge", "--no-edit", "taiko", check=False)
    if rc == 0:
        res["merged"] = True
    else:
        _, conflicts, _ = _git(repo, "diff", "--name-only", "--diff-filter=U", check=False)
        res["conflicts"] = conflicts.splitlines()
        _git(repo, "merge", "--abort", check=False)
        res["messages"].append("conflicto al mezclar taiko en trabajo: resuélvelo a mano con git merge taiko")

    if migrar:
        hook = repo / "agent" / "scripts" / "install-hooks.sh"
        if hook.exists():
            subprocess.run(["bash", str(hook)], cwd=repo, capture_output=True)
            res["messages"].append("hook pre-push reinstalado")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--migrar", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        res = sync(args.repo, migrar=args.migrar)
    except RuntimeError as exc:
        res = {"mode": "error", "merged": False, "updates": [], "conflicts": [], "messages": [str(exc)]}
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for m in res["messages"]:
            print(f"· {m}")
        if res.get("merged"):
            print(f"✅ trabajo al día con origin/taiko ({res['taiko_after'][:7]})")
        if res["updates"]:
            print("Novedades (TAIKO-UPDATES.md):")
            for u in res["updates"]:
                print(f"  · {u}")
        if res["conflicts"]:
            print("❌ Conflictos:", ", ".join(res["conflicts"]))
    return 0 if res.get("merged") or res.get("mode") == "base" else 1


if __name__ == "__main__":
    sys.exit(main())
