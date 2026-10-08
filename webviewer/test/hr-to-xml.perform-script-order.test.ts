/**
 * Regression: Perform Script must emit its children in FileMaker's order —
 * FileReference → Calculated → Calculation → Script (Script LAST).
 *
 * The catalog lists the params in HR order (script first). Emitted that way,
 * FileMaker accepts the paste but leaves the target unresolved
 * (`From list ; ""`) and the step calls nothing — fmlint X004. The Python
 * converter (agent/scripts/catalog_emit.py, _XML_CHILD_ORDER) applies the same
 * override.
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

/** Top-level child element names of the first <Step>, in document order. */
function stepChildren(xml: string): string[] {
  const body = xml.split(/<Step [^>]*>/)[1].split('</Step>')[0];
  return [...body.matchAll(/^ {4}<(\w+)/gm)].map((m) => m[1]);
}

describe('HR→XML Perform Script child order (fmlint X004)', () => {
  it('emits the parameter before <Script>', () => {
    const { xml } = hrToXml('Perform Script [ "Mi Script" ; Parameter: $p ]');
    expect(stepChildren(xml)).toEqual(['Calculation', 'Script']);
    expect(xml).toContain('<Calculation><![CDATA[$p]]></Calculation>\n    <Script id="0" name="Mi Script"/>');
  });

  it('emits no empty <FileReference> for a same-file call', () => {
    const { xml } = hrToXml('Perform Script [ "Mi Script" ]');
    expect(stepChildren(xml)).toEqual(['Script']);
  });

  it('keeps by-name <Calculated> before the parameter', () => {
    const { xml } = hrToXml('Perform Script [ By name: $nombre ; Parameter: $p ]');
    expect(stepChildren(xml)).toEqual(['Calculated', 'Calculation']);
  });
});

// Order copied from FileMaker 2026 (clipboard, 2026-10-08), minus the
// optional <DisableStepCollapsed>: both server steps already follow the
// catalog order, with the parameter before <Script>. Guards against a future
// XML_CHILD_ORDER entry or catalog reorder breaking them.
describe('HR→XML Perform Script on Server child order (FileMaker real)', () => {
  it('Perform Script on Server: WaitForCompletion → Calculation → Script', () => {
    const { xml } = hrToXml('Perform Script on Server [ "Mi Script" ; Parameter: $p ; Wait for completion: On ]');
    expect(stepChildren(xml)).toEqual(['WaitForCompletion', 'Calculation', 'Script']);
  });

  it('… with Callback: CallbackScriptState → Calculation → Script → CallbackScript', () => {
    const { xml } = hrToXml(
      'Perform Script on Server with Callback [ "Mi Script" ; Parameter: $p ; State: Continue ; ' +
        'Callback script: Script="Otro Script", Parameter=$c ]',
    );
    expect(stepChildren(xml)).toEqual(['CallbackScriptState', 'Calculation', 'Script', 'CallbackScript']);
    expect(xml).toContain('<ScriptName id="0" name="Otro Script"/>');
  });
});
