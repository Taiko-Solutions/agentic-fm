#!/usr/bin/env python3
"""
test_check_embedded_agfm.py - Unit tests for the embedded agentic-fm freshness check.

These tests pin the three faults that made the check silently useless: it looked
for a flat directory of scripts, it looked for the Context custom function in
folders the exporter never writes, and it compared raw step signatures across
two formats that disagree on meaningless detail.

Usage:
    python3 agent/scripts/test_check_embedded_agfm.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_embedded_agfm as C


class TestStemNormalisation(unittest.TestCase):
    def test_strips_exporter_id_suffix(self):
        self.assertEqual(C._stem_without_id(Path("Explode XML - ID 39.xml")), "Explode XML")
        self.assertEqual(C._stem_without_id(Path("AGFMScriptBridge - ID 7.xml")), "AGFMScriptBridge")

    def test_leaves_plain_names_alone(self):
        self.assertEqual(C._stem_without_id(Path("Explode XML.xml")), "Explode XML")

    def test_does_not_eat_a_trailing_id_that_is_part_of_the_name(self):
        self.assertEqual(C._stem_without_id(Path("Set Record ID.xml")), "Set Record ID")


class TestEmbeddedScriptIndex(unittest.TestCase):
    def test_finds_scripts_nested_per_solution_and_folder(self):
        """The exporter nests scripts; a flat glob finds nothing at all."""
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp) / "scripts"
            nested = scripts / "SolutionApp" / "agentic-fm - ID 37" / "OData - ID 41"
            nested.mkdir(parents=True)
            (nested / "AGFMScriptBridge - ID 42.xml").write_text("<x/>", encoding="utf-8")
            index = C._index_embedded_scripts(scripts)
            self.assertIn(C._key("AGFMScriptBridge"), index)

    def test_missing_directory_is_not_an_error(self):
        self.assertEqual(C._index_embedded_scripts(Path("/nonexistent/scripts")), {})


class TestContextLookup(unittest.TestCase):
    def _stub(self, root, folder):
        d = root / folder / "SolutionApp"
        d.mkdir(parents=True)
        (d / "Context - ID 3.xml").write_text(
            '<CustomFunction name="Context"><Calculation><Text>'
            'Let ( ~x = 1 ; ~x )'
            '</Text></Calculation></CustomFunction>', encoding="utf-8")

    def test_reads_from_custom_function_stubs(self):
        """custom_function_stubs is what the exporter actually produces."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._stub(root, "custom_function_stubs")
            self.assertIn("Let ( ~x = 1 ; ~x )", C._embedded_context_text(root) or "")

    def test_reads_from_custom_function_calcs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._stub(root, "custom_function_calcs")
            self.assertIsNotNone(C._embedded_context_text(root))

    def test_absent_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(C._embedded_context_text(Path(tmp)))


class TestExplodePresence(unittest.TestCase):
    def test_absent_directory(self):
        self.assertFalse(C._explode_present(Path("/nonexistent/xml_parsed")))

    def test_empty_directory_is_not_an_explode(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(C._explode_present(Path(tmp)))

    def test_ds_store_alone_is_not_an_explode(self):
        """macOS drops .DS_Store into the directory the setup creates up front."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".DS_Store").write_bytes(b"\x00")
            self.assertFalse(C._explode_present(Path(tmp)))

    def test_nested_xml_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "scripts" / "SolutionApp"
            d.mkdir(parents=True)
            (d / "Thing - ID 1.xml").write_text("<x/>", encoding="utf-8")
            self.assertTrue(C._explode_present(Path(tmp)))


class TestConverterNoise(unittest.TestCase):
    def test_dropped_parameter_is_noise(self):
        """fm_xml_to_snippet.py drops params it does not model; that only removes text."""
        self.assertTrue(C._looks_like_converter_loss(
            "Save a Copy as XML [ Destination file: $output ; Window name: Get ( WindowName ) ]",
            "Save a Copy as XML [ Window name: Get ( WindowName ) ]"))
        self.assertTrue(C._looks_like_converter_loss(
            "Perform AppleScript [ Text ; tell me to activate ]",
            "Perform AppleScript [ Text ]"))

    def test_engine_case_rewrite_is_noise(self):
        self.assertTrue(C._looks_like_converter_loss(
            "Set Variable [ $t ; Value: Get ( CurrentTimestamp ) ]",
            "Set Variable [ $t ; Value: Get ( CurrentTimeStamp ) ]"))

    def test_added_text_is_real_drift(self):
        """FileMaker commenting out an unresolvable reference ADDS text."""
        self.assertFalse(C._looks_like_converter_loss(
            "Set Variable [ $text ; Value: Table::CLIPBOARD ]",
            "Set Variable [ $text ; Value: /*Table::CLIPBOARD*/ ]"))

    def test_changed_value_is_real_drift(self):
        self.assertFalse(C._looks_like_converter_loss(
            "Set Variable [ $o ; Value: Get ( DesktopPath ) ]",
            "Set Variable [ $o ; Value: Get ( TemporaryPath ) ]"))


class TestCompareHR(unittest.TestCase):
    def test_identical_is_ok(self):
        self.assertEqual(C._compare_hr("a\nb", "a\nb")[0], "OK")

    def test_converter_loss_only_is_ok_tilde(self):
        status, _ = C._compare_hr(
            "Perform AppleScript [ Text ; tell me to activate ]\nOpen Script Workspace",
            "Perform AppleScript [ Text ]\nOpen Script Workspace")
        self.assertEqual(status, "OK~")

    def test_inserted_logic_is_stale(self):
        status, diff = C._compare_hr(
            "Exit Script [ Text Result: True ]",
            "If [ Get ( AccountName ) = \"X\" ]\nExit Script [ Text Result: True ]")
        self.assertEqual(status, "STALE")
        self.assertTrue(diff)

    def test_enum_label_difference_is_not_drift(self):
        """The two sides render the same enum option with different labels."""
        enum_map = {"browsedrecords": "records being browsed"}
        status, _ = C._compare_hr(
            "Save Records as Snapshot Link [ Records: BrowsedRecords ]",
            "Save Records as Snapshot Link [ Records: Records being browsed ]",
            enum_map)
        self.assertEqual(status, "OK~")


class TestEnumLabelMap(unittest.TestCase):
    def test_short_values_are_not_mapped(self):
        """True/False -> On/Off must never rewrite unrelated text."""
        repo_root = Path(__file__).resolve().parents[2]
        mapping = C._enum_label_map(repo_root)
        for raw in mapping:
            self.assertGreaterEqual(len(raw), 6)
        self.assertNotIn("true", mapping)
        self.assertNotIn("false", mapping)


class TestContextSignature(unittest.TestCase):
    def test_case_fold_absorbs_engine_rewrite(self):
        a = "GetAsTimestamp ( x )"
        b = "GetAsTimeStamp ( x )"
        self.assertNotEqual(C._context_signature(a), C._context_signature(b))
        self.assertEqual(C._context_signature(a, fold_case=True),
                         C._context_signature(b, fold_case=True))


def _snippet_script(path, exit_calc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('<fmxmlsnippet type="FMObjectList"><Step enable="True" id="103" name="Exit Script">'
                    f'<Calculation><![CDATA[{exit_calc}]]></Calculation></Step></fmxmlsnippet>', encoding="utf-8")


class TestAddonVersion(unittest.TestCase):
    def test_version_from_a_quoted_literal(self):
        import xml.etree.ElementTree as ET
        steps = ET.fromstring('<x><Step name="# (comment)"/><Step name="Exit Script">'
                              '<Calculation>"1.2.3"</Calculation></Step></x>').findall("Step")
        self.assertEqual(C._version_from_steps(steps), "1.2.3")
        self.assertIsNone(C._version_from_steps([]))

    def test_current_outdated_and_pasted_per_solution(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp) / "scripts"
            _snippet_script(scripts / "Current" / "agentic-fm - ID 1" / "AGFM Version - ID 20.xml", '"1.0.0"')
            _snippet_script(scripts / "Old" / "agentic-fm - ID 1" / "AGFM Version - ID 20.xml", '"0.9.0"')
            _snippet_script(scripts / "Pasted" / "agentic-fm - ID 1" / "Push Context - ID 4.xml", '""')
            _snippet_script(scripts / "Unrelated" / "Misc - ID 1" / "Hello - ID 1.xml", '""')
            entries = {e["name"]: e for e in C._addon_entries(scripts, Path("/unused"), "1.0.0", ["Push Context", "AGFM Version"])}
        self.assertEqual(entries["add-on (Current)"]["status"], "OK")
        self.assertEqual(entries["add-on (Old)"]["status"], "STALE")
        self.assertEqual(entries["add-on (Old)"]["diff"], "0.9.0 → 1.0.0")
        self.assertEqual(entries["add-on (Pasted)"]["status"], "PASTED")
        self.assertNotIn("add-on (Unrelated)", entries)

    def test_no_bundle_version_means_no_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(C._addon_entries(Path(tmp), Path("/unused"), None, ["Push Context"]), [])


class TestManifestScope(unittest.TestCase):
    BUNDLE = ('<fmxmlsnippet type="FMObjectList"><Group id="1" name="agentic-fm">'
              '<Script id="20" name="AGFM Version"><Step enable="True" id="103" name="Exit Script">'
              '<Calculation><![CDATA["1.0.0"]]></Calculation></Step></Script>'
              '<Script id="9" name="Agentic-fm Webviewer"><Step enable="True" id="103" name="Exit Script"/></Script>'
              '</Group></fmxmlsnippet>')

    def _repo(self, tmp, with_manifest):
        root = Path(tmp)
        (root / "filemaker" / "addon").mkdir(parents=True)
        (root / "filemaker" / "agentic-fm.xml").write_text(self.BUNDLE, encoding="utf-8")
        if with_manifest:
            (root / "filemaker" / "addon" / "manifest.json").write_text(
                '{"name": "agentic-fm", "version": "1.0.0", "scripts": ["AGFM Version"], "custom_functions": []}',
                encoding="utf-8")
        _snippet_script(root / "agent" / "xml_parsed" / "scripts" / "Demo" / "agentic-fm - ID 1" / "AGFM Version - ID 20.xml",
                        '"1.0.0"')
        return root

    def test_manifest_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(C._manifest_scripts(self._repo(tmp, True)), {"AGFM Version"})
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(C._manifest_scripts(self._repo(tmp, False)))

    def test_scripts_outside_the_add_on_are_not_missing_where_the_add_on_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = {o["name"]: o["status"] for o in C.check(self._repo(tmp, True))["objects"]}
        self.assertNotIn("Agentic-fm Webviewer", names)
        self.assertEqual(names["add-on (Demo)"], "OK")

    def test_without_a_manifest_they_are_still_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = {o["name"]: o["status"] for o in C.check(self._repo(tmp, False))["objects"]}
        self.assertEqual(names["Agentic-fm Webviewer"], "MISSING")


class TestSaveAsXmlEngineOptions(unittest.TestCase):
    CANON = "Set Variable [ $o ; Value: 1 ]\nSave a Copy as XML [ $output ; Get ( WindowName ) ]\nExit Script"
    EMB = ('Set Variable [ $o ; Value: 1 ]\nSave a Copy as XML [ $output ; Get ( WindowName ) ; '
           'Specify options as JSON: JSONSetElement ( "{}" ;\n  [ "catalogs_included" ; JSONMakeArray (\n'
           '  "ScriptCatalog\n  Metadata"\n  ; " " ; JSONString ) ; JSONArray ] ;\n'
           '  [ "include_details" ; False ; JSONBoolean ]\n) ]\nExit Script')

    def test_options_added_by_filemaker_26_on_paste_are_noise(self):
        status, diff = C._compare_hr(self.CANON, self.EMB)
        self.assertEqual(status, "OK~")
        self.assertIn("Specify options as JSON", diff)

    def test_other_changes_next_to_the_options_still_drift(self):
        status, _ = C._compare_hr(self.CANON, self.EMB.replace("Exit Script", "Exit Script [ 1 ]"))
        self.assertEqual(status, "STALE")

    def test_options_in_the_bundle_are_compared_normally(self):
        canon = self.EMB.replace("ScriptCatalog", "LayoutCatalog")
        status, _ = C._compare_hr(canon, self.EMB)
        self.assertEqual(status, "STALE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
