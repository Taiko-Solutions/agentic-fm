import * as monaco from 'monaco-editor';
import type { StepCatalogEntry } from '@/converter/catalog-types';
import type { ConversionError } from '@/converter/hr-to-xml';

/**
 * Client-side diagnostics for FileMaker script.
 * Checks for:
 * - Unmatched If/End If, Loop/End Loop pairs
 * - Unknown step names (vs. step catalog)
 * - Unclosed string literals
 */
export function createDiagnosticsProvider(
  editor: monaco.editor.IStandaloneCodeEditor,
  catalog: StepCatalogEntry[],
): monaco.IDisposable {
  const knownSet = new Set(catalog.map(e => e.name.toLowerCase()));
  const model = editor.getModel();
  if (!model) return { dispose() {} };

  function validate() {
    const model = editor.getModel();
    if (!model) return;

    const markers: monaco.editor.IMarkerData[] = [];
    const lines = model.getLinesContent();
    const blockStack: { type: 'If' | 'Loop'; line: number }[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const lineNum = i + 1;

      // Skip comments and empty lines
      if (!line || line.startsWith('#') || line.startsWith('//')) continue;

      // Extract step name (everything before [ or EOL)
      const bracketIdx = line.indexOf('[');
      const stepName = (bracketIdx >= 0 ? line.substring(0, bracketIdx) : line).trim();

      // Check block matching
      if (stepName === 'If') {
        blockStack.push({ type: 'If', line: lineNum });
      } else if (stepName === 'Loop') {
        blockStack.push({ type: 'Loop', line: lineNum });
      } else if (stepName === 'End If') {
        const top = blockStack.pop();
        if (!top || top.type !== 'If') {
          markers.push({
            severity: monaco.MarkerSeverity.Error,
            message: 'End If without matching If',
            startLineNumber: lineNum,
            startColumn: 1,
            endLineNumber: lineNum,
            endColumn: line.length + 1,
          });
          if (top) blockStack.push(top); // Put it back
        }
      } else if (stepName === 'End Loop') {
        const top = blockStack.pop();
        if (!top || top.type !== 'Loop') {
          markers.push({
            severity: monaco.MarkerSeverity.Error,
            message: 'End Loop without matching Loop',
            startLineNumber: lineNum,
            startColumn: 1,
            endLineNumber: lineNum,
            endColumn: line.length + 1,
          });
          if (top) blockStack.push(top);
        }
      }

      // Check for unknown step names (if we have a known list)
      if (knownSet.size > 0 && stepName && !knownSet.has(stepName.toLowerCase())) {
        // Only warn for lines that look like step invocations (start with uppercase)
        if (/^[A-Z]/.test(stepName) && stepName !== 'Else') {
          markers.push({
            severity: monaco.MarkerSeverity.Warning,
            message: `Unknown step: "${stepName}"`,
            startLineNumber: lineNum,
            startColumn: 1,
            endLineNumber: lineNum,
            endColumn: stepName.length + 1,
          });
        }
      }

      // Check for unclosed strings in bracket content
      if (bracketIdx >= 0) {
        const bracketContent = line.substring(bracketIdx);
        let inString = false;
        for (const ch of bracketContent) {
          if (ch === '"') inString = !inString;
        }
        if (inString) {
          markers.push({
            severity: monaco.MarkerSeverity.Warning,
            message: 'Unclosed string literal',
            startLineNumber: lineNum,
            startColumn: bracketIdx + 1,
            endLineNumber: lineNum,
            endColumn: line.length + 1,
          });
        }
      }
    }

    // Report unmatched opening blocks
    for (const block of blockStack) {
      markers.push({
        severity: monaco.MarkerSeverity.Error,
        message: `${block.type} without matching End ${block.type}`,
        startLineNumber: block.line,
        startColumn: 1,
        endLineNumber: block.line,
        endColumn: model.getLineContent(block.line).length + 1,
      });
    }

    monaco.editor.setModelMarkers(model, 'filemaker-script', markers);
  }

  // Run on change — debounced to avoid blocking the main thread on every keystroke
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  const disposable = model.onDidChangeContent(() => {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(validate, 300);
  });

  // Initial validation
  validate();

  return {
    dispose() {
      if (debounceTimer) clearTimeout(debounceTimer);
      disposable.dispose();
    },
  };
}

export function updateConversionDiagnostics(
  model: monaco.editor.ITextModel,
  errors: ConversionError[],
): void {
  const markers: monaco.editor.IMarkerData[] = errors.map(err => {
    const lineNumber = err.line > 0 ? err.line : 1;
    const lineContent = lineNumber <= model.getLineCount() ? model.getLineContent(lineNumber) : '';
    return {
      severity: monaco.MarkerSeverity.Error,
      message: err.message,
      startLineNumber: lineNumber,
      startColumn: 1,
      endLineNumber: lineNumber,
      endColumn: lineContent.length + 1,
    };
  });
  monaco.editor.setModelMarkers(model, 'filemaker-conversion', markers);
}
