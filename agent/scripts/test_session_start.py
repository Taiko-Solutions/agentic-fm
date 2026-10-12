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


class CheckEmbeddedAddonTests(unittest.TestCase):
    def _report(self, objects):
        import json
        from unittest import mock
        root = Path(tempfile.mkdtemp())
        (root / "agent" / "xml_parsed").mkdir(parents=True)
        (root / "agent" / "scripts").mkdir(parents=True)
        (root / "agent" / "scripts" / "check_embedded_agfm.py").write_text("", encoding="utf-8")
        report = json.dumps({"objects": objects, "checked": True, "explode_present": True})
        with mock.patch.object(ss, "REPO_ROOT", root), mock.patch.object(ss, "_run", return_value=(1, report)):
            return ss.check_embedded()

    def test_pasted_bundle_points_to_the_add_on_not_to_re_pasting(self):
        status, msg, _ = self._report([
            {"name": "AGFM Start", "kind": "script", "status": "MISSING", "diff": ""},
            {"name": "add-on (Demo)", "kind": "addon", "status": "PASTED", "diff": ""}])
        self.assertEqual(status, ss.WARN)
        self.assertIn("add-on", msg)
        self.assertNotIn("repegar", msg)

    def test_outdated_add_on_with_local_edits_keeps_the_diff_warning(self):
        status, msg, _ = self._report([
            {"name": "add-on (Demo)", "kind": "addon", "status": "STALE", "diff": "0.9.0 → 1.0.0"},
            {"name": "Explode XML", "kind": "script", "status": "STALE", "diff": "+x"}])
        self.assertEqual(status, ss.WARN)
        self.assertIn("desinstala", msg)
        self.assertIn("Explode XML", msg)
        self.assertIn("--diff", msg)

    def test_current_add_on_with_edited_scripts_does_not_say_re_paste(self):
        status, msg, _ = self._report([
            {"name": "add-on (Demo)", "kind": "addon", "status": "OK", "diff": ""},
            {"name": "Explode XML", "kind": "script", "status": "STALE", "diff": "+x"}])
        self.assertEqual(status, ss.WARN)
        self.assertIn("Explode XML", msg)
        self.assertNotIn("repegar", msg)

    def test_outdated_add_on_says_uninstall_and_install(self):
        status, msg, _ = self._report([
            {"name": "add-on (Demo)", "kind": "addon", "status": "STALE", "diff": "0.9.0 → 1.0.0"}])
        self.assertEqual(status, ss.WARN)
        self.assertIn("desinstala", msg)
        self.assertIn("0.9.0 → 1.0.0", msg)


if __name__ == "__main__":
    unittest.main()
