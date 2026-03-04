import * as monaco from 'monaco-editor';
import type { StepCatalogEntry } from '@/converter/catalog-types';

/**
 * Autocomplete provider for FileMaker script step names.
 * Driven by the step catalog for snippets, categories, and help links.
 */
export function createCompletionProvider(
  catalog: StepCatalogEntry[],
): monaco.languages.CompletionItemProvider {
  return {
    triggerCharacters: [],

    provideCompletionItems(
      model: monaco.editor.ITextModel,
      position: monaco.Position,
    ): monaco.languages.ProviderResult<monaco.languages.CompletionList> {
      const lineContent = model.getLineContent(position.lineNumber);
      const lineUntilPosition = lineContent.substring(0, position.column - 1).trimStart();

      // Only suggest step names at the start of a line (before any bracket)
      if (lineUntilPosition.includes('[')) {
        return { suggestions: [] };
      }

      const word = model.getWordUntilPosition(position);
      const range: monaco.IRange = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      const suggestions: monaco.languages.CompletionItem[] = catalog.map((entry, i) => {
        const isControl = controlSteps.has(entry.name);
        return {
          label: entry.name,
          kind: isControl
            ? monaco.languages.CompletionItemKind.Keyword
            : monaco.languages.CompletionItemKind.Function,
          insertText: getInsertText(entry),
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          detail: isControl ? 'Control flow' : entry.category,
          documentation: entry.helpUrl ? { value: `[Help](${entry.helpUrl})` } : undefined,
          sortText: String(i).padStart(4, '0'),
          range,
        };
      });

      return { suggestions };
    },
  };
}

const controlSteps = new Set([
  'If', 'Else If', 'Else', 'End If',
  'Loop', 'Exit Loop If', 'End Loop',
  'Exit Script', 'Halt Script',
]);

/** Generate snippet insert text from catalog entry */
function getInsertText(entry: StepCatalogEntry): string {
  // Use catalog monacoSnippet if available
  if (entry.monacoSnippet) return entry.monacoSnippet;

  // Generate from hrSignature if available
  if (entry.hrSignature) {
    return `${entry.name} ${entry.hrSignature.replace(/\$/g, '\\$')}`;
  }

  // Control steps without params: just the step name
  if (controlSteps.has(entry.name)) return entry.name;

  // Self-closing steps with no params: just the step name
  if (entry.selfClosing && entry.params.length === 0) return entry.name;

  // Default: step name with empty bracket and cursor
  return `${entry.name} [ $0 ]`;
}
