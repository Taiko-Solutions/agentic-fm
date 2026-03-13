/**
 * fmxmlsnippet XML -> Human-Readable converter.
 *
 * Parses fmxmlsnippet XML and emits formatted HR text with proper
 * indentation for control flow nesting.
 */

import { getXmlToHrConverter } from './step-registry';

// Import step registrations (side-effect imports)
import './steps/control';
import './steps/fields';
import './steps/navigation';
import './steps/records';
import './steps/windows';
import './steps/miscellaneous';

/**
 * Convert fmxmlsnippet XML to human-readable script text.
 */
export function xmlToHr(xml: string): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, 'text/xml');

  const parseError = doc.querySelector('parsererror');
  if (parseError) {
    return `# XML Parse Error: ${parseError.textContent}`;
  }

  const steps = doc.querySelectorAll('fmxmlsnippet > Step');
  const lines: string[] = [];
  let indent = 0;

  // Steps that decrease indent before the line
  const deindentBefore = new Set(['End If', 'End Loop', 'Else', 'Else If']);
  // Steps that increase indent after the line
  const indentAfter = new Set(['If', 'Else If', 'Else', 'Loop']);

  for (const step of steps) {
    const stepName = step.getAttribute('name') ?? '';
    const enabled = step.getAttribute('enable') !== 'False';

    // Decrease indent for closing/middle blocks
    if (deindentBefore.has(stepName)) {
      indent = Math.max(0, indent - 1);
    }

    const converter = getXmlToHrConverter(stepName);
    let hrLine: string;

    if (converter) {
      hrLine = converter.toHR(step as Element);
    } else {
      hrLine = `[UNKNOWN STEP: ${stepName}]`;
    }

    // Add disabled prefix
    if (!enabled) {
      hrLine = `// ${hrLine}`;
    }

    // Apply indentation
    const prefix = '    '.repeat(indent);
    lines.push(`${prefix}${hrLine}`);

    // Increase indent for opening blocks
    if (indentAfter.has(stepName)) {
      indent++;
    }
  }

  return lines.join('\n');
}
