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


if __name__ == "__main__":
    unittest.main(verbosity=2)
