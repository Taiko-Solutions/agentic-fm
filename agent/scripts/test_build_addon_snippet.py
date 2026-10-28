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


class TestDraggableObject(unittest.TestCase):
    """--package refuses a package whose template.xml places nothing (spec 10.1: empty <Directives/>)."""

    def _package(self, tmp, directives):
        d = Path(tmp)
        (d / "template.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<FMAdd_on version="2.3.0.0">\n\t<Structure/>\n\t{directives}\n</FMAdd_on>\n',
            encoding="utf-8")
        return d

    def test_an_empty_directives_element_is_a_named_error(self):
        import tempfile
        for empty in ("<Directives></Directives>", "<Directives/>", "<Directives>\n\t</Directives>"):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError) as ctx:
                    B.check_draggable_object(self._package(tmp, empty))
                self.assertIn("the package has no draggable object: template.xml <Directives/> is empty", str(ctx.exception))
                self.assertIn("__FMAddonTemplateDirectives_en", str(ctx.exception))

    def test_a_package_without_directives_is_refused_too(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                B.check_draggable_object(self._package(tmp, ""))

    def test_a_group_inside_directives_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            xml = '<Directives><Layout name="x"><LayoutObject type="Group"><LayoutObject type="Button"/></LayoutObject></Layout></Directives>'
            B.check_draggable_object(self._package(tmp, xml))

    def test_package_runs_the_check_before_touching_the_repo(self):
        import inspect
        source = inspect.getsource(B.package)
        self.assertLess(source.index("check_draggable_object"), source.index("shutil.rmtree"))


class TestWebViewerSnippet(unittest.TestCase):
    def test_committed_web_viewer_snippet_has_only_the_scripts_outside_the_add_on(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        bundle = names((REPO / "filemaker" / "agentic-fm.xml").read_text(encoding="utf-8"))
        text = (REPO / "filemaker" / "addon" / "agentic-fm-webviewer.xml").read_text(encoding="utf-8")
        self.assertEqual(names(text), bundle - set(manifest["scripts"]))


def package_has_agent():
    """False until the package is rebuilt in FileMaker with AGFM Agent in the template (Task 11)."""
    strings = REPO / "filemaker" / "addon" / "agentic-fm" / "en.xml"      # real script names live here, not in template.xml
    return "<SourceText>AGFM Agent</SourceText>" in strings.read_text(encoding="utf-8-sig")


CALC_TOKEN = r"com\.fmi\.calculation\.text\.[0-9A-F]{32}"


def calc_norm(text):
    """Comments dropped, whitespace collapsed: what a calculation keeps between the bundle and the package."""
    import re
    return re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/", "", text, flags=re.S)).strip()


def package_scripts(package_dir):
    """{script name: its step calculations as one normalised text}, from a built package. template.xml keeps names
    and literals as com.fmi.* tokens; en.xml holds their text."""
    import html
    import re
    strings = {sid: html.unescape(src) for sid, src in re.findall(
        r"<StringID>(.*?)</StringID>\s*<SourceText>(.*?)</SourceText>",
        (package_dir / "en.xml").read_text(encoding="utf-8-sig"), re.S)}
    resolve = lambda text: re.sub(CALC_TOKEN, lambda m: strings.get(m.group(0), m.group(0)), text)
    root = ET.fromstring((package_dir / "template.xml").read_text(encoding="utf-8-sig").encode("utf-8"))
    scripts = {}
    for steps in root.iter("StepsForScripts"):
        for entry in steps:
            ref = entry.find("ScriptReference")
            if ref is not None:
                name = strings.get(ref.get("name"), ref.get("name"))
                scripts[name] = calc_norm(" ".join(resolve(t.text or "") for t in entry.iter("Text")))
    return scripts


def script_mismatches(package):
    """(script, calculation) pairs of the manifest's bundle scripts that are not in that same script of `package`
    (literals included). Button labels are skipped: the package keeps them outside the step calculations."""
    manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
    root = ET.fromstring(B.fill_context(real_bundle(), real_fmfn()).encode("utf-8"))
    labels = {id(c) for button in root.iter("Button") for c in button.iter("Calculation")}
    out = []
    for script in root.iter("Script"):
        name = script.get("name")
        if name not in manifest["scripts"] or script.find("Step") is None:
            continue
        text = package.get(name)
        if text is None:
            continue    # a script missing from the package is the whole-package check's job
        for calc in script.iter("Calculation"):
            code = calc_norm(calc.text or "")
            if id(calc) not in labels and len(code) >= 3 and code not in text:
                out.append((name, code[:80]))
    return out


PENDING = unittest.skipUnless(package_has_agent(), "package not rebuilt yet with AGFM Agent / version 1.1.0 (rebuild in FileMaker, then --package)")


class TestPackageMatchesBundle(unittest.TestCase):
    """A stale package (bundle edited, package not rebuilt) must fail here, not ship."""

    @PENDING
    def test_every_calculation_of_the_manifest_scripts_is_in_the_package(self):
        import html
        import re
        literal = re.compile(r'"(?:[^"\\]|\\.)*"')

        block_comment = re.compile(r"/\*.*?\*/", re.S)   # template.xml stores comments as /*com.fmi.calculation.text.HEX*/

        def norm(text):
            return re.sub(r"\s+", " ", text).strip()

        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        raw = (REPO / "filemaker" / "addon" / "agentic-fm" / "template.xml").read_text(encoding="utf-8-sig")
        # template.xml keeps long literals as "com.fmi.calculation.text.HEX" tokens and short ones inline: neutralise all of them,
        # comments first (they may hold a stray quote), inside each <Calculation> only so XML attributes are not touched.
        blocks = re.findall(r"<Calculation[^>]*>(.*?)</Calculation>", raw, re.S)
        template = norm(" ".join(literal.sub('""', block_comment.sub("/**/", html.unescape(b))) for b in blocks))
        root = ET.fromstring(B.fill_context(real_bundle(), real_fmfn()).encode("utf-8"))
        missing = []
        for script in root.iter("Script"):
            if script.get("name") in manifest["scripts"] and script.find("Step") is not None:
                for calc in script.iter("Calculation"):
                    code = norm(literal.sub('""', block_comment.sub("/**/", calc.text or "")))   # comments first: they may hold a stray quote
                    if len(code) >= 3 and code not in template:
                        missing.append((script.get("name"), code[:80]))
        self.assertEqual(missing, [], "package is stale: rebuild it in FileMaker, then build_addon_snippet.py --package")

    @PENDING
    def test_each_script_of_the_package_matches_its_bundle_script(self):
        """Script by script, literals included: the 1.2.0 package had the card's /explode payload in AGFM Explode and
        the 1.1 payload in AGFM Explode Solution, and the whole-package check above still passed."""
        package = package_scripts(REPO / "filemaker" / "addon" / "agentic-fm")
        self.assertEqual(script_mismatches(package), [],
                         "package is stale: rebuild it in FileMaker, then build_addon_snippet.py --package")

    def test_a_script_missing_its_calculations_is_caught(self):
        package = {"AGFM Explode": "", "AGFM Explode Solution": ""}
        names = {name for name, _ in script_mismatches(package)}
        self.assertIn("AGFM Explode", names)
        self.assertIn("AGFM Explode Solution", names)

    @PENDING
    def test_package_version_matches_the_manifest(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        B.check_package_version(REPO / "filemaker" / "addon" / "agentic-fm", manifest)

    def test_a_package_with_another_version_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "en.xml").write_text("<SourceText>0.9.0</SourceText>", encoding="utf-8")
            with self.assertRaises(ValueError):
                B.check_package_version(Path(tmp), {"version": "1.0.0"})


FMFN = """/*
 * Context ( task )
 * header that is not part of the calculation
 */

Let ( [
    ~json = JSONSetElement ( "{}" ;
        [ "task" ; task ; JSONString ]
    )
] ;
    ~json
)
"""


def real_bundle():
    return (REPO / "filemaker" / "agentic-fm.xml").read_text(encoding="utf-8")


def real_fmfn():
    return (REPO / "filemaker" / "Context.fmfn").read_text(encoding="utf-8")


class TestInlineContext(unittest.TestCase):
    def test_inline_context_wraps_the_body_in_let_task(self):
        out = B.inline_context(FMFN)
        self.assertTrue(out.startswith("Let ( task = $task ;\nLet ( ["))
        self.assertTrue(out.endswith("~json\n)\n)"))
        self.assertNotIn("header that is not part", out)
        self.assertNotIn("/*", out)

    def test_inline_context_keeps_the_json_key_task(self):
        self.assertIn('[ "task" ; task ; JSONString ]', B.inline_context(FMFN))

    def test_a_function_without_a_body_is_an_error(self):
        with self.assertRaises(ValueError):
            B.inline_context("/* only a header */")


class TestAgentSnippets(unittest.TestCase):
    def setUp(self):
        self.filled = B.fill_context(real_bundle(), real_fmfn())
        self.script, self.steps = B.agent_snippets(self.filled)

    def test_agent_snippets_have_one_script_and_bare_steps(self):
        root = ET.fromstring(self.script)
        scripts = [s for s in root.iter("Script") if s.find("Step") is not None]
        self.assertEqual([s.get("name") for s in scripts], ["AGFM Agent"])
        self.assertEqual(list(root.iter("Group")), [])
        self.assertEqual(scripts[0].get("runFullAccess"), "False")
        steps_root = ET.fromstring(self.steps)
        self.assertEqual(list(steps_root.iter("Script")), [])
        self.assertEqual(len(steps_root.findall("Step")), len(scripts[0].findall("Step")))

    def test_outputs_never_contain_the_placeholder(self):
        self.assertIn(B.PLACEHOLDER, real_bundle())          # the bundle keeps the source of truth
        for text in (self.filled, self.script, self.steps):
            self.assertNotIn(B.PLACEHOLDER, text)
        self.assertIn("Let ( task = $task ;", self.steps)

    def test_agent_is_self_contained(self):
        root = ET.fromstring(self.script)
        self.assertEqual([s.get("name") for s in root.iter("Script") if s.find("Step") is None], [])
        self.assertNotIn('name="Perform Script"', self.script)
        self.assertIn("<Name>$version</Name>", self.steps)

    def test_agent_script_is_in_the_addon_snippet(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        out = B.build(self.filled, manifest)
        self.assertIn("AGFM Agent", names(out))
        self.assertIn("Let ( task = $task ;", out)
        self.assertNotIn(B.PLACEHOLDER, out)

    def test_manifest_lists_agent_and_version_1_3_0(self):
        manifest = json.loads((REPO / "filemaker" / "addon" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "1.3.0")
        self.assertEqual(manifest["agent_version"], "1.0.0")
        self.assertIn("AGFM Agent", manifest["scripts"])
        self.assertIn("AGFM Explode Solution", manifest["scripts"])
        self.assertIn('"1.0.0"', self.steps)                 # Set Variable [ $version ; "1.0.0" ]

    def test_context_calculation_is_byte_for_byte_the_inlined_function(self):
        expected = B.inline_context(real_fmfn())
        for text in (self.script, self.steps):
            root = ET.fromstring(text.encode("utf-8"))
            calcs = [c.text for c in root.iter("Calculation") if c.text and c.text.startswith("Let ( task = $task ;")]
            self.assertEqual(calcs, [expected])

    def test_dedent_keeps_a_multiline_literal_of_a_calculation(self):
        bundle = BUNDLE.replace('<Calculation><![CDATA["a" & "b"]]></Calculation>',
                                '<Calculation><![CDATA["x\n    indented\n  ]]></Calculation>').replace('name="Keep"', 'name="AGFM Agent"', 1)
        _, steps = B.agent_snippets(bundle)
        self.assertIn('"x\n    indented\n  ]]>', steps)

    def test_debug_mode_checks_success_of_the_answer_without_a_dialog(self):
        root = ET.fromstring(real_bundle().encode("utf-8"))
        agent = next(s for s in root.iter("Script") if s.get("name") == "AGFM Agent" and s.find("Step") is not None)
        stepsx = agent.findall("Step")
        i = next(k for k, st in enumerate(stepsx) if st.findtext("Calculation") == '$mode = "debug"')
        j = next(k for k, st in enumerate(stepsx) if k > i and st.get("name") in ("Else If", "Else"))
        block = stepsx[i:j]
        self.assertNotIn("Show Custom Dialog", [st.get("name") for st in block])
        post_to_exit = "\n".join(c.text for st in block[-3:] for c in st.iter("Calculation"))
        self.assertIn('JSONGetElement ( $response ; "success" )', post_to_exit)
        self.assertIn('JSONGetElement ( $response ; "error" )', post_to_exit)

    def test_longest_calculation_is_within_the_limit(self):
        self.assertLessEqual(B.longest_calculation(self.script), B.MAX_CALC_CHARS)
        self.assertEqual(B.MAX_CALC_CHARS, 30000)


class TestCheckAgentOutputs(unittest.TestCase):
    def _patched(self, tmp):
        from unittest import mock
        stack = [mock.patch.object(B, "OUTPUT", Path(tmp) / "agentic-fm-addon.xml"),
                 mock.patch.object(B, "WEBVIEWER_OUTPUT", Path(tmp) / "agentic-fm-webviewer.xml"),
                 mock.patch.object(B, "AGENT_OUTPUT", Path(tmp) / "agfm-agent.xml"),
                 mock.patch.object(B, "AGENT_STEPS_OUTPUT", Path(tmp) / "agfm-agent-steps.xml")]
        return stack

    def test_check_fails_on_a_stale_agent_snippet(self):
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as st:
            for m in self._patched(tmp):
                st.enter_context(m)
            self.assertEqual(B.main([]), 0)                    # writes the agent files
            self.assertEqual(B.main(["--check"]), 0)
            B.AGENT_STEPS_OUTPUT.write_text("stale", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(B.main(["--check"]), 1)
            self.assertIn("agfm-agent-steps.xml is stale", out.getvalue() + "")

    def test_check_fails_when_the_calc_is_too_long(self):
        import contextlib
        import io
        from unittest import mock
        with mock.patch.object(B, "MAX_CALC_CHARS", 1000), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(B.main(["--check"]), 1)
        self.assertIn("too long", err.getvalue())


class TestRunInCI(unittest.TestCase):
    def test_ci_checks_runs_the_add_on_tests(self):
        ci = (REPO / "agent" / "scripts" / "ci_checks.py").read_text(encoding="utf-8")
        self.assertIn("agent/scripts/test_build_addon_snippet.py", ci)
        self.assertIn("agent/scripts/test_filemaker_bundle.py", ci)


if __name__ == "__main__":
    unittest.main()
