#!/usr/bin/env python3
"""analyze.py must read custom functions from custom_functions/ (exploder ≥ 0.6.1) or custom_function_stubs/ (0.5.1)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402

CF = ('<?xml version="1.0" encoding="UTF-8"?>\n<CustomFunction access="All" id="1" name="FormatMoney">'
      '<Calculation><Text><![CDATA[Round ( amount ; 2 )]]></Text></Calculation>'
      '<ObjectList membercount="1"><Parameter name="amount"/></ObjectList></CustomFunction>\n')


class TestCustomFunctionLayouts(unittest.TestCase):
    def _run(self, stub_folder):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = Path(tmp)
            (parsed / "custom_functions_sanitized" / "Demo").mkdir(parents=True)
            (parsed / "custom_functions_sanitized" / "Demo" / "FormatMoney - ID 1.txt").write_text("Round ( amount ; 2 )\n")
            (parsed / stub_folder / "Demo").mkdir(parents=True)
            (parsed / stub_folder / "Demo" / "FormatMoney - ID 1.xml").write_text(CF)
            old = A.XML_PARSED_DIR
            A.XML_PARSED_DIR = parsed
            try:
                return A.analyze_custom_functions("Demo")
            finally:
                A.XML_PARSED_DIR = old

    def test_new_layout_custom_functions(self):
        self.assertEqual(self._run("custom_functions")["total"], 1)

    def test_legacy_layout_custom_function_stubs(self):
        self.assertEqual(self._run("custom_function_stubs")["total"], 1)


if __name__ == "__main__":
    unittest.main()
