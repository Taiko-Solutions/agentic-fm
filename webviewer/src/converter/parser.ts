/**
 * Line parser for human-readable FileMaker script format.
 *
 * Parses lines like:
 *   # comment text
 *   // Disabled Step [ params ]
 *   Set Variable [ $name ; expression ]
 *   If [ condition ]
 *   Go to Layout [ "LayoutName" ]
 */

export interface ParsedLine {
  /** Original line text */
  raw: string;
  /** Line number (1-based) */
  lineNumber: number;
  /** Whether step is disabled (// prefix) */
  disabled: boolean;
  /** Whether this is a comment (# prefix) */
  isComment: boolean;
  /** Comment text (for # comments) */
  commentText?: string;
  /** Step name (e.g. "Set Variable", "If") */
  stepName: string;
  /** Raw content inside brackets, or empty string */
  bracketContent: string;
  /** Parsed parameters (semicolon-separated inside brackets) */
  params: string[];
  /** Indentation level (spaces/tabs) */
  indent: number;
}

/** Parse a single line of HR script text */
export function parseLine(raw: string, lineNumber: number): ParsedLine {
  const trimmed = raw.trimStart();
  const indent = raw.length - trimmed.length;

  // Empty line
  if (!trimmed) {
    return {
      raw, lineNumber, disabled: false, isComment: false,
      stepName: '', bracketContent: '', params: [], indent,
    };
  }

  // Comment: # ...
  if (trimmed.startsWith('#')) {
    const commentText = trimmed.substring(1).trim();
    return {
      raw, lineNumber, disabled: false, isComment: true,
      commentText, stepName: '# (comment)', bracketContent: '',
      params: [], indent,
    };
  }

  // Disabled step: // ...
  let disabled = false;
  let workText = trimmed;
  if (trimmed.startsWith('//')) {
    disabled = true;
    workText = trimmed.substring(2).trim();
  }

  // Extract step name and bracket content
  const bracketIdx = findTopLevelBracket(workText);

  let stepName: string;
  let bracketContent = '';
  let params: string[] = [];

  if (bracketIdx >= 0) {
    stepName = workText.substring(0, bracketIdx).trim();
    // Extract content between outermost [ and ]
    const closeBracket = findMatchingBracket(workText, bracketIdx);
    if (closeBracket >= 0) {
      bracketContent = workText.substring(bracketIdx + 1, closeBracket).trim();
      params = splitParams(bracketContent);
    } else {
      bracketContent = workText.substring(bracketIdx + 1).trim();
      params = splitParams(bracketContent);
    }
  } else {
    stepName = workText.trim();
  }

  return {
    raw, lineNumber, disabled, isComment: false,
    stepName, bracketContent, params, indent,
  };
}

/** Parse all lines of HR script text */
export function parseScript(text: string): ParsedLine[] {
  return text.split('\n').map((line, i) => parseLine(line, i + 1));
}

/**
 * Find the first top-level '[' that starts the parameter list.
 * Skips brackets inside quotes.
 */
function findTopLevelBracket(text: string): number {
  let inQuote = false;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '"') inQuote = !inQuote;
    if (!inQuote && text[i] === '[') return i;
  }
  return -1;
}

/**
 * Find the matching closing ']' for an opening '['.
 * Handles nested brackets and quoted strings.
 */
function findMatchingBracket(text: string, openIdx: number): number {
  let depth = 0;
  let inQuote = false;
  for (let i = openIdx; i < text.length; i++) {
    if (text[i] === '"') inQuote = !inQuote;
    if (inQuote) continue;
    if (text[i] === '[') depth++;
    if (text[i] === ']') {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

/**
 * Split bracket content by semicolons, respecting:
 * - Quoted strings
 * - Nested parentheses (for function calls)
 * - Nested brackets
 */
function splitParams(content: string): string[] {
  const params: string[] = [];
  let current = '';
  let inQuote = false;
  let parenDepth = 0;
  let bracketDepth = 0;

  for (let i = 0; i < content.length; i++) {
    const ch = content[i];

    if (ch === '"') {
      inQuote = !inQuote;
      current += ch;
      continue;
    }

    if (inQuote) {
      current += ch;
      continue;
    }

    if (ch === '(') parenDepth++;
    if (ch === ')') parenDepth--;
    if (ch === '[') bracketDepth++;
    if (ch === ']') bracketDepth--;

    if (ch === ';' && parenDepth === 0 && bracketDepth === 0) {
      params.push(current.trim());
      current = '';
      continue;
    }

    current += ch;
  }

  if (current.trim()) {
    params.push(current.trim());
  }

  return params;
}

/**
 * Extract a labeled parameter value.
 * e.g. extractLabel("Parameter: $id", "Parameter") => "$id"
 * e.g. extractLabel("With dialog: Off", "With dialog") => "Off"
 */
export function extractLabel(param: string, label: string): string | null {
  const prefix = label + ':';
  const idx = param.indexOf(prefix);
  if (idx < 0) return null;
  return param.substring(idx + prefix.length).trim();
}

/** Strip surrounding quotes from a string */
export function unquote(s: string): string {
  if (s.startsWith('"') && s.endsWith('"') && s.length >= 2) {
    return s.substring(1, s.length - 1);
  }
  return s;
}
