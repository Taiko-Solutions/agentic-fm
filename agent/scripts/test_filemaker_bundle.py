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
        self.assertEqual(bundle_version(), "1.2.0")

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


class TestPathCallers(unittest.TestCase):
    CALLERS = ("Explode XML", "Push Context")

    def test_callers_read_ok_from_the_json_and_fall_back_to_the_picker(self):
        for name in self.CALLERS:
            body = steps(name)
            idx = next(i for i, st in enumerate(body) if st.get("name") == "Perform Script"
                       and st.find("Script") is not None and st.find("Script").get("name") == "Get agentic-fm path")
            self.assertEqual(body[idx + 1].findtext("Name"), "$pathResult", name)
            self.assertIn('not JSONGetElement ( $pathResult ; "ok" )', calcs(name), name)
            called = [st.find("Script").get("name") for st in body
                      if st.get("name") == "Perform Script" and st.find("Script") is not None]
            self.assertIn("AGFM Choose Folder", called, name)
            self.assertNotIn("Bad install", "\n".join(calcs(name)), name)


class TestStartAndExplode(unittest.TestCase):
    def test_start_and_explode_are_silent(self):
        for name in ("AGFM Start", "AGFM Explode"):
            self.assertFalse(INTERACTIVE & set(step_names(name)), name)

    def test_start_tells_the_app_from_the_classic_companion(self):
        joined = "\n".join(calcs("AGFM Start"))
        self.assertIn(COMPANION_BASE + '/health"', joined)
        self.assertIn('JSONGetElementType ( $health ; "service" ) = JSONObject', joined)
        self.assertIn('"no_service"', joined)

    def test_explode_runs_start_then_exports_to_the_temporary_folder(self):
        body = steps("AGFM Explode")
        called = [st.find("Script").get("name") for st in body
                  if st.get("name") == "Perform Script" and st.find("Script") is not None]
        self.assertEqual(called[0], "AGFM Start")
        joined = "\n".join(calcs("AGFM Explode"))
        self.assertIn("Get ( TemporaryPath )", joined)
        self.assertIn(COMPANION_BASE + '/explode"', joined)


class TestReviewFixes(unittest.TestCase):
    def test_a_json_answer_without_success_is_no_config(self):
        """The classic companion answers /config with a JSON 404 ({"error": "Not found"}), not with text."""
        self.assertIn('JSONGetElementType ( $response ; "success" ) ≠ JSONBoolean', "\n".join(calcs("Get agentic-fm path")))

    def test_layout_references_use_explicit_close_tags(self):
        self.assertNotRegex(BUNDLE.read_text(encoding="utf-8"), r"<Layout\b[^>]*/>")


MANIFEST = BUNDLE.parent / "addon" / "manifest.json"
WEB_VIEWER_SCRIPTS = {"Agentic-fm Webviewer", "Agentic-fm Menu", "Agentic-fm Paste"}


def manifest():
    import json
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class TestManifest(unittest.TestCase):
    def test_manifest_version_matches_agfm_version(self):
        self.assertEqual(manifest()["version"], bundle_version())

    def test_every_manifest_script_is_in_the_bundle(self):
        for name in manifest()["scripts"]:
            script(name)

    def test_no_web_viewer_part_in_the_add_on(self):
        self.assertFalse(WEB_VIEWER_SCRIPTS & set(manifest()["scripts"]))
        self.assertNotIn("AGFM Open Editor", all_scripts())

    def test_context_is_the_only_custom_function(self):
        self.assertEqual(manifest()["custom_functions"], ["Context"])


class TestExplodeSolution(unittest.TestCase):
    NAME = "AGFM Explode Solution"

    def test_it_is_in_the_add_on_and_not_full_access(self):
        self.assertIn(self.NAME, manifest()["scripts"])
        self.assertEqual(script(self.NAME).get("runFullAccess"), "False")

    def test_without_a_parameter_it_starts_the_service_and_opens_the_card_by_layout_name(self):
        body = steps(self.NAME)
        joined = "\n".join(calcs(self.NAME))
        self.assertEqual(body[0].get("name"), "# (comment)")
        windows = [st for st in body if st.get("name") == "New Window"]
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].find("NewWndStyles").get("Style"), "Card")
        self.assertEqual(windows[0].findtext("Name/Calculation"), '"agentic-fm"')
        goto = [st for st in body if st.get("name") == "Go to Layout"]
        self.assertEqual(goto[0].find("LayoutDestination").get("value"), "LayoutNameByCalc")
        self.assertEqual(goto[0].findtext("Layout/Calculation"), '"AGFM Explode"')
        self.assertIn(COMPANION_BASE + '/addon/card?file=" & GetAsURLEncoded ( Get ( FileName ) )', joined)
        self.assertIn("Falta el layout AGFM Explode", joined)

    def test_files_are_called_by_name_with_the_retry_for_closed_files(self):
        joined = "\n".join(calcs(self.NAME))
        self.assertIn('$dataSource & "::AGFM Agent"', joined)
        self.assertIn("$callError = 104 and not $wasOpen", joined)
        self.assertIn('Get ( TemporaryPath ) & "agfm/" & Get ( UUID ) & "/"', joined)
        by_name = [st for st in steps(self.NAME) if st.get("name") == "Perform Script" and st.find("Calculated") is not None]
        self.assertEqual(len(by_name), 2)

    def test_a_failed_start_only_marks_files_as_errors_for_export(self):
        joined = "\n".join(calcs(self.NAME))
        self.assertIn('$action = "export" and not IsEmpty ( $startError )', joined)
        self.assertNotIn("\n" + "not IsEmpty ( $startError )", "\n" + joined)

    def test_the_start_dialog_translates_the_service_codes(self):
        joined = "\n".join(calcs(self.NAME))
        self.assertIn("agentic-fm-app no responde: ábrela y vuelve a intentarlo.", joined)
        self.assertIn("Registra el clon de este archivo en agentic-fm-app (Proyectos) o elige allí su clon.", joined)
        self.assertIn('= "no_service"', joined)
        self.assertIn('= "unknown_solution"', joined)
        self.assertIn('= "ambiguous_solution"', joined)

    def test_was_open_ignores_case(self):
        joined = "\n".join(calcs(self.NAME))
        self.assertIn('FilterValues ( Lower ( DatabaseNames ) ; Lower ( $base ) & ¶ & Lower ( $base ) & ".fmp12" )', joined)

    def test_it_reports_to_the_card_and_posts_explode(self):
        joined = "\n".join(calcs(self.NAME))
        functions = [st.findtext("FunctionName/Calculation") for st in steps(self.NAME)
                     if st.get("name") == "Perform JavaScript in Web Viewer"]
        self.assertIn('"agfm.progress"', functions)
        self.assertEqual(functions[-1], '"agfm.done"')
        self.assertIn(COMPANION_BASE + '/explode"', joined)
        self.assertIn('"~/bin/fm-xml-export-exploder"', joined)
        self.assertIn('"agentic-fm-app no responde"', joined)

    def test_the_only_dialogs_are_before_the_card_opens(self):
        body = steps(self.NAME)
        loop = next(i for i, st in enumerate(body) if st.get("name") == "Loop")
        self.assertFalse([st for st in body[loop:] if st.get("name") == "Show Custom Dialog"])


def explode_payloads(name):
    """The calculations of the `$payload` variables a script POSTs to /explode."""
    return [st.findtext("Value/Calculation") or "" for st in steps(name)
            if st.get("name") == "Set Variable" and st.findtext("Name") == "$payload"
            and "export_file_path" in (st.findtext("Value/Calculation") or "")]


class TestExplodeCommentAndOrigin(unittest.TestCase):
    """1.2.0: the explode records what the person typed in the card and who triggered it (agentic-fm-app F6b)."""

    def test_the_card_forwards_its_comment_and_says_card(self):
        payloads = explode_payloads("AGFM Explode Solution")
        self.assertTrue(payloads)
        for text in payloads:
            self.assertIn('[ "comment" ; JSONGetElement ( $p ; "comment" ) ; JSONString ]', text)
            self.assertIn('[ "origin" ; "card" ; JSONString ]', text)

    def test_explode_xml_says_explode_xml_and_sends_no_comment(self):
        payloads = explode_payloads("Explode XML")
        self.assertEqual(len(payloads), 2)                      # app path and classic companion path
        for text in payloads:
            self.assertIn('[ "origin" ; "explode-xml" ; JSONString ]', text)
            self.assertNotIn('"comment"', text)


class TestPackage(unittest.TestCase):
    PACKAGE = BUNDLE.parent / "addon" / "agentic-fm"
    # Until the package is rebuilt in FileMaker with AGFM Agent (add-on 1.1.0) the committed package is the old one.
    REBUILT = "<SourceText>AGFM Agent</SourceText>" in (PACKAGE / "en.xml").read_text(encoding="utf-8-sig")

    def _info(self, lang):
        import json
        return json.loads((self.PACKAGE / f"info_{lang}.json").read_text(encoding="utf-8-sig"))

    @unittest.skipUnless(REBUILT, "package not rebuilt yet with AGFM Agent / 1.1.0 (rebuild in FileMaker, then --package)")
    def test_package_title_and_description_carry_the_version(self):
        for lang in ("en", "es"):
            info = self._info(lang)
            self.assertEqual(info["Title"], "agentic-fm")
            self.assertIn(bundle_version(), info["Description"])
            self.assertNotIn("DESCRIPTION MISSING", info["Description"])

    @unittest.skipUnless(REBUILT, "package not rebuilt yet with AGFM Agent / 1.1.0 (rebuild in FileMaker, then --package)")
    def test_package_contains_exactly_the_manifest_scripts(self):
        strings = (self.PACKAGE / "en.xml").read_text(encoding="utf-8-sig")
        for name in manifest()["scripts"]:
            self.assertIn(f"<SourceText>{name}</SourceText>", strings, name)
        for name in WEB_VIEWER_SCRIPTS:
            self.assertNotIn(f"<SourceText>{name}</SourceText>", strings, name)

    def test_package_has_the_card_layout_and_a_draggable_group(self):
        """1.1.0 packages exactly one layout (AGFM Explode) with the Web Viewer `agfm`, plus a draggable group."""
        import re
        template = (self.PACKAGE / "template.xml").read_text(encoding="utf-8-sig")
        strings = (self.PACKAGE / "en.xml").read_text(encoding="utf-8-sig")

        def source_text(token):
            found = re.search(r"<StringID>" + re.escape(token) + r"</StringID>\s*<SourceText>(.*?)</SourceText>", strings, re.S)
            return found.group(1) if found else None

        self.assertIn('<LayoutCatalog membercount="1">', template)
        catalog = template[template.index("<LayoutCatalog"):template.index("</LayoutCatalog>")]
        layout = re.search(r'<Layout id="\d+" name="(com\.fmi\.layout\.[0-9A-Fa-f]+)"', catalog)
        self.assertIsNotNone(layout)
        self.assertEqual(source_text(layout.group(1)), "AGFM Explode")
        viewers = re.findall(r'<LayoutObject [^>]*type="Web Viewer" name="(com\.fmi\.layoutobject\.[0-9A-Fa-f]+)"', catalog)
        self.assertIn("agfm", [source_text(token) for token in viewers])
        directives = template[template.index("<Directives>"):template.index("</Directives>")]
        self.assertRegex(directives, r'<LayoutObject [^>]*type="Group"')

    def test_distributable_archive_exists(self):
        archive = BUNDLE.parent / "addon" / "agentic-fm.fmaddon"
        self.assertTrue(archive.is_file() and archive.stat().st_size > 0)


class TestExplodeErrorDialog(unittest.TestCase):
    def test_explode_xml_shows_the_service_error_when_stderr_is_empty(self):
        """agentic-fm-app's validation errors (400) come in "error", not "stderr": the dialog was blank."""
        self.assertIn('JSONGetElement ( $response ; "error" )', "\n".join(calcs("Explode XML")))


class TestTemplateLocation(unittest.TestCase):
    def test_template_lives_under_addon_and_keeps_the_add_on_name(self):
        """The add-on takes the template file's name, and filemaker/agentic-fm.fmp12 is the upstream full bundle."""
        self.assertTrue((BUNDLE.parent / "addon" / "template" / "agentic-fm.fmp12").is_file())

    def test_upstream_bundle_file_is_not_the_template(self):
        full = (BUNDLE.parent / "agentic-fm.fmp12").read_bytes()
        template = (BUNDLE.parent / "addon" / "template" / "agentic-fm.fmp12").read_bytes()
        self.assertNotEqual(full, template)



class TestWebViewerCallsByName(unittest.TestCase):
    """The web viewer scripts are installed by hand next to the add-on: their calls into the add-on must be by
    name, or an add-on update (uninstall + install) leaves them <unknown>."""

    def _calls(self, name):
        by_ref = [st.find("Script").get("name") for st in steps(name)
                  if st.get("name") == "Perform Script" and st.find("Script") is not None]
        by_name = [st.findtext("Calculated/Calculation") for st in steps(name)
                   if st.get("name") == "Perform Script" and st.find("Calculated") is not None]
        return by_ref, by_name

    def test_web_viewer_scripts_call_add_on_scripts_by_name_only(self):
        addon = set(manifest()["scripts"])
        for name in WEB_VIEWER_SCRIPTS:
            by_ref, by_name = self._calls(name)
            self.assertFalse(addon & set(by_ref), name)
        _, by_name = self._calls("Agentic-fm Webviewer")
        self.assertIn('"Get agentic-fm path"', by_name)
        self.assertIn('"AGFM Choose Folder"', by_name)
        self.assertIn('not JSONGetElement ( $pathResult ; "ok" )', calcs("Agentic-fm Webviewer"))


if __name__ == "__main__":
    unittest.main()
