import type { ParsedLine } from '../parser';
import { registerHrToXml, registerXmlToHr, stepOpen, stepSelfClose } from '../step-registry';

// --- Commit Records/Requests ---
registerHrToXml({
  stepNames: ['Commit Records/Requests'],
  toXml(line: ParsedLine): string {
    let noInteract = 'True';  // Default: no dialog
    let skipDataEntry = 'False';
    let essForceCommit = 'False';

    for (const p of line.params) {
      const dialogMatch = p.match(/^With dialog:\s*(.*)$/i);
      const skipMatch = p.match(/^Skip data entry validation:\s*(.*)$/i);
      const essMatch = p.match(/^Force Commit:\s*(.*)$/i);
      if (dialogMatch) {
        noInteract = dialogMatch[1].trim().toLowerCase() === 'off' ? 'True' : 'False';
      } else if (skipMatch) {
        skipDataEntry = skipMatch[1].trim().toLowerCase() === 'on' ? 'True' : 'False';
      } else if (essMatch) {
        essForceCommit = essMatch[1].trim().toLowerCase() === 'on' ? 'True' : 'False';
      }
    }

    return [
      stepOpen('Commit Records/Requests', !line.disabled),
      `    <NoInteract state="${noInteract}"/>`,
      `    <Option state="${skipDataEntry}"/>`,
      `    <ESSForceCommit state="${essForceCommit}"/>`,
      '  </Step>',
    ].join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Commit Records/Requests'],
  toHR(el: Element): string {
    const noInteract = el.querySelector('NoInteract')?.getAttribute('state') === 'True';
    const parts: string[] = [];
    if (noInteract) {
      parts.push('With dialog: Off');
    } else {
      parts.push('With dialog: On');
    }
    return `Commit Records/Requests [ ${parts.join(' ; ')} ]`;
  },
});

// --- New Record/Request ---
registerHrToXml({
  stepNames: ['New Record/Request'],
  toXml(line: ParsedLine): string {
    return stepSelfClose('New Record/Request', !line.disabled);
  },
});

registerXmlToHr({
  xmlStepNames: ['New Record/Request'],
  toHR(): string {
    return 'New Record/Request';
  },
});
