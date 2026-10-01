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
from datetime import datetime
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
           "merged": False, "conflicts": [], "migrated": False, "hook_changed": False,
           "messages": []}
    # Con --migrar el desarrollador afirma que esto es un clon: un remote `upstream`
    # residual (anomalía) no lo convierte en repo base, se elimina más abajo.
    if not migrar and is_base_repo(repo):
        res["mode"] = "base"
        res["messages"].append("repo base (remote upstream): aquí se actualiza con git pull; sync no aplica")
        return res

    _, status, _ = _git(repo, "status", "--porcelain", "--untracked-files=no")
    if status:
        res["messages"].append("hay cambios sin commit: haz commit o stash antes de sincronizar")
        return res

    # Punta remota ANTES del fetch: permite distinguir commits propios de una reescritura del remoto
    rc, old_remote, _ = _git(repo, "rev-parse", "--verify", "--quiet", "origin/taiko", check=False)
    old_remote = old_remote if rc == 0 else None
    _git(repo, "fetch", "--quiet", "origin")
    _, current, _ = _git(repo, "branch", "--show-current")
    _, remote_taiko, _ = _git(repo, "rev-parse", "origin/taiko")
    res["taiko_before"] = _git(repo, "rev-parse", "taiko")[1] if _branch_exists(repo, "taiko") else None

    # ¿origin/taiko fue reescrita (force-push)? Entonces lo que había no es "trabajo local"
    rewritten = False
    if old_remote and old_remote != remote_taiko:
        rc, _, _ = _git(repo, "merge-base", "--is-ancestor", old_remote, remote_taiko, check=False)
        rewritten = rc != 0
    base_for_local = old_remote if old_remote else remote_taiko

    # Commits propios en taiko (más allá de la punta remota que conocíamos): nunca se destruyen en silencio
    local_on_taiko = []
    if res["taiko_before"]:
        _, out, _ = _git(repo, "rev-list", "--no-merges", f"{base_for_local}..taiko", check=False)
        local_on_taiko = out.splitlines()
    if not migrar and (local_on_taiko or rewritten):
        why = "origin/taiko fue reescrita" if rewritten else f"taiko tiene {len(local_on_taiko)} commit(s) locales"
        res["messages"].append(f"{why}: ejecuta agentic-fm-sync --migrar (no se ha tocado nada)")
        return res

    to_replay = []   # commits propios a reaplicar sobre la taiko nueva (solo si hubo reescritura)
    if migrar:
        if rewritten:
            res["messages"].append(f"origin/taiko fue reescrita ({old_remote[:7]} → {remote_taiko[:7]}): "
                                   f"taiko y trabajo se realinean a la historia nueva")
            if res["taiko_before"]:
                keep = "backup/taiko-pre-reescritura-" + datetime.now().strftime("%Y-%m-%d")
                _git(repo, "branch", "-f", keep, "taiko")
                res["messages"].append(f"historia antigua de taiko guardada en {keep}")
            if _branch_exists(repo, "trabajo"):
                _, out, _ = _git(repo, "rev-list", "--no-merges", "--reverse", f"{old_remote}..trabajo", check=False)
                to_replay = out.splitlines()
                backup = "backup/trabajo-pre-reescritura-" + datetime.now().strftime("%Y-%m-%d")
                _git(repo, "branch", "-f", backup, "trabajo")
                _git(repo, "branch", "-D", "trabajo")
                res["messages"].append(f"trabajo recreada (copia previa en {backup})")
            else:
                _, out, _ = _git(repo, "rev-list", "--no-merges", "--reverse", f"{old_remote}..taiko", check=False)
                to_replay = out.splitlines()
        elif local_on_taiko:
            if not _branch_exists(repo, "trabajo"):
                _git(repo, "branch", "trabajo", "taiko")
                res["messages"].append("commits locales de taiko movidos a trabajo")
            else:
                backup = "backup/taiko-local-" + datetime.now().strftime("%Y-%m-%d")
                _git(repo, "branch", "-f", backup, "taiko")
                res["messages"].append(f"taiko tenía commits locales y trabajo ya existía: guardados en {backup} "
                                       f"y mezclados en trabajo")
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
    if to_replay:
        # Reaplicar los commits propios (sin merges) sobre la historia nueva
        for sha in to_replay:
            rc, _, err = _git(repo, "cherry-pick", "--allow-empty", "--keep-redundant-commits", sha, check=False)
            if rc != 0:
                _git(repo, "cherry-pick", "--abort", check=False)
                res["conflicts"] = [f"cherry-pick {sha[:7]}"]
                res["messages"].append(f"conflicto al reaplicar {sha[:7]} sobre la taiko nueva: hazlo a mano "
                                       f"(git cherry-pick {sha[:7]}) — el resto queda en la rama de copia")
                return res
        res["messages"].append(f"{len(to_replay)} commit(s) propios reaplicados sobre la historia nueva")
    if migrar and not rewritten and local_on_taiko and _branch_exists(repo, "trabajo"):
        # trabajo existía: traer primero los commits que estaban en taiko (backup/*)
        rc, _, _ = _git(repo, "merge", "--no-edit", res["taiko_before"], check=False)
        if rc != 0:
            _git(repo, "merge", "--abort", check=False)
            res["messages"].append("conflicto al traer los commits locales de taiko a trabajo: resuélvelo a mano")
            return res
    rc, _, _ = _git(repo, "merge", "--no-edit", "taiko", check=False)
    if rc == 0:
        res["merged"] = True
    else:
        _, conflicts, _ = _git(repo, "diff", "--name-only", "--diff-filter=U", check=False)
        res["conflicts"] = conflicts.splitlines()
        _git(repo, "merge", "--abort", check=False)
        res["messages"].append("conflicto al mezclar taiko en trabajo: resuélvelo a mano con git merge taiko")

    # Hook: reinstalar si cambió (o siempre con --migrar); excluir specs de cliente del índice
    if res["taiko_before"] and res["taiko_before"] != remote_taiko:
        _, changed, _ = _git(repo, "diff", "--name-only", f"{res['taiko_before']}..{remote_taiko}",
                             "--", "agent/scripts/hooks/", "agent/scripts/check_pushed_paths.py",
                             "agent/scripts/install-hooks.sh", check=False)
        res["hook_changed"] = bool(changed.strip())
    installer = repo / "agent" / "scripts" / "install-hooks.sh"
    if (migrar or res["hook_changed"]) and installer.exists():
        subprocess.run(["bash", str(installer)], cwd=repo, capture_output=True)
        res["messages"].append("hook pre-push reinstalado (install-hooks.sh)")
    elif res["hook_changed"]:
        res["messages"].append("el hook cambió: ejecuta bash agent/scripts/install-hooks.sh")
    if migrar:
        _, gitdir, _ = _git(repo, "rev-parse", "--git-common-dir")
        exclude = (repo / gitdir if not Path(gitdir).is_absolute() else Path(gitdir)) / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        current_text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        if "docs/superpowers/" not in current_text:
            with exclude.open("a", encoding="utf-8") as fh:
                fh.write("\n# agentic-fm: specs/planes de cliente viven en el vault, nunca en git\ndocs/superpowers/\n")
            res["messages"].append("docs/superpowers/ excluido del índice (.git/info/exclude)")
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
