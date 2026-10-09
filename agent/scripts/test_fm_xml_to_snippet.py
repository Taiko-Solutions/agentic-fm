#!/usr/bin/env python3
"""
test_fm_xml_to_snippet.py - Unit tests for the SaXML → fmxmlsnippet translator.

Usage:
    python3 agent/scripts/test_fm_xml_to_snippet.py
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_REPO = Path(__file__).resolve().parents[2]

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


# Send Mail as FileMaker 2026 serializes it: the dialog flag is <Boolean type="With dialog">.
# value="True" means the mail client opens the message for review (NoInteract=False).
def _send_mail(dialog_type: str, value: str) -> str:
    return f'''\
<Step hash="0" id="63" name="Send Mail" enable="True">
    <Options>16416</Options>
    <ParameterValues membercount="1">
        <Parameter type="Email">
            <Boolean type="{dialog_type}" position="159" value="{value}"></Boolean>
            <Send OAuthAuthentication="False" SMTP="False">
                <Multiple value="False"></Multiple>
                <To>
                    <CollectAddresses value="False"></CollectAddresses>
                    <Calculation datatype="1" position="0"><Calculation><Text><![CDATA[$to]]></Text></Calculation></Calculation>
                </To>
                <Subject><Calculation datatype="1" position="3"><Calculation><Text><![CDATA["Asunto"]]></Text></Calculation></Calculation></Subject>
                <Message><Calculation datatype="1" position="4"><Calculation><Text><![CDATA["Cuerpo"]]></Text></Calculation></Calculation></Message>
            </Send>
        </Parameter>
    </ParameterValues>
</Step>'''


class TestSendMailDialog(unittest.TestCase):

    def test_with_dialog_true_opens_message(self):
        out = _translate(_send_mail("With dialog", "True"))
        self.assertIn('<NoInteract state="False"/>', out)

    def test_with_dialog_false_goes_to_outbox(self):
        out = _translate(_send_mail("With dialog", "False"))
        self.assertIn('<NoInteract state="True"/>', out)

    def test_legacy_no_dialog_true_goes_to_outbox(self):
        out = _translate(_send_mail("No dialog", "True"))
        self.assertIn('<NoInteract state="True"/>', out)


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


# Real SaXML shapes (FileMaker Save As XML, 2026), with generic names.
# Go to Layout whose destination is a calculation holding a quoted literal: the
# shape behind the <BROKEN REFERENCE> pastes in a client project (2026-10).
GO_TO_LAYOUT_CALC_LITERAL = '''\
<Step hash="0" id="6" name="Go to Layout" enable="True">
    <Options>16394</Options>
    <ParameterValues membercount="2">
        <Parameter type="LayoutReferenceContainer">
            <LayoutReferenceContainer value="3">
                <Calculation datatype="1" position="5">
                    <Calculation>
                        <Text><![CDATA["Proc_Notes"]]></Text>
                    </Calculation>
                </Calculation>
            </LayoutReferenceContainer>
        </Parameter>
        <Parameter type="Animation">
            <Animation name="None" value="0"></Animation>
        </Parameter>
    </ParameterValues>
</Step>'''

GO_TO_LAYOUT_SELECTED = '''\
<Step hash="0" id="6" name="Go to Layout" enable="True">
    <Options>10</Options>
    <ParameterValues membercount="2">
        <Parameter type="LayoutReferenceContainer">
            <LayoutReferenceContainer value="5">
                <LayoutReference id="304" name="Proc_Notes"></LayoutReference>
            </LayoutReferenceContainer>
        </Parameter>
        <Parameter type="Animation">
            <Animation name="None" value="0"></Animation>
        </Parameter>
    </ParameterValues>
</Step>'''

PERFORM_SCRIPT_FROM_LIST = '''\
<Step hash="0" id="1" name="Perform Script" enable="True">
    <Options>16448</Options>
    <ParameterValues membercount="2">
        <Parameter type="List">
            <List name="From list" value="1">
                <ScriptReference id="805" name="Find Record"></ScriptReference>
            </List>
        </Parameter>
        <Parameter type="Parameter">
            <Parameter>
                <Calculation datatype="1" position="0">
                    <Calculation>
                        <Text><![CDATA[JSONSetElement ( "{}" ; "id" ; $id ; JSONString )]]></Text>
                    </Calculation>
                </Calculation>
            </Parameter>
        </Parameter>
    </ParameterValues>
</Step>'''

PERFORM_SCRIPT_BY_NAME = '''\
<Step id="1" name="Perform Script" enable="True">
    <Options>33572864</Options>
    <ParameterValues membercount="2">
        <Parameter type="List">
            <List name="By name" value="2">
                <Calculation datatype="1" position="2">
                    <Calculation>
                        <Text>$scriptName</Text>
                    </Calculation>
                </Calculation>
            </List>
        </Parameter>
        <Parameter type="Parameter">
            <Parameter>
                <Calculation datatype="1" position="0">
                    <Calculation>
                        <Text>$param</Text>
                    </Calculation>
                </Calculation>
            </Parameter>
        </Parameter>
    </ParameterValues>
</Step>'''

PERFORM_SCRIPT_CROSS_FILE = '''\
<Step hash="0" id="1" name="Perform Script" enable="True">
    <Options>16464</Options>
    <ParameterValues membercount="2">
        <Parameter type="List">
            <List name="From list" value="1">
                <DataSourceReference id="10" name="Controller" />
                <ScriptReference id="586" name="Invoices | Save" />
            </List>
        </Parameter>
        <Parameter type="Parameter">
            <Parameter>
                <Calculation datatype="1" position="0">
                    <Calculation>
                        <Text>$json</Text>
                    </Calculation>
                </Calculation>
            </Parameter>
        </Parameter>
    </ParameterValues>
</Step>'''


def _lint(snippet: str) -> list[dict]:
    """Run fmlint (tier 1) over a snippet and return its diagnostics."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'out.xml'
        f.write_text(snippet, encoding='utf-8')
        res = subprocess.run(
            [sys.executable, '-m', 'agent.fmlint', '--tier', '1', '--format', 'json', str(f)],
            cwd=_REPO, capture_output=True, text=True,
        )
    return [x for r in json.loads(res.stdout)['files'] for x in r['diagnostics']]


def _rules(diags: list[dict], *ids: str) -> list[dict]:
    return [x for x in diags if x['rule_id'] in ids and x['severity'] != 'info']


class TestGoToLayout(unittest.TestCase):

    def test_calc_literal_stays_by_calculation(self):
        out = _translate(GO_TO_LAYOUT_CALC_LITERAL)
        self.assertIn('<LayoutDestination value="LayoutNameByCalc"/>', out)
        self.assertIn('<Calculation><![CDATA["Proc_Notes"]]></Calculation>', out)
        # Never a by-name reference without id (pastes as <BROKEN REFERENCE>).
        self.assertNotIn('<Layout name=', out)

    def test_selected_layout_keeps_id(self):
        out = _translate(GO_TO_LAYOUT_SELECTED)
        self.assertIn('<LayoutDestination value="SelectedLayout"/>', out)
        self.assertIn('<Layout id="304" name="Proc_Notes"/>', out)

    def test_fmlint_clean(self):
        for saxml in (GO_TO_LAYOUT_CALC_LITERAL, GO_TO_LAYOUT_SELECTED):
            self.assertEqual(_rules(_lint(_translate(saxml)), 'X001', 'X002'), [])


class TestPerformScript(unittest.TestCase):

    def test_from_list_parameter_then_script_last(self):
        out = _translate(PERFORM_SCRIPT_FROM_LIST)
        self.assertIn(
            '  <Step enable="True" id="1" name="Perform Script">\n'
            '    <Calculation><![CDATA[JSONSetElement ( "{}" ; "id" ; $id ; JSONString )]]></Calculation>\n'
            '    <Script id="805" name="Find Record"/>\n'
            '  </Step>',
            out,
        )
        self.assertNotIn('<Calculated>', out)
        self.assertNotIn('<FileReference', out)

    def test_by_name_keeps_name_and_parameter(self):
        out = _translate(PERFORM_SCRIPT_BY_NAME)
        self.assertIn(
            '    <Calculated>\n'
            '      <Calculation><![CDATA[$scriptName]]></Calculation>\n'
            '    </Calculated>\n'
            '    <Calculation><![CDATA[$param]]></Calculation>\n',
            out,
        )

    def test_cross_file_reference_first_with_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'xml_parsed'
            ds = root / 'external_data_sources' / 'SolutionApp'
            ds.mkdir(parents=True)
            (ds / 'Controller - ID 10.xml').write_text(
                '<ExternalDataSource name="Controller" type="FileMaker" id="10">'
                '<File><UniversalPathList>file:SolutionController</UniversalPathList></File>'
                '</ExternalDataSource>', encoding='utf-8')
            src = root / 'scripts' / 'SolutionApp' / 'Save - ID 1.xml'
            src.parent.mkdir(parents=True)
            src.write_text(_saxml(PERFORM_SCRIPT_CROSS_FILE), encoding='utf-8')
            out = translate_script(src)
        self.assertIn(
            '  <Step enable="True" id="1" name="Perform Script">\n'
            '    <FileReference id="10" name="Controller">\n'
            '      <UniversalPathList>file:SolutionController</UniversalPathList>\n'
            '    </FileReference>\n'
            '    <Calculation><![CDATA[$json]]></Calculation>\n'
            '    <Script id="586" name="Invoices | Save"/>\n'
            '  </Step>',
            out,
        )
        self.assertEqual(_rules(_lint(out), 'X003', 'X004'), [])

    def test_fmlint_no_x004(self):
        for saxml in (PERFORM_SCRIPT_FROM_LIST, PERFORM_SCRIPT_BY_NAME):
            self.assertEqual(_rules(_lint(_translate(saxml)), 'X001', 'X004'), [])


if __name__ == '__main__':
    unittest.main()
