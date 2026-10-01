"""Tests de check_pushed_paths.py (reglas de rutas del hook, safe-push y la Action).

Run: python3 agent/scripts/test_check_pushed_paths.py
"""
import tempfile
import unittest
from pathlib import Path

import check_pushed_paths as cpp

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


if __name__ == "__main__":
    unittest.main()
