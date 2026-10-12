#!/usr/bin/env python3
"""
test_git_test_env.py - Tests that create git commits must not depend on the developer's global git config
(commit signing through a password manager hangs or fails when it is locked).

Usage:
    python3 -m unittest agent/scripts/test_git_test_env.py
"""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class TestGitTestEnv(unittest.TestCase):
    def test_commits_work_under_a_hostile_global_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            hostile = Path(tmp) / "hostile-gitconfig"
            hostile.write_text("[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = /usr/bin/false\n"
                               "[gpg \"ssh\"]\n\tprogram = /usr/bin/false\n", encoding="utf-8")
            script = textwrap.dedent(f"""
                import subprocess, sys
                sys.path.insert(0, {str(HERE)!r})
                import git_test_env  # noqa: F401 — isolates every git run below
                repo = {str(Path(tmp) / "repo")!r}
                subprocess.run(["git", "init", "-q", repo], check=True)
                open(repo + "/a.txt", "w").write("a")
                subprocess.run(["git", "-C", repo, "add", "a.txt"], check=True)
                subprocess.run(["git", "-C", repo, "commit", "-qm", "x"], check=True)
            """)
            env = {**os.environ, "GIT_CONFIG_GLOBAL": str(hostile)}
            result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True,
                                    timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
