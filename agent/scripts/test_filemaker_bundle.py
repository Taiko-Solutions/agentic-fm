#!/usr/bin/env python3
"""
test_filemaker_bundle.py - Invariants of filemaker/agentic-fm.xml (the agentic-fm add-on source).

Spec: agentic-fm-app docs/spec/2026-10-10-agfm-addon-design.md (§3, §5).

Usage:
    python3 -m unittest agent/scripts/test_filemaker_bundle.py
"""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[2] / "filemaker" / "agentic-fm.xml"
COMPANION_BASE = ('"http://" & If ( IsEmpty ( $$AGENTIC.FM.COMPANION.IP ) ; "localhost" ; '
                  '$$AGENTIC.FM.COMPANION.IP ) & ":8765')
_ROOT = ET.parse(BUNDLE).getroot()


def script(name):
    """The <Script> definition (the entry with steps; 0-step entries are Perform Script references)."""
    found = [s for s in _ROOT.iter("Script") if s.get("name") == name and s.find("Step") is not None]
    if not found:
        raise AssertionError(f"script {name!r} not in the bundle")
    return found[0]


def steps(name):
    return script(name).findall("Step")


def calcs(name):
    return [c.text or "" for c in script(name).iter("Calculation")]


def all_scripts():
    return [s.get("name") for s in _ROOT.iter("Script") if s.find("Step") is not None]


class TestCompanionHost(unittest.TestCase):
    def test_no_script_hard_codes_the_companion_host(self):
        for name in all_scripts():
            for text in calcs(name):
                self.assertNotIn("localhost:8765", text, name)
                self.assertNotIn("127.0.0.1:8765", text, name)

    def test_companion_calls_use_the_host_variable_with_a_localhost_fallback(self):
        for name in ("Explode XML", "Agentic-fm Webviewer", "Agentic-fm Paste", "Agentic-fm Debug"):
            self.assertTrue(any(COMPANION_BASE in text for text in calcs(name)), name)


class TestExplodeLocation(unittest.TestCase):
    def test_explode_xml_exports_to_the_temporary_folder(self):
        texts = calcs("Explode XML")
        self.assertTrue(any("Get ( TemporaryPath )" in t for t in texts))
        self.assertFalse(any("Get ( DesktopPath )" in t for t in texts))


SEMVER = re.compile(r'^"(\d+\.\d+\.\d+)"$')


def bundle_version():
    exits = [st for st in steps("AGFM Version") if st.get("name") == "Exit Script"]
    match = SEMVER.match((exits[0].findtext("Calculation") or "").strip())
    if not match:
        raise AssertionError("AGFM Version must exit with a quoted x.y.z literal")
    return match.group(1)


class TestVersion(unittest.TestCase):
    def test_version_is_a_quoted_semver_literal(self):
        self.assertEqual(bundle_version(), "1.0.0")

    def test_version_script_lives_in_the_top_folder(self):
        top = _ROOT.find("Group")
        self.assertIn("AGFM Version", [s.get("name") for s in top.findall("Script")])


if __name__ == "__main__":
    unittest.main()
