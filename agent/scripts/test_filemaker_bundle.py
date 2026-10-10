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


INTERACTIVE = {"Show Custom Dialog", "Get Folder Path", "Show/Hide Toolbars", "Pause/Resume Script"}


def step_names(name):
    return [st.get("name") for st in steps(name)]


class TestPathScript(unittest.TestCase):
    def test_path_script_has_no_dialogs(self):
        self.assertFalse(INTERACTIVE & set(step_names("Get agentic-fm path")))

    def test_path_script_asks_config_with_the_file_name_encoded_once(self):
        texts = calcs("Get agentic-fm path")
        self.assertTrue(any("/config?file=" in t and "GetAsURLEncoded ( Get ( FileName ) )" in t for t in texts))
        urls = [st for st in steps("Get agentic-fm path") if st.get("name") == "Insert from URL"]
        self.assertTrue(urls)
        for st in urls:
            self.assertEqual(st.find("DontEncodeURL").get("state"), "True")
            self.assertIn("--max-time 3", st.find("CURLOptions/Calculation").text)

    def test_path_script_reports_every_failure_as_json(self):
        joined = "\n".join(calcs("Get agentic-fm path"))
        for error in ('"no_service"', '"no_config"', 'JSONGetElement ( $response ; "error" )'):
            self.assertIn(error, joined)
        exits = [st for st in steps("Get agentic-fm path") if st.get("name") == "Exit Script"]
        self.assertTrue(exits)
        for st in exits:
            self.assertIn('[ "ok" ;', st.findtext("Calculation"))

    def test_path_script_sets_both_globals_from_the_answer(self):
        joined = "\n".join(calcs("Get agentic-fm path"))
        self.assertIn('JSONGetElement ( $response ; "repo_path" )', joined)
        names = [st.findtext("Name") for st in steps("Get agentic-fm path") if st.get("name") == "Set Variable"]
        self.assertIn("$$AGENTIC.FM", names)
        self.assertIn("$$AGENTIC.FM.COMPANION.IP", names)


class TestChooseFolder(unittest.TestCase):
    def test_choose_folder_is_the_interactive_fallback(self):
        names = step_names("AGFM Choose Folder")
        self.assertIn("Get Folder Path", names)
        self.assertIn("Get File Exists", names)


if __name__ == "__main__":
    unittest.main()
