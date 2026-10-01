"""Tests de sync_clone.py con repos de juguete (sin datos reales).

Run: python3 agent/scripts/test_sync_clone.py
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

import sync_clone as sc


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def make_origin(tmp: Path):
    """Origen bare con rama taiko (HEAD → taiko) y un seed que la alimenta."""
    origin = tmp / "origin.git"
    seed = tmp / "seed"
    git(tmp, "init", "-q", "--bare", str(origin))
    git(origin, "symbolic-ref", "HEAD", "refs/heads/taiko")
    git(tmp, "init", "-q", str(seed))
    git(seed, "config", "user.email", "t@t")
    git(seed, "config", "user.name", "t")
    (seed / "TAIKO-UPDATES.md").write_text("# Changelog Taiko\n\n## 2026-09-01 — Primera\n", encoding="utf-8")
    (seed / "agent").mkdir()
    (seed / "agent" / "a.md").write_text("a", encoding="utf-8")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "base")
    git(seed, "branch", "-M", "taiko")
    git(seed, "remote", "add", "origin", str(origin))
    git(seed, "push", "-q", "origin", "taiko")
    return origin, seed


def add_rule(seed: Path, title: str):
    p = seed / "TAIKO-UPDATES.md"
    p.write_text(p.read_text(encoding="utf-8") + f"\n## {title}\n", encoding="utf-8")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", title)
    git(seed, "push", "-q", "origin", "taiko")


class SyncCloneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.origin, self.seed = make_origin(self.tmp)
        self.clone = self.tmp / "clone"
        git(self.tmp, "clone", "-q", str(self.origin), str(self.clone))
        git(self.clone, "config", "user.email", "t@t")
        git(self.clone, "config", "user.name", "t")

    def test_fresh_clone_creates_trabajo_and_lists_updates(self):
        add_rule(self.seed, "2026-10-01 — Segunda")
        res = sc.sync(self.clone)
        self.assertEqual(res["mode"], "clone")
        self.assertTrue(res["merged"], res)
        self.assertEqual(git(self.clone, "branch", "--show-current"), "trabajo")
        self.assertEqual(res["updates"], ["2026-10-01 — Segunda"])

    def test_no_updates_when_up_to_date(self):
        res = sc.sync(self.clone)
        self.assertEqual(res["updates"], [])
        self.assertTrue(res["merged"], res)

    def test_migrar_moves_local_commits_off_taiko(self):
        (self.clone / "local.md").write_text("cliente", encoding="utf-8")
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-qm", "commit de cliente")
        git(self.clone, "remote", "add", "upstream", str(self.origin))   # anomalía a corregir
        add_rule(self.seed, "2026-10-02 — Tercera")
        res = sc.sync(self.clone, migrar=True)
        self.assertTrue(res["migrated"], res)
        self.assertEqual(git(self.clone, "branch", "--show-current"), "trabajo")
        self.assertEqual(git(self.clone, "rev-parse", "taiko"), git(self.clone, "rev-parse", "origin/taiko"))
        self.assertIn("commit de cliente", git(self.clone, "log", "--oneline", "trabajo"))
        self.assertNotIn("upstream", git(self.clone, "remote"))

    def test_sync_without_migrar_refuses_when_taiko_has_local_commits(self):
        (self.clone / "local.md").write_text("cliente", encoding="utf-8")
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-qm", "commit de cliente")
        sha = git(self.clone, "rev-parse", "HEAD")
        res = sc.sync(self.clone)
        self.assertFalse(res["merged"], res)
        self.assertTrue(any("--migrar" in m for m in res["messages"]), res["messages"])
        self.assertEqual(git(self.clone, "rev-parse", "taiko"), sha)          # nada destruido

    def test_migrar_with_existing_trabajo_keeps_local_taiko_commits(self):
        git(self.clone, "branch", "trabajo")
        (self.clone / "local.md").write_text("cliente", encoding="utf-8")
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-qm", "commit de cliente")
        res = sc.sync(self.clone, migrar=True)
        self.assertTrue(res["migrated"], res)
        self.assertIn("commit de cliente", git(self.clone, "log", "--oneline", "trabajo"))
        self.assertEqual(git(self.clone, "rev-parse", "taiko"), git(self.clone, "rev-parse", "origin/taiko"))

    def test_migrar_excludes_client_specs(self):
        res = sc.sync(self.clone, migrar=True)
        self.assertTrue(res["migrated"], res)
        exclude = (self.clone / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        self.assertIn("docs/superpowers/", exclude)

    def test_hook_change_is_reported(self):
        git(self.clone, "checkout", "-qb", "trabajo")
        (self.seed / "agent" / "scripts" / "hooks").mkdir(parents=True)
        (self.seed / "agent" / "scripts" / "hooks" / "pre-push").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        git(self.seed, "add", "-A")
        git(self.seed, "commit", "-qm", "hook nuevo")
        git(self.seed, "push", "-q", "origin", "taiko")
        res = sc.sync(self.clone)
        self.assertTrue(res["merged"], res)
        self.assertTrue(res["hook_changed"])
        self.assertTrue(any("install-hooks" in m for m in res["messages"]), res["messages"])

    def test_untracked_files_do_not_block_sync(self):
        (self.clone / "borrador.md").write_text("sin trackear", encoding="utf-8")
        res = sc.sync(self.clone)
        self.assertTrue(res["merged"], res)
        self.assertTrue((self.clone / "borrador.md").exists())

    def test_modified_tracked_file_blocks_sync(self):
        (self.clone / "agent" / "a.md").write_text("modificado", encoding="utf-8")
        res = sc.sync(self.clone)
        self.assertFalse(res["merged"])
        self.assertTrue(any("sin commit" in m for m in res["messages"]), res["messages"])

    def rewrite_origin_history(self):
        """Simula un force-push: el seed reescribe su último commit y lo empuja forzado."""
        git(self.seed, "commit", "--amend", "-qm", "base (reescrita)")
        git(self.seed, "push", "-q", "--force", "origin", "taiko")

    def test_migrar_after_force_push_without_local_work_tracks_new_history(self):
        self.rewrite_origin_history()
        res = sc.sync(self.clone, migrar=True)
        self.assertTrue(res["merged"], res)
        self.assertEqual(res["conflicts"], [])
        self.assertEqual(git(self.clone, "rev-parse", "trabajo"), git(self.clone, "rev-parse", "origin/taiko"))
        self.assertTrue(any("reescrit" in m for m in res["messages"]), res["messages"])
        backups = [b.strip() for b in git(self.clone, "branch", "--list", "backup/taiko-pre-reescritura-*").splitlines()]
        self.assertEqual(len(backups), 1, backups)          # la historia antigua queda en una rama, no solo en el reflog

    def test_migrar_after_force_push_rebases_real_local_commits(self):
        (self.clone / "local.md").write_text("cliente", encoding="utf-8")
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-qm", "commit de cliente")
        self.rewrite_origin_history()
        res = sc.sync(self.clone, migrar=True)
        self.assertTrue(res["merged"], res)
        log = git(self.clone, "log", "--oneline", "trabajo")
        self.assertIn("commit de cliente", log)
        self.assertIn("base (reescrita)", log)
        self.assertEqual(git(self.clone, "rev-list", "--count", "origin/taiko..trabajo"), "1")

    def test_conflict_reported_not_raised(self):
        git(self.clone, "checkout", "-qb", "trabajo")
        (self.clone / "agent" / "a.md").write_text("local", encoding="utf-8")
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-qm", "local")
        (self.seed / "agent" / "a.md").write_text("remoto", encoding="utf-8")
        git(self.seed, "add", "-A")
        git(self.seed, "commit", "-qm", "remoto")
        git(self.seed, "push", "-q", "origin", "taiko")
        res = sc.sync(self.clone)
        self.assertFalse(res["merged"])
        self.assertIn("agent/a.md", res["conflicts"])
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")   # merge abortado, árbol limpio

    def test_base_repo_refuses(self):
        git(self.clone, "remote", "add", "upstream", str(self.origin))
        res = sc.sync(self.clone)
        self.assertEqual(res["mode"], "base")
        self.assertFalse(res["merged"])

    def test_updates_between_parses_only_added_headings(self):
        before = git(self.clone, "rev-parse", "origin/taiko")
        add_rule(self.seed, "2026-10-03 — Cuarta")
        git(self.clone, "fetch", "-q", "origin")
        after = git(self.clone, "rev-parse", "origin/taiko")
        self.assertEqual(sc.updates_between(self.clone, before, after), ["2026-10-03 — Cuarta"])


if __name__ == "__main__":
    unittest.main()
