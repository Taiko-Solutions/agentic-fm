#!/usr/bin/env python3
"""
test_build_addon_snippet.py - The add-on snippet is the full bundle restricted to the manifest.

Usage:
    python3 -m unittest agent/scripts/test_build_addon_snippet.py
"""

import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_addon_snippet as B

REPO = Path(__file__).resolve().parents[2]
BUNDLE = """<?xml version="1.0"?>
<fmxmlsnippet type="FMObjectList">
  <Group groupCollapsed="False" includeInMenu="False" id="1" name="agentic-fm">
    <Script includeInMenu="False" SiriShortcutVisible="False" runFullAccess="False" id="2" name="Keep">
      <Step enable="True" id="103" name="Exit Script">
        <Calculation><![CDATA["a" & "b"]]></Calculation>
      </Step>
    </Script>
    <Script includeInMenu="False" SiriShortcutVisible="False" runFullAccess="False" id="3" name="Drop">
      <Step enable="True" id="103" name="Exit Script"/>
    </Script>
    <Group groupCollapsed="False" includeInMenu="False" id="4" name="Sub">
      <Script includeInMenu="False" SiriShortcutVisible="False" runFullAccess="True" id="5" name="Nested">
        <Step enable="True" id="1" name="Perform Script">
          <Script id="2" name="Keep"/>
        </Step>
      </Script>
    </Group>
    <Group groupCollapsed="False" includeInMenu="False" id="6" name="Gone">
      <Script includeInMenu="False" SiriShortcutVisible="False" runFullAccess="False" id="7" name="Drop too">
        <Step enable="True" id="103" name="Exit Script"/>
      </Script>
    </Group>
    <Group groupCollapsed="False" includeInMenu="False" id="8" name="Empty"/>
  </Group>
</fmxmlsnippet>
"""
MANIFEST = {"name": "agentic-fm", "version": "1.0.0", "scripts": ["Keep", "Nested"], "custom_functions": []}


def names(xml_text):
    root = ET.fromstring(xml_text)
    return {s.get("name") for s in root.iter("Script") if s.find("Step") is not None}


class TestBuild(unittest.TestCase):
    def test_keeps_only_manifest_scripts(self):
        self.assertEqual(names(B.build(BUNDLE, MANIFEST)), {"Keep", "Nested"})

    def test_keeps_folders_with_content_and_drops_empty_ones(self):
        root = ET.fromstring(B.build(BUNDLE, MANIFEST))
        groups = [g.get("name") for g in root.iter("Group")]
        self.assertEqual(groups, ["agentic-fm", "Sub"])

    def test_script_xml_is_unchanged(self):
        out = B.build(BUNDLE, MANIFEST)
        self.assertIn('<Calculation><![CDATA["a" & "b"]]></Calculation>', out)
        self.assertIn('runFullAccess="True" id="5" name="Nested"', out)
        self.assertIn('<Script id="2" name="Keep"/>', out)

    def test_output_is_deterministic(self):
        self.assertEqual(B.build(BUNDLE, MANIFEST), B.build(BUNDLE, MANIFEST))

    def test_unknown_manifest_script_is_an_error(self):
        with self.assertRaises(ValueError):
            B.build(BUNDLE, {**MANIFEST, "scripts": ["Keep", "Missing"]})


class TestCommittedSnippet(unittest.TestCase):
    def test_committed_add_on_snippet_is_up_to_date(self):
        result = subprocess.run([sys.executable, str(REPO / "agent" / "scripts" / "build_addon_snippet.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_committed_snippet_has_exactly_the_manifest_scripts(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        text = (REPO / "filemaker" / "addon" / "agentic-fm-addon.xml").read_text(encoding="utf-8")
        self.assertEqual(names(text), set(manifest["scripts"]))


if __name__ == "__main__":
    unittest.main()
