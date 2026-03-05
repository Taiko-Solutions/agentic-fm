import type { ParsedLine } from '../parser';
import type { IdResolver } from '../id-resolver';
import { registerHrToXml, registerXmlToHr, stepOpen, stepSelfClose, cdata } from '../step-registry';

// --- # (comment) ---
registerHrToXml({
  stepNames: ['# (comment)'],
  toXml(line: ParsedLine): string {
    const text = line.commentText ?? '';
    if (!text) {
      return stepSelfClose('# (comment)', !line.disabled);
    }
    return [
      stepOpen('# (comment)', !line.disabled),
      `    <Text>${text}</Text>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['# (comment)'],
  toHR(el: Element): string {
    const text = el.querySelector('Text')?.textContent ?? '';
    return `# ${text}`;
  },
});

// --- If ---
registerHrToXml({
  stepNames: ['If'],
  toXml(line: ParsedLine): string {
    const condition = line.params[0] ?? '';
    return [
      stepOpen('If', !line.disabled),
      '    <Restore state="False"/>',
      `    <Calculation>${cdata(condition)}</Calculation>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['If'],
  toHR(el: Element): string {
    const calc = el.querySelector('Calculation')?.textContent ?? '';
    return calc ? `If [ ${calc} ]` : 'If';
  },
});

// --- Else If ---
registerHrToXml({
  stepNames: ['Else If'],
  toXml(line: ParsedLine): string {
    const condition = line.params[0] ?? '';
    return [
      stepOpen('Else If', !line.disabled),
      '    <Restore state="False"/>',
      `    <Calculation>${cdata(condition)}</Calculation>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Else If'],
  toHR(el: Element): string {
    const calc = el.querySelector('Calculation')?.textContent ?? '';
    return calc ? `Else If [ ${calc} ]` : 'Else If';
  },
});

// --- Else ---
registerHrToXml({
  stepNames: ['Else'],
  toXml(line: ParsedLine): string {
    return [
      stepOpen('Else', !line.disabled),
      '    <Restore state="False"/>',
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Else'],
  toHR(): string {
    return 'Else';
  },
});

// --- End If ---
registerHrToXml({
  stepNames: ['End If'],
  toXml(line: ParsedLine): string {
    return stepSelfClose('End If', !line.disabled);
  },
});

registerXmlToHr({
  xmlStepNames: ['End If'],
  toHR(): string {
    return 'End If';
  },
});

// --- Loop ---
registerHrToXml({
  stepNames: ['Loop'],
  toXml(line: ParsedLine): string {
    return [
      stepOpen('Loop', !line.disabled),
      '    <Restore state="False"/>',
      '    <FlushType value="Always"/>',
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Loop'],
  toHR(): string {
    return 'Loop';
  },
});

// --- Exit Loop If ---
registerHrToXml({
  stepNames: ['Exit Loop If'],
  toXml(line: ParsedLine): string {
    const condition = line.params[0] ?? 'True';
    return [
      stepOpen('Exit Loop If', !line.disabled),
      `    <Calculation>${cdata(condition)}</Calculation>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Exit Loop If'],
  toHR(el: Element): string {
    const calc = el.querySelector('Calculation')?.textContent ?? '';
    return `Exit Loop If [ ${calc} ]`;
  },
});

// --- End Loop ---
registerHrToXml({
  stepNames: ['End Loop'],
  toXml(line: ParsedLine): string {
    return stepSelfClose('End Loop', !line.disabled);
  },
});

registerXmlToHr({
  xmlStepNames: ['End Loop'],
  toHR(): string {
    return 'End Loop';
  },
});

// --- Exit Script ---
registerHrToXml({
  stepNames: ['Exit Script'],
  toXml(line: ParsedLine): string {
    let result = '';
    if (line.params.length > 0) {
      const param = line.params[0];
      // Handle "Result: value" label
      const resultMatch = param.match(/^Result:\s*(.*)$/i);
      result = resultMatch ? resultMatch[1].trim() : param;
    }
    return [
      stepOpen('Exit Script', !line.disabled),
      `    <Calculation>${cdata(result)}</Calculation>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Exit Script'],
  toHR(el: Element): string {
    const calc = el.querySelector('Calculation')?.textContent ?? '';
    if (calc) return `Exit Script [ Result: ${calc} ]`;
    return 'Exit Script';
  },
});

// --- Set Variable ---
registerHrToXml({
  stepNames: ['Set Variable'],
  toXml(line: ParsedLine): string {
    const name = line.params[0] ?? '$var';
    let value = line.params[1] ?? '';
    let rep = line.params[2];
    // Strip "Value:" label prefix (same pattern as Exit Script's "Result:")
    const valueMatch = value.match(/^Value:\s*([\s\S]*)$/i);
    if (valueMatch) value = valueMatch[1].trim();
    // Strip "Repetition:" label prefix
    if (rep) {
      const repMatch = rep.match(/^Repetition:\s*([\s\S]*)$/i);
      if (repMatch) rep = repMatch[1].trim();
    }
    const lines = [
      stepOpen('Set Variable', !line.disabled),
      '    <Value>',
      `      <Calculation>${cdata(value)}</Calculation>`,
      '    </Value>',
    ];
    if (rep) {
      lines.push(
        '    <Repetition>',
        `      <Calculation>${cdata(rep)}</Calculation>`,
        '    </Repetition>',
      );
    }
    lines.push(`    <Name>${name}</Name>`, '  </Step>');
    return lines.join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Set Variable'],
  toHR(el: Element): string {
    const name = el.querySelector('Name')?.textContent ?? '$var';
    const value = el.querySelector('Value > Calculation')?.textContent ?? '';
    return `Set Variable [ ${name} ; ${value} ]`;
  },
});

// --- Allow User Abort ---
registerHrToXml({
  stepNames: ['Allow User Abort'],
  toXml(line: ParsedLine): string {
    const param = (line.params[0] ?? 'Off').trim();
    const state = param.toLowerCase() === 'on' ? 'True' : 'False';
    return [
      stepOpen('Allow User Abort', !line.disabled),
      `    <Set state="${state}"/>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Allow User Abort'],
  toHR(el: Element): string {
    const state = el.querySelector('Set')?.getAttribute('state') ?? 'False';
    return `Allow User Abort [ ${state === 'True' ? 'On' : 'Off'} ]`;
  },
});

// --- Set Error Capture ---
registerHrToXml({
  stepNames: ['Set Error Capture'],
  toXml(line: ParsedLine): string {
    const param = (line.params[0] ?? 'On').trim();
    const state = param.toLowerCase() === 'on' ? 'True' : 'False';
    return [
      stepOpen('Set Error Capture', !line.disabled),
      `    <Set state="${state}"/>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Set Error Capture'],
  toHR(el: Element): string {
    const state = el.querySelector('Set')?.getAttribute('state') ?? 'True';
    return `Set Error Capture [ ${state === 'True' ? 'On' : 'Off'} ]`;
  },
});

// --- Perform Script ---
registerHrToXml({
  stepNames: ['Perform Script'],
  toXml(line: ParsedLine, resolver: IdResolver): string {
    let scriptName = '';
    let parameter = '';

    for (const p of line.params) {
      const paramMatch = p.match(/^Parameter:\s*(.*)$/i);
      if (paramMatch) {
        parameter = paramMatch[1].trim();
      } else if (!scriptName) {
        scriptName = p.replace(/^"|"$/g, '').trim();
      }
    }

    const resolved = resolver.resolveScript(scriptName);
    const lines = [
      stepOpen('Perform Script', !line.disabled),
    ];
    if (parameter) {
      lines.push(`    <Calculation>${cdata(parameter)}</Calculation>`);
    }
    lines.push(
      `    <Script id="${resolved.id}" name="${resolved.name}"/>`,
      '  </Step>',
    );
    return lines.join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Perform Script'],
  toHR(el: Element): string {
    const script = el.querySelector('Script');
    const name = script?.getAttribute('name') ?? '';
    const calc = el.querySelector('Calculation')?.textContent ?? '';
    const parts = [`"${name}"`];
    if (calc) parts.push(`Parameter: ${calc}`);
    return `Perform Script [ ${parts.join(' ; ')} ]`;
  },
});

// --- Halt Script ---
registerHrToXml({
  stepNames: ['Halt Script'],
  toXml(line: ParsedLine): string {
    return stepSelfClose('Halt Script', !line.disabled);
  },
});

registerXmlToHr({
  xmlStepNames: ['Halt Script'],
  toHR(): string {
    return 'Halt Script';
  },
});
