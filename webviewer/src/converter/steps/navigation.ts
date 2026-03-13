import type { ParsedLine } from '../parser';
import type { IdResolver } from '../id-resolver';
import { registerHrToXml, registerXmlToHr, stepOpen, cdata, escXml } from '../step-registry';
import { unquote } from '../parser';

// --- Go to Layout ---
registerHrToXml({
  stepNames: ['Go to Layout'],
  toXml(line: ParsedLine, resolver: IdResolver): string {
    // Extract layout name: handle both simple `"Name"` and labeled `Layout: "Name"`
    let layoutRaw = '';
    for (const p of line.params) {
      const layoutMatch = p.match(/^Layout:\s*(.*)$/i);
      if (layoutMatch) {
        layoutRaw = layoutMatch[1].trim();
      } else if (p.match(/^Animation:/i)) {
        // Ignore Animation parameter
      } else if (!layoutRaw) {
        layoutRaw = p.trim();
      }
    }

    // Handle special "original layout" value (with or without angle brackets)
    const rawLower = layoutRaw.toLowerCase();
    if (rawLower === 'original layout' || rawLower === '<original layout>') {
      return [
        stepOpen('Go to Layout', !line.disabled),
        '    <LayoutDestination value="OriginalLayout"/>',
        '  </Step>',
      ].join('\n');
    }

    const layoutName = unquote(layoutRaw);
    const resolved = resolver.resolveLayout(layoutName);

    return [
      stepOpen('Go to Layout', !line.disabled),
      '    <LayoutDestination value="SelectedLayout"/>',
      `    <Layout id="${resolved.id}" name="${escXml(resolved.name)}"/>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Go to Layout'],
  toHR(el: Element): string {
    const dest = el.querySelector('LayoutDestination')?.getAttribute('value');
    if (dest === 'OriginalLayout') {
      return 'Go to Layout [ original layout ]';
    }
    const layout = el.querySelector('Layout');
    const name = layout?.getAttribute('name') ?? '';
    return `Go to Layout [ "${name}" ]`;
  },
});

// --- Go to Object ---
registerHrToXml({
  stepNames: ['Go to Object'],
  toXml(line: ParsedLine): string {
    let objectName = '';
    let repetition = '';

    for (const p of line.params) {
      const objMatch = p.match(/^Object Name:\s*(.*)$/i);
      const repMatch = p.match(/^Repetition:\s*(.*)$/i);
      if (objMatch) {
        objectName = unquote(objMatch[1].trim());
      } else if (repMatch) {
        repetition = repMatch[1].trim();
      } else if (!objectName) {
        objectName = unquote(p.trim());
      }
    }

    const lines = [
      stepOpen('Go to Object', !line.disabled),
      '    <ObjectName>',
      `      <Calculation>${cdata(objectName ? `"${objectName}"` : '')}</Calculation>`,
      '    </ObjectName>',
      '    <Repetition>',
      `      <Calculation>${cdata(repetition || '1')}</Calculation>`,
      '    </Repetition>',
      '  </Step>',
    ];
    return lines.join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Go to Object'],
  toHR(el: Element): string {
    const objCalc = el.querySelector('ObjectName > Calculation')?.textContent ?? '';
    // Strip surrounding quotes from the calc expression
    const name = objCalc.replace(/^"|"$/g, '');
    return `Go to Object [ Object Name: "${name}" ]`;
  },
});
