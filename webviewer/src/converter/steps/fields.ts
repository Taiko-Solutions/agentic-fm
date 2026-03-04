import type { ParsedLine } from '../parser';
import type { IdResolver } from '../id-resolver';
import { registerHrToXml, registerXmlToHr, stepOpen, cdata, escXml } from '../step-registry';

// --- Set Field ---
registerHrToXml({
  stepNames: ['Set Field'],
  toXml(line: ParsedLine, resolver: IdResolver): string {
    const fieldRef = line.params[0] ?? '';
    const value = line.params[1] ?? '';
    const resolved = resolver.resolveField(fieldRef);

    return [
      stepOpen('Set Field', !line.disabled),
      `    <Calculation>${cdata(value)}</Calculation>`,
      `    <Field table="${escXml(resolved.table)}" id="${resolved.fieldId}" name="${escXml(resolved.fieldName)}"/>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Set Field'],
  toHR(el: Element): string {
    const field = el.querySelector('Field');
    const table = field?.getAttribute('table') ?? '';
    const name = field?.getAttribute('name') ?? '';
    const calc = el.querySelector('Calculation')?.textContent ?? '';
    const fieldRef = table ? `${table}::${name}` : name;
    return `Set Field [ ${fieldRef} ; ${calc} ]`;
  },
});
