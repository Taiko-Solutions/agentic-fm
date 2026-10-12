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


class TestMalformedBundle(unittest.TestCase):
    def test_a_script_without_its_close_tag_is_named(self):
        broken = BUNDLE.replace("    </Script>\n    <Script includeInMenu=\"False\" SiriShortcutVisible=\"False\" runFullAccess=\"False\" id=\"3\"",
                                "     </Script>\n    <Script includeInMenu=\"False\" SiriShortcutVisible=\"False\" runFullAccess=\"False\" id=\"3\"", 1)
        with self.assertRaisesRegex(ValueError, r"<Script> 'Keep' .*no matching </Script>"):
            B.build(broken, MANIFEST)

    def test_a_folder_with_a_misplaced_close_tag_is_named(self):
        """Well-formed XML (the XML parser is happy) but the close tag is not at the folder's indentation."""
        broken = BUNDLE.replace("    </Group>\n    <Group groupCollapsed=\"False\" includeInMenu=\"False\" id=\"6\"",
                                "     </Group>\n    <Group groupCollapsed=\"False\" includeInMenu=\"False\" id=\"6\"", 1)
        with self.assertRaisesRegex(ValueError, r"<Group> 'Sub' .*no matching </Group>"):
            B.build(broken, MANIFEST)

    def test_malformed_xml_is_a_clear_error(self):
        broken = BUNDLE.replace("    </Group>\n    <Group groupCollapsed=\"False\" includeInMenu=\"False\" id=\"6\"",
                                "    <Group groupCollapsed=\"False\" includeInMenu=\"False\" id=\"6\"", 1)
        with self.assertRaisesRegex(ValueError, r"not well-formed XML"):
            B.build(broken, MANIFEST)


class TestCommittedSnippet(unittest.TestCase):
    def test_committed_add_on_snippet_is_up_to_date(self):
        result = subprocess.run([sys.executable, str(REPO / "agent" / "scripts" / "build_addon_snippet.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_committed_snippet_has_exactly_the_manifest_scripts(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        text = (REPO / "filemaker" / "addon" / "agentic-fm-addon.xml").read_text(encoding="utf-8")
        self.assertEqual(names(text), set(manifest["scripts"]))


class TestPackageMetadata(unittest.TestCase):
    META = {**MANIFEST, "attribution": "Marco Pérez — based on agentic-fm by Matt Petrowsky",
            "url": "https://taikosolutions.com", "category": "Developer tools",
            "description": {"en": "agentic-fm {version}", "es": "agentic-fm versión {version}"}}

    def _package(self, tmp):
        import tempfile
        d = Path(tmp) / "agentic-fm"
        d.mkdir()
        (d / "info.json").write_text('\ufeff{\n\t"GUID" : "X",\n\t"Attribution" : "Claris",\n\t"URL" : "https://claris.com",\n\t"Version" : "1.0"\n}\n', encoding="utf-8")
        for lang in ("en", "es", "de"):
            (d / f"info_{lang}.json").write_text('\ufeff{\n\t"Title" : "agentic-fm",\n\t"Description" : "*** DESCRIPTION MISSING *** - DNL",\n\t"Category" : "___...___"\n}\n', encoding="utf-8")
        return d

    def _json(self, path):
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def test_metadata_replaces_filemaker_defaults(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = self._package(tmp)
            B.apply_metadata(d, self.META)
            info = self._json(d / "info.json")
            self.assertEqual(info["Attribution"], "Marco Pérez — based on agentic-fm by Matt Petrowsky")
            self.assertEqual(info["URL"], "https://taikosolutions.com")
            self.assertEqual(info["GUID"], "X")
            self.assertEqual(self._json(d / "info_es.json")["Description"], "agentic-fm versión 1.0.0")
            self.assertEqual(self._json(d / "info_de.json")["Description"], "agentic-fm 1.0.0")   # falls back to en
            self.assertEqual(self._json(d / "info_en.json")["Category"], "Developer tools")
            self.assertTrue((d / "info_en.json").read_text(encoding="utf-8").startswith("\ufeff"))   # BOM kept

    def test_quotes_in_the_manifest_survive_repeated_runs(self):
        import tempfile
        meta = {**self.META, "attribution": 'Marco "Taiko" Pérez',
                "description": {"en": 'the "agentic-fm" add-on {version}'}}
        with tempfile.TemporaryDirectory() as tmp:
            d = self._package(tmp)
            B.apply_metadata(d, meta)
            B.apply_metadata(d, meta)                                   # --package run twice
            self.assertEqual(self._json(d / "info.json")["Attribution"], 'Marco "Taiko" Pérez')
            self.assertEqual(self._json(d / "info_es.json")["Description"], 'the "agentic-fm" add-on 1.0.0')

    def test_archive_carries_no_machine_metadata(self):
        """--distribution leaves out user, group, extended attributes and times: no maintainer's data in the
        archive and the same bytes for the same files."""
        self.assertEqual(B.xar_command("agentic-fm.fmaddon", "agentic-fm"),
                         ["xar", "-cf", "agentic-fm.fmaddon", "--compression=gzip", "--distribution", "agentic-fm"])

    def test_committed_package_carries_the_manifest_metadata(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        info = self._json(REPO / "filemaker" / "addon" / "agentic-fm" / "info.json")
        self.assertEqual(info["Attribution"], manifest["attribution"])
        self.assertIn("Matt Petrowsky", info["Attribution"])
        self.assertEqual(info["URL"], manifest["url"])


class TestWebViewerSnippet(unittest.TestCase):
    def test_committed_web_viewer_snippet_has_only_the_scripts_outside_the_add_on(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        bundle = names((REPO / "filemaker" / "agentic-fm.xml").read_text(encoding="utf-8"))
        text = (REPO / "filemaker" / "addon" / "agentic-fm-webviewer.xml").read_text(encoding="utf-8")
        self.assertEqual(names(text), bundle - set(manifest["scripts"]))


class TestPackageMatchesBundle(unittest.TestCase):
    """A stale package (bundle edited, package not rebuilt) must fail here, not ship."""

    def test_every_calculation_of_the_manifest_scripts_is_in_the_package(self):
        import html
        import re
        literal = re.compile(r'"(?:[^"\\]|\\.)*"')
        token = re.compile(r'"com\.fmi\.calculation\.text\.[0-9A-Fa-f]+"')   # how template.xml stores literals

        def norm(text):
            return re.sub(r"\s+", " ", text).strip()

        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        template = html.unescape((REPO / "filemaker" / "addon" / "agentic-fm" / "template.xml").read_text(encoding="utf-8-sig"))
        template = norm(token.sub('""', template))
        root = ET.parse(REPO / "filemaker" / "agentic-fm.xml").getroot()
        missing = []
        for script in root.iter("Script"):
            if script.get("name") in manifest["scripts"] and script.find("Step") is not None:
                for calc in script.iter("Calculation"):
                    code = norm(literal.sub('""', calc.text or ""))
                    if len(code) >= 3 and code not in template:
                        missing.append((script.get("name"), code[:80]))
        self.assertEqual(missing, [], "package is stale: rebuild it in FileMaker, then build_addon_snippet.py --package")

    def test_package_version_matches_the_manifest(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        B.check_package_version(REPO / "filemaker" / "addon" / "agentic-fm", manifest)

    def test_a_package_with_another_version_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "en.xml").write_text("<SourceText>0.9.0</SourceText>", encoding="utf-8")
            with self.assertRaises(ValueError):
                B.check_package_version(Path(tmp), {"version": "1.0.0"})


class TestRunInCI(unittest.TestCase):
    def test_ci_checks_runs_the_add_on_tests(self):
        ci = (REPO / "agent" / "scripts" / "ci_checks.py").read_text(encoding="utf-8")
        self.assertIn("agent/scripts/test_build_addon_snippet.py", ci)
        self.assertIn("agent/scripts/test_filemaker_bundle.py", ci)


if __name__ == "__main__":
    unittest.main()
