#!/usr/bin/env python3
"""
test_fm_xml_to_snippet.py - Unit tests for the SaXML → fmxmlsnippet translator.

Usage:
    python3 agent/scripts/test_fm_xml_to_snippet.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fm_xml_to_snippet import translate_script


def _saxml(steps_xml: str) -> str:
    """Wrap raw <Step> XML in the minimal SaXML document structure."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<FMSaveAsXML>\n'
        '  <Structure>\n'
        '    <AddAction>\n'
        '      <StepsForScripts>\n'
        '        <Script>\n'
        f'          <ObjectList>\n{steps_xml}\n</ObjectList>\n'
        '        </Script>\n'
        '      </StepsForScripts>\n'
        '    </AddAction>\n'
        '  </Structure>\n'
        '</FMSaveAsXML>\n'
    )


def _translate(steps_xml: str) -> str:
    with tempfile.NamedTemporaryFile(
        'w', suffix='.xml', encoding='utf-8', delete=False
    ) as f:
        f.write(_saxml(steps_xml))
        tmp = Path(f.name)
    try:
        return translate_script(tmp)
    finally:
        tmp.unlink()


# Real-world SaXML shape for Revert Transaction with all 5 parameters,
# as produced by FileMaker Save As XML.
REVERT_TX_FULL = '''\
<Step hash="0" id="207" name="Revert Transaction" enable="True">
    <Options>17152</Options>
    <ParameterValues membercount="5">
        <Parameter type="Boolean">
            <Boolean type="Condition" id="256" value="True"></Boolean>
        </Parameter>
        <Parameter type="Condition">
            <Calculation datatype="7" position="0">
                <Calculation>
                    <Text><![CDATA[$_Check]]></Text>
                </Calculation>
            </Calculation>
        </Parameter>
        <Parameter type="Boolean">
            <Boolean type="Error Code" id="512" value="True"></Boolean>
        </Parameter>
        <Parameter type="ErrorCode">
            <Calculation datatype="2" position="1">
                <Calculation>
                    <Text><![CDATA[5499]]></Text>
                </Calculation>
            </Calculation>
        </Parameter>
        <Parameter type="ErrorMessage">
            <Calculation datatype="1" position="2">
                <Calculation>
                    <Text><![CDATA[transaction.SetError ( $_ErrorHint )]]></Text>
                </Calculation>
            </Calculation>
        </Parameter>
    </ParameterValues>
</Step>'''


class TestRevertTransaction(unittest.TestCase):

    def test_full_form_emits_all_parameters(self):
        out = _translate(REVERT_TX_FULL)
        self.assertIn('<Step enable="True" id="207" name="Revert Transaction">', out)
        self.assertIn('<Option state="True"/>', out)
        self.assertIn(
            '<Condition>\n      <Calculation><![CDATA[$_Check]]></Calculation>\n'
            '    </Condition>',
            out,
        )
        self.assertIn(
            '<ErrorCode>\n      <Calculation><![CDATA[5499]]></Calculation>\n'
            '    </ErrorCode>',
            out,
        )
        self.assertIn(
            '<ErrorMessage>\n      <Calculation>'
            '<![CDATA[transaction.SetError ( $_ErrorHint )]]></Calculation>\n'
            '    </ErrorMessage>',
            out,
        )

    def test_full_form_is_not_self_closing(self):
        out = _translate(REVERT_TX_FULL)
        self.assertNotIn('name="Revert Transaction"/>', out)

    def test_bare_step_emits_option_false(self):
        bare = '<Step id="207" name="Revert Transaction" enable="True"></Step>'
        out = _translate(bare)
        self.assertIn('<Option state="False"/>', out)
        self.assertNotIn('<Condition>', out)
        self.assertNotIn('<ErrorCode>', out)
        self.assertNotIn('<ErrorMessage>', out)


OPEN_TX = '''\
<Step id="205" name="Open Transaction" enable="True">
    <ParameterValues membercount="4">
        <Parameter type="Boolean">
            <Boolean type="Collapsed" id="33554432" value="False"></Boolean>
        </Parameter>
        <Parameter type="Boolean">
            <Boolean type="Skip auto-enter options" id="4096" value="True"></Boolean>
        </Parameter>
        <Parameter type="Boolean">
            <Boolean type="Skip data entry validation" id="256" value="False"></Boolean>
        </Parameter>
        <Parameter type="Boolean">
            <Boolean type="Override ESS locking conflicts" id="512" value="True"></Boolean>
        </Parameter>
    </ParameterValues>
</Step>'''


class TestOpenTransaction(unittest.TestCase):

    def test_booleans_bind_by_type_not_position(self):
        out = _translate(OPEN_TX)
        # Element order per snippet example: Option, ESSForceCommit,
        # SkipAutoEntry, Restore.
        self.assertIn(
            '<Step enable="True" id="205" name="Open Transaction">\n'
            '    <Option state="False"/>\n'
            '    <ESSForceCommit state="True"/>\n'
            '    <SkipAutoEntry state="True"/>\n'
            '    <Restore state="False"/>\n'
            '  </Step>',
            out,
        )


PSOS_FROM_LIST = '''\
<Step id="164" name="Perform Script on Server" enable="True">
    <Options>16704</Options>
    <ParameterValues membercount="3">
        <Parameter type="List">
            <List name="From list" value="1">
                <ScriptReference id="123" name="Solution Script"></ScriptReference>
            </List>
        </Parameter>
        <Parameter type="Parameter">
            <Parameter>
                <Calculation datatype="1" position="0">
                    <Calculation>
                        <Text><![CDATA[$param]]></Text>
                    </Calculation>
                </Calculation>
            </Parameter>
        </Parameter>
        <Parameter type="Boolean">
            <Boolean type="Wait for completion" id="256" value="False"></Boolean>
        </Parameter>
    </ParameterValues>
</Step>'''


class TestPerformScriptOnServer(unittest.TestCase):

    def test_from_list_keeps_script_parameter(self):
        out = _translate(PSOS_FROM_LIST)
        self.assertIn('<WaitForCompletion state="False"/>', out)
        self.assertIn('<Calculation><![CDATA[$param]]></Calculation>', out)
        self.assertIn('<Script id="123" name="Solution Script"/>', out)


if __name__ == '__main__':
    unittest.main()
