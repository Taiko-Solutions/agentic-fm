"""Tests for param-fidelity rules X001–X003.

Two layers:
1. Synthetic cases — one per known silent-discard bug (must fire) and the
   corrected form of each (must be clean).
2. Corpus smoke test — every reference example in agent/snippet_examples/
   must produce zero X-family diagnostics (the corpus is ground truth; a
   false positive there means the rule is miscalibrated).

Run:  python3 -m unittest agent.fmlint.tests.test_param_fidelity
"""

import unittest
from pathlib import Path

from ..engine import LintRunner
from ..types import Severity

REPO_ROOT = Path(__file__).resolve().parents[3]

WRAP = '<fmxmlsnippet type="FMObjectList">{}</fmxmlsnippet>'


def x_diags(result):
    """Only the param-fidelity family diagnostics."""
    return [d for d in result.diagnostics if d.rule_id.startswith("X")]


class ParamFidelityTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.runner = LintRunner(project_root=REPO_ROOT)

    def lint(self, inner_xml):
        return self.runner.lint(WRAP.format(inner_xml), fmt="xml")

    # -- X001: alias de elemento declarados en el catálogo ------------------

    def test_x001_accepts_catalog_element_alias(self):
        # FileMaker 2025 escribía <SetLLMAccout> (sic); FM 2026 lo corrigió a
        # <SetLLMAccount>. El catálogo declara la grafía antigua como alias
        # (parentElementAliases) y el conversor lee las dos: X001 no debe marcarla.
        for contenedor in ("SetLLMAccount", "SetLLMAccout"):
            result = self.lint(
                '<Step enable="True" id="212" name="Configure AI Account">'
                f'<{contenedor}><AccountName><Calculation><![CDATA["cuenta"]]></Calculation></AccountName></{contenedor}>'
                '<LLMType value="ChatGPT"/><VerifySSLCertificates state="False"/></Step>'
            )
            x001 = [d.message for d in x_diags(result) if d.rule_id == "X001"]
            self.assertEqual(x001, [], contenedor)

    def test_x001_still_flags_unknown_element(self):
        result = self.lint(
            '<Step enable="True" id="212" name="Configure AI Account">'
            '<SetLLMCuenta><AccountName><Calculation><![CDATA["cuenta"]]></Calculation></AccountName></SetLLMCuenta>'
            '<LLMType value="ChatGPT"/></Step>'
        )
        self.assertTrue(any(d.rule_id == "X001" for d in x_diags(result)))

    # -- X003: FileReference vacío en same-file no es error ---------------

    def test_x003_empty_filereference_same_file_is_not_error(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<FileReference></FileReference>'
            '<Calculation><![CDATA["p"]]></Calculation>'
            '<Script id="12" name="Create Log"/></Step>'
        )
        errors = [d for d in x_diags(result) if d.rule_id == "X003" and d.severity == Severity.ERROR]
        self.assertEqual(errors, [])

    def test_x003_empty_filereference_gives_info(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<FileReference></FileReference>'
            '<Script id="12" name="Create Log"/></Step>'
        )
        infos = [d for d in x_diags(result) if d.rule_id == "X003" and d.severity == Severity.INFO]
        self.assertEqual(len(infos), 1, [(d.rule_id, d.severity, d.message) for d in x_diags(result)])

    def test_x003_crossfile_without_pathlist_still_error(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<FileReference id="10" name="Controller"></FileReference>'
            '<Script id="12" name="Remote"/></Step>'
        )
        self.assertTrue(any(d.rule_id == "X003" for d in x_diags(result)))

    def test_x003_crossfile_path_without_name_is_error(self):
        # Verificado en FileMaker (2026-10): con name="" descarta la ruta al pegar
        # y el paso queda "<unknown> from file: \"\"". No es ruido de mismo archivo.
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<FileReference id="0" name=""><UniversalPathList>file:Otro</UniversalPathList></FileReference>'
            '<Script id="0" name="Remote"/></Step>'
        )
        errors = [d for d in x_diags(result) if d.rule_id == "X003" and d.severity == Severity.ERROR]
        self.assertEqual(len(errors), 1, [(d.rule_id, d.severity, d.message) for d in x_diags(result)])

    def test_x003_crossfile_by_name_with_id_zero_is_ok(self):
        # id="0" + name + ruta: FileMaker resuelve la fuente de datos por nombre al pegar.
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<FileReference id="0" name="Otro"><UniversalPathList>file:Otro</UniversalPathList></FileReference>'
            '<Script id="0" name="Remote"/></Step>'
        )
        self.assertEqual([d for d in x_diags(result) if d.rule_id == "X003"], [])

    # -- X004: orden de hijos en Perform Script ---------------------------

    def test_x004_script_first_is_dead_step(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<Script id="12" name="Create Log"/>'
            '<Calculation><![CDATA["p"]]></Calculation></Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X004"]
        self.assertEqual(len(diags), 1, [d.message for d in x_diags(result)])
        self.assertIn("último", diags[0].message)

    def test_x004_canonical_crossfile_order_clean(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<DisableStepCollapsed state="False"/>'
            '<FileReference id="10" name="Controller"><UniversalPathList>file:OtherFile</UniversalPathList></FileReference>'
            '<Calculation><![CDATA["p"]]></Calculation>'
            '<Script id="12" name="Remote"/></Step>'
        )
        self.assertEqual([d for d in x_diags(result) if d.rule_id == "X004"], [])

    def test_x004_script_only_clean(self):
        result = self.lint('<Step enable="True" id="1" name="Perform Script"><Script id="12" name="X"/></Step>')
        self.assertEqual(x_diags(result), [], [d.message for d in x_diags(result)])

    def test_x004_calculated_with_parameter_like_content(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<Calculated><Calculation><![CDATA[JSONSetElement ( "{}" ; "a" ; 1 ; JSONString )]]></Calculation></Calculated>'
            '<Script id="12" name="Create Log"/></Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X004"]
        self.assertTrue(diags and "by name" in diags[0].message, [d.message for d in x_diags(result)])

    def test_x004_by_name_with_expression_is_warning_not_error(self):
        # Patrón selector/router: el nombre se calcula; no puede ser ERROR (bloquearía el deploy)
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<Calculated><Calculation><![CDATA[Case ( $Modo ; "Alta" ; "Baja" )]]></Calculation></Calculated>'
            '<Calculation><![CDATA["p"]]></Calculation></Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X004"]
        self.assertEqual([d.severity for d in diags], [Severity.WARNING], [d.message for d in diags])

    def test_x004_calculated_and_script_coexist_is_error(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<Calculated><Calculation><![CDATA[$ReturnScript]]></Calculation></Calculated>'
            '<Script id="12" name="Create Log"/></Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X004"]
        self.assertEqual([d.severity for d in diags], [Severity.ERROR], [d.message for d in diags])

    def test_x004_by_name_legit_clean(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<Calculated><Calculation><![CDATA[$ReturnScript]]></Calculation></Calculated>'
            '<Calculation><![CDATA["p"]]></Calculation></Step>'
        )
        self.assertEqual([d for d in x_diags(result) if d.rule_id == "X004"], [])

    # -- X001: unknown param element ------------------------------------

    def test_x001_set_error_capture_wrong_element(self):
        # <State> instead of <Set> → error capture silently stays OFF
        result = self.lint(
            '<Step enable="True" id="86" name="Set Error Capture">'
            '<State state="True"/></Step>'
        )
        diags = x_diags(result)
        self.assertTrue(any(d.rule_id == "X001" and "<State>" in d.message.replace("&lt;", "<")
                            or d.rule_id == "X001" and "State" in d.message
                            for d in diags),
                        f"expected X001 for <State>, got: {[d.message for d in diags]}")

    def test_x001_go_to_record_wrong_elements(self):
        # <Option>/<ExitAfterLast> instead of <RowPageLocation>/<Exit>
        result = self.lint(
            '<Step enable="True" id="16" name="Go to Record/Request/Page">'
            '<Option value="First"/><ExitAfterLast state="True"/></Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X001"]
        self.assertEqual(len(diags), 2,
                         f"expected 2 X001 diags, got: {[d.message for d in diags]}")

    def test_x001_clean_forms_pass(self):
        result = self.lint(
            '<Step enable="True" id="86" name="Set Error Capture">'
            '<Set state="True"/></Step>'
            '<Step enable="True" id="16" name="Go to Record/Request/Page">'
            '<NoInteract state="True"/><Exit state="True"/>'
            '<RowPageLocation value="Next"/></Step>'
        )
        self.assertEqual(x_diags(result), [],
                         f"clean steps flagged: {[d.message for d in x_diags(result)]}")

    def test_x001_editor_collapse_state_is_allowed(self):
        # FileMaker adds <DisableStepCollapsed> to EVERY step copied from the
        # Script Workspace (editor fold state) — it is not a step parameter.
        result = self.lint(
            '<Step enable="True" id="207" name="Revert Transaction">'
            '<Option state="True"/><DisableStepCollapsed state="False"/>'
            '<Condition><Calculation><![CDATA[$_Check]]></Calculation></Condition>'
            '<ErrorCode><Calculation><![CDATA[5499]]></Calculation></ErrorCode>'
            '<ErrorMessage><Calculation><![CDATA[transaction.SetError ( $_ErrorHint )]]>'
            '</Calculation></ErrorMessage></Step>'
            '<Step enable="True" id="86" name="Set Error Capture">'
            '<Set state="True"/><DisableStepCollapsed state="True"/></Step>'
        )
        self.assertEqual([d for d in x_diags(result) if d.rule_id == "X001"], [],
                         f"editor state flagged: {[d.message for d in x_diags(result)]}")

    def test_x001_still_fires_next_to_editor_state(self):
        # The allowlist must not mask real unknown elements on the same step.
        result = self.lint(
            '<Step enable="True" id="86" name="Set Error Capture">'
            '<DisableStepCollapsed state="False"/><State state="True"/></Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X001"]
        self.assertEqual(len(diags), 1, f"got: {[d.message for d in diags]}")
        self.assertIn("State", diags[0].message)

    # -- X002: missing discriminator -------------------------------------

    def test_x002_go_to_layout_without_destination(self):
        result = self.lint(
            '<Step enable="True" id="6" name="Go to Layout">'
            '<Layout id="28" name="Clientes"></Layout></Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X002"]
        self.assertEqual(len(diags), 1,
                         f"expected 1 X002 diag, got: {[d.message for d in x_diags(result)]}")

    def test_x002_go_to_layout_with_destination_passes(self):
        result = self.lint(
            '<Step enable="True" id="6" name="Go to Layout">'
            '<LayoutDestination value="SelectedLayout"/>'
            '<Layout id="28" name="Clientes"></Layout></Step>'
        )
        self.assertEqual([d for d in x_diags(result) if d.rule_id == "X002"], [])

    # -- X003: known silent-discard patterns ------------------------------

    def test_x003_card_without_styles_bitmask(self):
        result = self.lint(
            '<Step enable="True" id="122" name="New Window">'
            '<NewWndStyles DimParentWindow="Yes" Toolbars="No" MenuBar="No" '
            'Style="Card" Close="Yes" Minimize="No" Maximize="No" Resize="No"/>'
            '</Step>'
        )
        diags = [d for d in x_diags(result) if d.rule_id == "X003"]
        self.assertEqual(len(diags), 1,
                         f"expected 1 X003 diag, got: {[d.message for d in x_diags(result)]}")

    def test_x003_card_with_styles_bitmask_passes(self):
        result = self.lint(
            '<Step enable="True" id="122" name="New Window">'
            '<NewWndStyles DimParentWindow="Yes" Toolbars="No" MenuBar="No" '
            'Style="Card" Close="Yes" Minimize="No" Maximize="No" Resize="No" '
            'Styles="3222339600"/></Step>'
        )
        self.assertEqual([d for d in x_diags(result) if d.rule_id == "X003"], [])

    def test_x003_fileref_nested_inside_script(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<Calculation><![CDATA[$param]]></Calculation>'
            '<Script id="1363" name="Some Script">'
            '<FileReference id="10" name="OtherFile"/></Script></Step>'
        )
        msgs = [d.message for d in x_diags(result) if d.rule_id == "X003"]
        self.assertTrue(any("SIBLING" in m for m in msgs),
                        f"expected nested-FileReference diag, got: {msgs}")

    def test_x003_fileref_without_universal_path_list(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<FileReference id="10" name="OtherFile"/>'
            '<Calculation><![CDATA[$param]]></Calculation>'
            '<Script id="1363" name="Some Script"/></Step>'
        )
        msgs = [d.message for d in x_diags(result) if d.rule_id == "X003"]
        self.assertTrue(any("UniversalPathList" in m for m in msgs),
                        f"expected missing-UniversalPathList diag, got: {msgs}")

    def test_x003_crossfile_correct_form_passes(self):
        result = self.lint(
            '<Step enable="True" id="1" name="Perform Script">'
            '<FileReference id="10" name="OtherFile">'
            '<UniversalPathList>file:OtherFile</UniversalPathList>'
            '</FileReference>'
            '<Calculation><![CDATA[$param]]></Calculation>'
            '<Script id="1363" name="Some Script"/></Step>'
        )
        self.assertEqual([d for d in x_diags(result) if d.rule_id == "X003"], [])


class CorpusSmokeTest(unittest.TestCase):
    """Every reference example must be clean of X-family diagnostics."""

    @classmethod
    def setUpClass(cls):
        cls.runner = LintRunner(project_root=REPO_ROOT)

    def test_snippet_examples_corpus_is_clean(self):
        corpus = REPO_ROOT / "agent" / "snippet_examples"
        files = sorted(corpus.rglob("*.xml"))
        self.assertGreater(len(files), 50, "corpus not found or too small")
        failures = []
        for path in files:
            try:
                result = self.runner.lint_file(str(path))
            except Exception as exc:  # malformed reference file — not ours
                failures.append(f"{path.relative_to(corpus)}: lint crashed: {exc}")
                continue
            for d in x_diags(result):
                failures.append(f"{path.relative_to(corpus)}: {d.rule_id} {d.message}")
        self.assertEqual(failures, [],
                         "false positives in reference corpus:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
