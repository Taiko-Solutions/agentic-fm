import * as monaco from 'monaco-editor';
import { monarchLanguage, languageConfiguration } from './monarch';
import { filemakerDarkTheme } from './theme';
import { createCompletionProvider } from './completion';
import { createDiagnosticsProvider } from './diagnostics';
import type { StepCatalogEntry } from '@/converter/catalog-types';

const LANGUAGE_ID = 'filemaker-script';
let registered = false;

export function registerFileMakerLanguage(
  catalog?: StepCatalogEntry[],
): void {
  if (registered) return;
  registered = true;

  monaco.languages.register({ id: LANGUAGE_ID });
  monaco.languages.setMonarchTokensProvider(LANGUAGE_ID, monarchLanguage);
  monaco.languages.setLanguageConfiguration(LANGUAGE_ID, languageConfiguration);

  monaco.editor.defineTheme('filemaker-dark', filemakerDarkTheme);

  if (catalog && catalog.length > 0) {
    monaco.languages.registerCompletionItemProvider(
      LANGUAGE_ID,
      createCompletionProvider(catalog),
    );
  }
}

export function attachDiagnostics(
  editor: monaco.editor.IStandaloneCodeEditor,
  catalog?: StepCatalogEntry[],
): monaco.IDisposable {
  return createDiagnosticsProvider(editor, catalog ?? []);
}

export { LANGUAGE_ID };
