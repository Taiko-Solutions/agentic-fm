/**
 * Regression: Perform Script to another file (`File: "Y"` / `"X" from file: "Y"`).
 *
 * The converter used to drop the `File: "Y"` token positionally into the
 * catalog's <FileReference> text param, emitting `<FileReference>File: "Y"</FileReference>`
 * — a step FileMaker cannot resolve.
 *
 * Verified by pasting into FileMaker 2026-10 (same caller file, data source and
 * file both named "TaikoAI"):
 *   - <FileReference id="0" name="Y"> + <UniversalPathList>file:Y</UniversalPathList>
 *     and <Script id="0" name="X"/> → FileMaker resolves both by NAME on paste
 *     (data source id 26, remote script id 644).
 *   - <FileReference id="0" name=""> with only the path → FileMaker discards the
 *     path and the step shows `<unknown> from file: ""`. The name is what matters.
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
function body(xml: string): string {
  const inner = xml.split(/<Step [^>]*>/)[1].split('</Step>')[0];
  return inner.split('\n').map((l) => l.trim()).filter(Boolean).join('\n');
}

const CROSS_FILE_PS =
  '<FileReference id="0" name="OtroArchivo">\n' +
  '<UniversalPathList>file:OtroArchivo</UniversalPathList>\n' +
  '</FileReference>\n' +
  '<Calculation><![CDATA[$p]]></Calculation>\n' +
  '<Script id="0" name="Mi Script"/>';

describe('HR→XML Perform Script to another file', () => {
  it.each([
    'Perform Script [ "Mi Script" ; Specified: From list ; File: "OtroArchivo" ; Parameter: $p ]',
    'Perform Script [ Specified: From list ; "Mi Script" ; File: "OtroArchivo" ; Parameter: $p ]',
    'Perform Script [ "Mi Script" from file: "OtroArchivo" ; Specified: From list ; Parameter: $p ]',
  ])('emits a name-resolved FileReference: %s', (hr) => {
    const { xml, errors } = hrToXml(hr);
    expect(errors).toEqual([]);
    expect(body(xml)).toBe(CROSS_FILE_PS);
  });

  it('never resolves the target script against the caller file context', () => {
    // A same-named script in the caller file must not leak its id into a
    // cross-file call: the target id belongs to the other file.
    const context = { scripts: { 'Mi Script': { id: 77 } } } as never;
    const { xml } = hrToXml(
      'Perform Script [ "Mi Script" ; Specified: From list ; File: "OtroArchivo" ; Parameter: $p ]',
      context,
    );
    expect(body(xml)).toBe(CROSS_FILE_PS);
  });

  it.each([
    'Perform Script [ "Mi Script" ; Specified: From list ; File: "" ; Parameter: $p ]',
    'Perform Script [ <unknown> from file: "" (file not open) ; Specified: From list ; Parameter: $p ]',
  ])('flags a cross-file call without a file name as not convertible: %s', (hr) => {
    const { xml, errors } = hrToXml(hr);
    expect(errors).toHaveLength(1);
    expect(errors[0].message).toMatch(/otro archivo|another file/i);
    expect(xml).not.toContain('<FileReference');
  });

  it('same-file call emits no FileReference', () => {
    const { xml } = hrToXml('Perform Script [ "Mi Script" ; Specified: From list ; Parameter: $p ]');
    expect(xml).not.toContain('FileReference');
  });
});
