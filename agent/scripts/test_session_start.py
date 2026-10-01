"""Tests del check git de session_start.py (ramas trabajo/taiko y novedades).

Run: python3 agent/scripts/test_session_start.py
"""
import tempfile
import unittest
from pathlib import Path

import session_start as ss
from test_sync_clone import git, make_origin, add_rule


class CheckGitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.origin, self.seed = make_origin(self.tmp)
        self.clone = self.tmp / "clone"
        git(self.tmp, "clone", "-q", str(self.origin), str(self.clone))

    def test_clone_on_taiko_warns_to_use_trabajo(self):
        status, msg, data = ss.check_git(self.clone)
        self.assertEqual(status, ss.WARN)
        self.assertIn("trabajo", msg)
        self.assertEqual(data["branch"], "taiko")

    def test_trabajo_behind_lists_updates(self):
        git(self.clone, "checkout", "-qb", "trabajo")
        add_rule(self.seed, "2026-10-01 — Nueva regla")
        status, msg, data = ss.check_git(self.clone)
        self.assertEqual(status, ss.WARN)
        self.assertEqual(data["behind"], 1)
        self.assertEqual(data["updates"], ["2026-10-01 — Nueva regla"])
        self.assertIn("agentic-fm-sync", msg)

    def test_trabajo_up_to_date_ok(self):
        git(self.clone, "checkout", "-qb", "trabajo")
        status, _, data = ss.check_git(self.clone)
        self.assertEqual(status, ss.OK)
        self.assertEqual(data["updates"], [])

    def test_repo_without_origin_taiko_uses_main(self):
        git(self.seed, "branch", "main")
        git(self.seed, "push", "-q", "origin", "main")
        git(self.origin, "symbolic-ref", "HEAD", "refs/heads/main")
        git(self.seed, "push", "-q", "origin", ":taiko")
        other = self.tmp / "other"
        git(self.tmp, "clone", "-q", "-b", "main", str(self.origin), str(other))
        status, msg, data = ss.check_git(other)
        self.assertEqual(data["model"], "main")
        self.assertEqual(status, ss.OK)


if __name__ == "__main__":
    unittest.main()
