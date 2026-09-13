"""Tests for C003 (known-function) — dotted custom function names.

Custom functions with a namespace prefix (`transaction.SetError`,
`error.Throw`) must be extracted as ONE name. Previously the `\\b` word
boundary matched right after the dot, so only the suffix (`SetError`) was
reported, and adding the real CF name to `extra_known_functions` could
never silence the warning.

Run:  python3 -m unittest agent.fmlint.tests.test_known_function
"""

import unittest
from pathlib import Path

from ..engine import LintRunner

REPO_ROOT = Path(__file__).resolve().parents[3]

WRAP = '<fmxmlsnippet type="FMObjectList">{}</fmxmlsnippet>'

STEP = (
    '<Step enable="True" id="141" name="Set Variable">'
    '<Value><Calculation><![CDATA[{}]]></Calculation></Value>'
    '<Repetition><Calculation><![CDATA[1]]></Calculation></Repetition>'
    '<Name>$x</Name></Step>'
)


class KnownFunctionDottedNameTest(unittest.TestCase):

    def lint(self, calc, extra=None):
        runner = LintRunner(project_root=REPO_ROOT)
        if extra is not None:
            rc = dict(runner.config.rule_configs.get("C003", {}))
            rc["extra_known_functions"] = extra
            runner.config.rule_configs["C003"] = rc
        result = runner.lint(WRAP.format(STEP.format(calc)), fmt="xml")
        return [d.message for d in result.diagnostics if d.rule_id == "C003"]

    def test_dotted_name_reported_whole(self):
        msgs = self.lint("transaction.SetError ( $_ErrorHint )", extra=[])
        self.assertEqual(msgs, ['Unknown function "transaction.SetError" in calculation'])

    def test_dotted_name_recognized_via_config(self):
        msgs = self.lint(
            "error.Throw ( transaction.SetError ( $_ErrorHint ) )",
            extra=["transaction.SetError", "error.Throw"],
        )
        self.assertEqual(msgs, [])

    def test_suffix_alone_does_not_silence_dotted_call(self):
        # Declaring only the suffix must not whitelist a namespaced CF.
        msgs = self.lint("transaction.SetError ( 1 )", extra=["SetError"])
        self.assertEqual(msgs, ['Unknown function "transaction.SetError" in calculation'])

    def test_builtin_calls_still_clean(self):
        msgs = self.lint('JSONSetElement ( "{}" ; "a" ; Get ( LastError ) ; JSONNumber )', extra=[])
        self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
