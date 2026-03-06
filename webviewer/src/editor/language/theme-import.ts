import type { ThemeColors } from './themes';

interface VSCodeTokenColor {
  scope?: string | string[];
  settings?: { foreground?: string; background?: string; fontStyle?: string };
}

interface VSCodeTheme {
  tokenColors?: VSCodeTokenColor[];
  colors?: Record<string, string>;
}

// TextMate scope → ThemeColors category mapping
// Each category lists scopes in priority order (first match wins)
const SCOPE_MAP: Array<{ key: keyof ThemeColors; scopes: string[] }> = [
  { key: 'comments', scopes: ['comment.line', 'comment.block', 'comment'] },
  { key: 'controlFlow', scopes: ['keyword.control.flow', 'keyword.control'] },
  { key: 'scriptSteps', scopes: ['storage.type', 'keyword.other', 'keyword'] },
  { key: 'variables', scopes: ['variable.other.readwrite', 'variable.parameter', 'variable.other', 'variable'] },
  { key: 'globals', scopes: ['variable.other.readwrite.global', 'variable.other.global'] },
  { key: 'fields', scopes: ['entity.name.tag', 'constant.other', 'support.class'] },
  { key: 'strings', scopes: ['string.quoted.double', 'string.quoted.single', 'string.quoted', 'string'] },
  { key: 'functions', scopes: ['meta.function-call', 'support.function', 'entity.name.function'] },
  { key: 'constants', scopes: ['constant.language', 'support.constant', 'constant'] },
  { key: 'numbers', scopes: ['constant.numeric.integer', 'constant.numeric.float', 'constant.numeric'] },
  { key: 'operators', scopes: ['keyword.operator', 'punctuation.separator'] },
  { key: 'brackets', scopes: ['punctuation.definition', 'meta.brace'] },
];

export function importVSCodeTheme(json: string): Partial<ThemeColors> {
  let theme: VSCodeTheme;
  try {
    theme = JSON.parse(json);
  } catch {
    throw new Error('Invalid JSON');
  }

  const tokenColors = theme.tokenColors;
  if (!tokenColors || !Array.isArray(tokenColors)) {
    throw new Error('No tokenColors array found — is this a VS Code / TextMate theme?');
  }

  // Build a flat scope → color lookup
  const scopeColors = new Map<string, string>();
  for (const rule of tokenColors) {
    const color = rule.settings?.foreground;
    if (!color) continue;
    const scopes = Array.isArray(rule.scope) ? rule.scope : rule.scope ? [rule.scope] : [];
    for (const scope of scopes) {
      scopeColors.set(scope.trim(), color);
    }
  }

  const result: Partial<ThemeColors> = {};
  for (const { key, scopes } of SCOPE_MAP) {
    for (const scope of scopes) {
      // Try exact match first, then prefix match
      const exact = scopeColors.get(scope);
      if (exact) {
        result[key] = normalizeColor(exact);
        break;
      }
      // Prefix match: find any scope that starts with our scope
      for (const [s, c] of scopeColors) {
        if (s.startsWith(scope + '.') || s === scope) {
          result[key] = normalizeColor(c);
          break;
        }
      }
      if (result[key]) break;
    }
  }

  return result;
}

interface MonacoThemeRule {
  token: string;
  foreground?: string;
}

interface MonacoThemeData {
  rules?: MonacoThemeRule[];
}

const MONACO_TOKEN_MAP: Array<{ key: keyof ThemeColors; tokens: string[] }> = [
  { key: 'comments', tokens: ['comment', 'comment.disabled'] },
  { key: 'controlFlow', tokens: ['keyword.control'] },
  { key: 'scriptSteps', tokens: ['keyword.step'] },
  { key: 'variables', tokens: ['variable.local', 'variable.let'] },
  { key: 'globals', tokens: ['variable.global'] },
  { key: 'fields', tokens: ['field.reference'] },
  { key: 'strings', tokens: ['string'] },
  { key: 'functions', tokens: ['function'] },
  { key: 'constants', tokens: ['constant'] },
  { key: 'numbers', tokens: ['number'] },
  { key: 'operators', tokens: ['operator'] },
  { key: 'brackets', tokens: ['delimiter.bracket'] },
];

export function importMonacoTheme(json: string): Partial<ThemeColors> {
  let theme: MonacoThemeData;
  try {
    theme = JSON.parse(json);
  } catch {
    throw new Error('Invalid JSON');
  }

  if (!theme.rules || !Array.isArray(theme.rules)) {
    throw new Error('No rules array found — is this a Monaco theme?');
  }

  const tokenColors = new Map<string, string>();
  for (const rule of theme.rules) {
    if (rule.foreground) {
      tokenColors.set(rule.token, '#' + rule.foreground.replace('#', ''));
    }
  }

  const result: Partial<ThemeColors> = {};
  for (const { key, tokens } of MONACO_TOKEN_MAP) {
    for (const token of tokens) {
      const color = tokenColors.get(token);
      if (color) {
        result[key] = normalizeColor(color);
        break;
      }
    }
  }

  return result;
}

function normalizeColor(color: string): string {
  const hex = color.replace('#', '');
  // Expand 3-char hex to 6-char
  if (hex.length === 3) {
    return '#' + hex.split('').map(c => c + c).join('');
  }
  // Strip alpha channel from 8-char hex
  if (hex.length === 8) {
    return '#' + hex.slice(0, 6);
  }
  return '#' + hex.slice(0, 6);
}
