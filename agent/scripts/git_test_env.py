#!/usr/bin/env python3
"""
git_test_env.py - Import it first in tests that create git commits: every git run (direct or through the
scripts under test, which inherit the environment) then uses a private global config with a test identity and
no commit signing, instead of the developer's (signing through a password manager hangs or fails when locked).
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

_DIR = Path(tempfile.mkdtemp(prefix="agfm-git-test-"))
atexit.register(shutil.rmtree, _DIR, ignore_errors=True)
_CONFIG = _DIR / "gitconfig"
_CONFIG.write_text("[user]\n\tname = agentic-fm tests\n\temail = tests@example.invalid\n"
                   "[commit]\n\tgpgsign = false\n[tag]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n",
                   encoding="utf-8")
os.environ["GIT_CONFIG_GLOBAL"] = str(_CONFIG)
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
