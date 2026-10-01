"""Tests de check_pushed_paths.py (reglas de rutas del hook, safe-push y la Action).

Run: python3 agent/scripts/test_check_pushed_paths.py
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

import check_pushed_paths as cpp
from test_sync_clone import git, make_origin

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES = cpp.load_rules(REPO_ROOT / "agent/scripts/hooks/paths.conf")


class ForbiddenTests(unittest.TestCase):
    def test_forbidden_blocks_on_any_branch(self):
        r = cpp.classify(["agent/CONTEXT.json", "agent/docs/taiko/x.md"], "trabajo", is_base=True, rules=RULES)
        self.assertFalse(r.ok)
        self.assertEqual([f for f, _ in r.blocked], ["agent/CONTEXT.json"])

    def test_forbidden_file_reported_once(self):
        r = cpp.classify(["agent/CONTEXT.json"], "mejora/x", is_base=False, rules=RULES)
        self.assertEqual(len(r.blocked), 1, r.blocked)

    def test_whitelist_wins_over_forbidden(self):
        r = cpp.classify(["agent/config/automation.json.example", "agent/sandbox/script.xml"], "mejora/x", False, RULES)
        self.assertTrue(r.ok, r.blocked)


class BranchRuleTests(unittest.TestCase):
    def test_clone_cannot_push_taiko_or_trabajo(self):
        for br in ("taiko", "trabajo"):
            r = cpp.classify(["agent/docs/taiko/x.md"], br, is_base=False, rules=RULES)
            self.assertFalse(r.ok, br)
            self.assertIn("rama", r.blocked[0][1])

    def test_base_repo_can_push_taiko(self):
        r = cpp.classify(["agent/docs/taiko/x.md", "docs/superpowers/specs/y.md"], "taiko", is_base=True, rules=RULES)
        self.assertTrue(r.ok, r.blocked)


class AllowlistTests(unittest.TestCase):
    def test_mejora_outside_allowlist_blocked(self):
        r = cpp.classify(["docs/superpowers/specs/x.md", "agent/docs/taiko/ok.md"], "mejora/x", False, RULES)
        self.assertEqual([f for f, _ in r.blocked], ["docs/superpowers/specs/x.md"])

    def test_mejora_tool_layer_passes(self):
        files = [".claude/CLAUDE.md", "agent/scripts/x.py", "agent/fmlint/rules/y.py",
                 "agent/catalogs/step-catalog-en.json", "filemaker/agentic-fm.xml",
                 "agent/UPSTREAM_PROPOSALS.md", "TAIKO-UPDATES.md", ".github/workflows/a.yml",
                 "agent/config/companion.json.example"]
        r = cpp.classify(files, "mejora/x", False, RULES)
        self.assertTrue(r.ok, r.blocked)

    def test_mejora_rules_without_changelog_warns(self):
        r = cpp.classify(["agent/docs/taiko/knowledge/a.md"], "mejora/x", False, RULES)
        self.assertTrue(r.ok)
        self.assertTrue(any("TAIKO-UPDATES.md" in w for w in r.warnings))

    def test_any_other_branch_from_clone_uses_allowlist(self):
        # Claude Desktop abre PRs desde ramas claude/*; una rama backup/* podría reintroducir un spec.
        r = cpp.classify(["docs/superpowers/specs/x.md"], "claude/abc", False, RULES)
        self.assertFalse(r.ok)
        r = cpp.classify(["agent/docs/taiko/ok.md", "TAIKO-UPDATES.md"], "claude/abc", False, RULES)
        self.assertTrue(r.ok, r.blocked)


class ConfParsingTests(unittest.TestCase):
    def test_blank_and_comment_lines_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "paths.conf"
            p.write_text("[forbidden]\n\n# comentario\n^secret/   \n[whitelist]\n[allow]\n^ok/\n[changelog-trigger]\n",
                         encoding="utf-8")
            rules = cpp.load_rules(p)
            self.assertEqual([r.pattern for r in rules["forbidden"]], ["^secret/"])
            r = cpp.classify(["ok/a.md"], "mejora/x", False, rules)
            self.assertTrue(r.ok, r.blocked)


class ChangedFilesTests(unittest.TestCase):
    """Los ficheros del rango se calculan POR COMMIT (con -m en merges), no como diff de árboles."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.origin, self.seed = make_origin(self.tmp)
        self.clone = self.tmp / "clone"
        git(self.tmp, "clone", "-q", str(self.origin), str(self.clone))
        git(self.clone, "config", "user.email", "t@t")
        git(self.clone, "config", "user.name", "t")
        git(self.clone, "checkout", "-qb", "mejora/x")

    def commit_file(self, rel, text, msg):
        f = self.clone / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-qm", msg)

    def test_added_then_deleted_is_still_seen(self):
        self.commit_file("docs/spec.md", "secreto", "añade")
        git(self.clone, "rm", "-q", "docs/spec.md")
        git(self.clone, "commit", "-qm", "borra")
        self.assertIn("docs/spec.md", cpp.changed_files(self.clone, "origin/taiko..HEAD"))

    def test_pure_deletion_is_ignored(self):
        git(self.clone, "rm", "-q", "agent/a.md")
        git(self.clone, "commit", "-qm", "borra a")
        self.assertEqual(cpp.changed_files(self.clone, "origin/taiko..HEAD"), [])

    def test_file_introduced_in_merge_commit_is_seen(self):
        self.commit_file("agent/a.md", "rama x", "x")
        git(self.clone, "checkout", "-qb", "otra", "origin/taiko")
        self.commit_file("agent/a.md", "rama otra", "otra")
        git(self.clone, "checkout", "-q", "mejora/x")
        rc = subprocess.run(["git", "-C", str(self.clone), "merge", "otra"], capture_output=True).returncode
        self.assertNotEqual(rc, 0)                       # conflicto esperado
        (self.clone / "agent" / "a.md").write_text("resuelto", encoding="utf-8")
        (self.clone / "docs").mkdir(exist_ok=True)
        (self.clone / "docs" / "evil.md").write_text("colado en el merge", encoding="utf-8")
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-qm", "merge con regalo")
        self.assertIn("docs/evil.md", cpp.changed_files(self.clone, "origin/taiko..HEAD"))

    def test_new_branch_revs_syntax(self):
        self.commit_file("agent/b.md", "b", "b")
        self.assertIn("agent/b.md", cpp.changed_files(self.clone, "HEAD --not --remotes"))


if __name__ == "__main__":
    unittest.main()
