import type { ParsedLine } from '../parser';
import type { IdResolver } from '../id-resolver';
import { registerHrToXml, registerXmlToHr, stepOpen, stepSelfClose, cdata, escXml } from '../step-registry';
import { unquote } from '../parser';

// --- Freeze Window ---
registerHrToXml({
  stepNames: ['Freeze Window'],
  toXml(line: ParsedLine): string {
    return stepSelfClose('Freeze Window', !line.disabled);
  },
});

registerXmlToHr({
  xmlStepNames: ['Freeze Window'],
  toHR(): string {
    return 'Freeze Window';
  },
});

// --- New Window ---
registerHrToXml({
  stepNames: ['New Window'],
  toXml(line: ParsedLine, resolver: IdResolver): string {
    let windowName = '';
    let height = '';
    let width = '';
    let top = '';
    let left = '';
    let style = 'Document';
    let layoutName = '';

    for (const p of line.params) {
      const nameMatch = p.match(/^Name:\s*(.*)$/i);
      const heightMatch = p.match(/^Height:\s*(.*)$/i);
      const widthMatch = p.match(/^Width:\s*(.*)$/i);
      const topMatch = p.match(/^Top:\s*(.*)$/i);
      const leftMatch = p.match(/^Left:\s*(.*)$/i);
      const styleMatch = p.match(/^Style:\s*(.*)$/i);
      const layoutMatch = p.match(/^Layout:\s*(.*)$/i);

      if (nameMatch) windowName = nameMatch[1].trim();
      else if (heightMatch) height = heightMatch[1].trim();
      else if (widthMatch) width = widthMatch[1].trim();
      else if (topMatch) top = topMatch[1].trim();
      else if (leftMatch) left = leftMatch[1].trim();
      else if (styleMatch) style = styleMatch[1].trim();
      else if (layoutMatch) layoutName = unquote(layoutMatch[1].trim());
    }

    const resolvedLayout = layoutName ? resolver.resolveLayout(layoutName) : null;

    const lines = [
      stepOpen('New Window', !line.disabled),
      '    <LayoutDestination value="SelectedLayout"/>',
      '    <Name>',
      `      <Calculation>${cdata(windowName ? `"${windowName}"` : '')}</Calculation>`,
      '    </Name>',
      '    <Height>',
      `      <Calculation>${cdata(height)}</Calculation>`,
      '    </Height>',
      '    <Width>',
      `      <Calculation>${cdata(width)}</Calculation>`,
      '    </Width>',
      '    <DistanceFromTop>',
      `      <Calculation>${cdata(top)}</Calculation>`,
      '    </DistanceFromTop>',
      '    <DistanceFromLeft>',
      `      <Calculation>${cdata(left)}</Calculation>`,
      '    </DistanceFromLeft>',
      `    <NewWndStyles DimParentWindow="No" Toolbars="Yes" MenuBar="Yes" Style="${escXml(style)}" Close="Yes" Minimize="Yes" Maximize="Yes" Resize="Yes" Styles="1076299266"/>`,
    ];

    if (resolvedLayout) {
      lines.push(`    <Layout id="${resolvedLayout.id}" name="${escXml(resolvedLayout.name)}"/>`);
    } else {
      lines.push('    <Layout id="0" name=""/>');
    }

    lines.push('  </Step>');
    return lines.join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['New Window'],
  toHR(el: Element): string {
    const parts: string[] = [];
    const nameCalc = el.querySelector('Name > Calculation')?.textContent ?? '';
    const style = el.querySelector('NewWndStyles')?.getAttribute('Style') ?? 'Document';
    const layout = el.querySelector('Layout');
    const layoutName = layout?.getAttribute('name');
    const heightCalc = el.querySelector('Height > Calculation')?.textContent ?? '';
    const widthCalc = el.querySelector('Width > Calculation')?.textContent ?? '';

    if (nameCalc) parts.push(`Name: ${nameCalc}`);
    if (style !== 'Document') parts.push(`Style: ${style}`);
    if (layoutName) parts.push(`Layout: "${layoutName}"`);
    if (heightCalc) parts.push(`Height: ${heightCalc}`);
    if (widthCalc) parts.push(`Width: ${widthCalc}`);

    if (parts.length > 0) return `New Window [ ${parts.join(' ; ')} ]`;
    return 'New Window';
  },
});

// --- Close Window ---
registerHrToXml({
  stepNames: ['Close Window'],
  toXml(line: ParsedLine): string {
    let windowMode = 'Current';
    let windowName = '';

    for (const p of line.params) {
      const nameMatch = p.match(/^Name:\s*(.*)$/i);
      if (nameMatch) {
        windowName = nameMatch[1].trim();
        windowMode = 'ByName';
      } else if (p.trim().toLowerCase() === 'current') {
        windowMode = 'Current';
      }
    }

    const lines = [
      stepOpen('Close Window', !line.disabled),
      '    <LimitToWindowsOfCurrentFile state="True"/>',
      `    <Window value="${windowMode}"/>`,
    ];

    if (windowMode === 'ByName') {
      lines.push(
        '    <Name>',
        `      <Calculation>${cdata(windowName)}</Calculation>`,
        '    </Name>',
      );
    }

    lines.push('  </Step>');
    return lines.join('\n');
  },
});

registerXmlToHr({
  xmlStepNames: ['Close Window'],
  toHR(el: Element): string {
    const mode = el.querySelector('Window')?.getAttribute('value') ?? 'Current';
    if (mode === 'ByName') {
      const name = el.querySelector('Name > Calculation')?.textContent ?? '';
      return `Close Window [ Name: ${name} ]`;
    }
    return `Close Window [ Current ]`;
  },
});
