/**
 * Regression: the "Specified:" token that FileMaker's HR puts on Perform Script
 * and its server variants is a mode marker, not a value.
 *
 * FileMaker renders the mode as `Specified: From list` / `Specified: By name`
 * (also seen as bare `From list` / `By name`, before or after the script name).
 * The converter used to read it as data: Perform Script turned
 * `Specified: From list` into the script name and pushed the real name into
 * <FileReference>; Perform Script on Server put "From list" in <Calculated>
 * (by-name mode) next to <Script>, a dead step (fmlint X004).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { hrToXml, loadCatalog } from '@/converter/hr-to-xml';
import type { StepCatalogEntry } from '@/converter/catalog-types';

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const CATALOG_PATH = path.join(REPO_ROOT, 'agent', 'catalogs', 'step-catalog-en.json');

const rawCatalog = JSON.parse(readFileSync(CATALOG_PATH, 'utf-8'));
const entries: StepCatalogEntry[] = rawCatalog.steps ?? rawCatalog;
loadCatalog(entries);

/** Inner XML of the first <Step>, one child element per line, indentation dropped. */
function body(hr: string): string {
  const { xml } = hrToXml(hr);
  const inner = xml.split(/<Step [^>]*>/)[1].split('</Step>')[0];
  return inner.split('\n').map((l) => l.trim()).filter(Boolean).join('\n');
}

const FROM_LIST_PS = '<Calculation><![CDATA[$p]]></Calculation>\n<Script id="0" name="Mi Script"/>';

describe('HR→XML Perform Script "Specified:" mode marker', () => {
  it.each([
    'Perform Script [ Specified: From list ; "Mi Script" ; Parameter: $p ]',
    'Perform Script [ "Mi Script" ; Specified: From list ; Parameter: $p ]',
    'Perform Script [ From list ; "Mi Script" ; Parameter: $p ]',
  ])('From list: %s', (hr) => {
    expect(body(hr)).toBe(FROM_LIST_PS);
  });

  it.each([
    'Perform Script [ Specified: By name ; $Nombre ; Parameter: $p ]',
    'Perform Script [ By name ; $Nombre ; Parameter: $p ]',
  ])('By name: %s', (hr) => {
    expect(body(hr)).toBe(
      '<Calculated>\n<Calculation><![CDATA[$Nombre]]></Calculation>\n</Calculated>\n' +
        '<Calculation><![CDATA[$p]]></Calculation>',
    );
  });

  it('By name keeps a quoted literal as the calculation', () => {
    expect(body('Perform Script [ Specified: By name ; "Mi Script" ; Parameter: ]')).toBe(
      '<Calculated>\n<Calculation><![CDATA["Mi Script"]]></Calculation>\n</Calculated>',
    );
  });
});

describe('HR→XML Perform Script on Server "Specified:" mode marker', () => {
  it.each([
    'Perform Script on Server [ Specified: From list ; "Mi Script" ; Parameter: $p ; Wait for completion: On ]',
    'Perform Script on Server [ From list ; "Mi Script" ; Parameter: $p ; Wait for completion: On ]',
  ])('From list: %s', (hr) => {
    expect(body(hr)).toBe(
      '<WaitForCompletion state="True"/>\n' + FROM_LIST_PS,
    );
  });

  it('By name emits <Calculated> and no <Script>', () => {
    expect(
      body('Perform Script on Server [ Specified: By name ; $Nombre ; Parameter: $p ; Wait for completion: Off ]'),
    ).toBe(
      '<Calculated>\n<Calculation><![CDATA[$Nombre]]></Calculation>\n</Calculated>\n' +
        '<WaitForCompletion state="False"/>\n<Calculation><![CDATA[$p]]></Calculation>',
    );
  });

  it('with Callback, From list', () => {
    expect(
      body(
        'Perform Script on Server with Callback [ Specified: From list ; "Mi Script" ; Parameter: $p ; ' +
          'State: Continue ; Callback script: Script="Otro Script", Parameter=$c ]',
      ),
    ).toBe(
      '<CallbackScriptState value="Continue"/>\n' + FROM_LIST_PS + '\n' +
        '<CallbackScript>\n<ScriptName id="0" name="Otro Script"/>\n<ScriptParameter>\n' +
        '<Calculation><![CDATA[$c]]></Calculation>\n</ScriptParameter>\n</CallbackScript>',
    );
  });

  it('with Callback, By name emits no <Script>', () => {
    expect(
      body('Perform Script on Server with Callback [ Specified: By name ; $Nombre ; Parameter: $p ; State: Halt ]'),
    ).toBe(
      '<Calculated>\n<Calculation><![CDATA[$Nombre]]></Calculation>\n</Calculated>\n' +
        '<CallbackScriptState value="Halt"/>\n<Calculation><![CDATA[$p]]></Calculation>',
    );
  });
});
