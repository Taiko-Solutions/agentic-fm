import type { ParsedLine } from '../parser';
import { registerHrToXml, registerXmlToHr, stepOpen, cdata } from '../step-registry';
import { unquote } from '../parser';

// --- Show Custom Dialog ---
registerHrToXml({
  stepNames: ['Show Custom Dialog'],
  toXml(line: ParsedLine): string {
    const title = line.params[0] ? unquote(line.params[0]) : '';
    const message = line.params[1] ? unquote(line.params[1]) : '';

    return [
      stepOpen('Show Custom Dialog', !line.disabled),
      '    <Title>',
      `      <Calculation>${cdata(title ? `"${title}"` : '')}</Calculation>`,
      '    </Title>',
      '    <Message>',
      `      <Calculation>${cdata(message ? `"${message}"` : '')}</Calculation>`,
      '    </Message>',
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Show Custom Dialog'],
  toHR(el: Element): string {
    const title = el.querySelector('Title > Calculation')?.textContent ?? '';
    const message = el.querySelector('Message > Calculation')?.textContent ?? '';
    const parts: string[] = [];
    if (title) parts.push(title);
    if (message) parts.push(message);
    return `Show Custom Dialog [ ${parts.join(' ; ')} ]`;
  },
});
