#!/usr/bin/env python3
"""Repo sanity checks for agentic-fm.

Guards the machine-readable artifacts that every other tool depends on:

  1. catalogs   — every agent/catalogs/*.json parses as valid JSON
                  (a single missing comma silently breaks every consumer)
  2. converter  — unit tests for the SaXML → fmxmlsnippet translator
  3. scripts    — paths rules, sync_clone and session_start tests
  4. fmlint     — unit tests for the linter (incl. the param-fidelity
                  corpus smoke test against agent/snippet_examples/)

Usage:
  python3 agent/scripts/ci_checks.py            # run everything
  python3 agent/scripts/ci_checks.py --quick    # catalogs only (fast path)

Exit code 0 = all green; 1 = at least one check failed.
Designed to be run by hand, from the pre-push hook, or from CI.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def check_catalogs() -> list:
    """Validate every JSON catalog parses. Returns list of failures."""
    failures = []
    catalog_dir = REPO_ROOT / "agent" / "catalogs"
    files = sorted(catalog_dir.glob("*.json"))
    if not files:
        return [f"no JSON catalogs found in {catalog_dir}"]
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT)}: invalid JSON — {exc}")
        except OSError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT)}: unreadable — {exc}")
    return failures


def _clean_env() -> dict:
    """Environment without git's repo-local variables.

    Run from a git hook (pre-push), git exports GIT_DIR and friends; the tests that
    build throwaway repos would then run their git commands against THIS repo and
    fail (seen pushing from a worktree). ``git rev-parse --local-env-vars`` lists them.
    """
    env = dict(os.environ)
    try:
        names = subprocess.run(["git", "rev-parse", "--local-env-vars"],
                               capture_output=True, text=True).stdout.split()
    except OSError:
        names = []
    for name in names or ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX"):
        env.pop(name, None)
    return env


def run_cmd(label: str, cmd: list) -> list:
    """Run a test command from the repo root. Returns list of failures."""
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=300,
        env=_clean_env(),
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-12:])
        return [f"{label} failed (exit {proc.returncode}):\n{tail}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="catalog JSON validation only (skip test suites)")
    args = parser.parse_args()

    checks = [("catalogs", check_catalogs)]
    if not args.quick:
        checks.append(("converter tests", lambda: run_cmd(
            "converter tests",
            [sys.executable, "agent/scripts/test_fm_xml_to_snippet.py"])))
        checks.append(("freshness check tests", lambda: run_cmd(
            "freshness check tests",
            [sys.executable, "agent/scripts/test_check_embedded_agfm.py"])))
        for label, script in (("paths rules tests", "agent/scripts/test_check_pushed_paths.py"),
                              ("sync_clone tests", "agent/scripts/test_sync_clone.py"),
                              ("session_start tests", "agent/scripts/test_session_start.py"),
                              ("analyze layouts tests", "agent/scripts/test_analyze_layouts.py")):
            checks.append((label, lambda label=label, script=script: run_cmd(
                label, [sys.executable, script])))
        checks.append(("explode layouts tests (fmparse.sh + fmcontext.sh)", lambda: run_cmd(
            "explode layouts tests", ["bash", "agent/scripts/test_explode_layouts.sh"])))
        checks.append(("agentic-fm-start tests", lambda: run_cmd(
            "agentic-fm-start tests", ["bash", "agent/scripts/test_agentic_fm_start.sh"])))
        checks.append(("fmlint tests", lambda: run_cmd(
            "fmlint tests",
            [sys.executable, "-m", "unittest", "discover",
             "-s", "agent/fmlint/tests", "-t", "."])))

    all_failures = []
    for label, fn in checks:
        failures = fn()
        status = "OK" if not failures else "FAIL"
        print(f"[{status}] {label}")
        all_failures.extend(failures)

    if all_failures:
        print("\n--- failures ---", file=sys.stderr)
        for f in all_failures:
            print(f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
