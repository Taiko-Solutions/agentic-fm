import type * as monaco from 'monaco-editor';

/**
 * Monarch tokenizer for human-readable FileMaker script format.
 *
 * Reference: the sanitized output from fm-xml-export-exploder's sanitize.rs
 *
 * Format:
 *   # comment
 *   // disabled step
 *   StepName [ param ; param ]
 *   If [ condition ]
 *     nested steps (indented)
 *   End If
 */

const controlKeywords = [
  'If', 'Else If', 'Else', 'End If',
  'Loop', 'Exit Loop If', 'End Loop',
  'Exit Script',
  'Perform Script', 'Perform Script on Server',
  'Allow User Abort', 'Set Error Capture',
  'Halt Script',
];

const controlKeywordsPattern = controlKeywords
  .map(kw => kw.replace(/\s+/g, '\\s+'))
  .join('|');

export const monarchLanguage: monaco.languages.IMonarchLanguage = {
  defaultToken: '',
  ignoreCase: false,

  // Bracket and delimiter tokens
  brackets: [
    { open: '[', close: ']', token: 'delimiter.bracket' },
    { open: '(', close: ')', token: 'delimiter.paren' },
  ],

  // Use these for word detection
  wordPattern: /[a-zA-Z_$~][a-zA-Z0-9_$.~]*/,

  tokenizer: {
    root: [
      // Full-line comment: # ...
      [/^[ \t]*#.*$/, 'comment'],

      // Disabled step: // ...
      [/^[ \t]*\/\/.*$/, 'comment.disabled'],

      // Control keywords (must come before general step matching)
      [new RegExp(`^([ \\t]*)(${controlKeywordsPattern})(?=\\s*\\[|\\s*$)`), ['white', 'keyword.control']],

      // General step name at start of line (everything before [ or EOL)
      [/^[ \t]*[A-Z][A-Za-z0-9/ ]*(?=\s*\[|\s*$)/, 'keyword.step'],

      // Include bracket contents
      { include: '@bracketContent' },

      // Whitespace
      [/\s+/, 'white'],
    ],

    bracketContent: [
      // Opening bracket
      [/\[/, 'delimiter.bracket', '@insideBrackets'],
    ],

    insideBrackets: [
      // Closing bracket
      [/\]/, 'delimiter.bracket', '@pop'],

      // Strings
      [/"/, 'string', '@string'],

      // Global variables $$
      [/\$\$[a-zA-Z_~][a-zA-Z0-9_.~]*/, 'variable.global'],

      // Local variables $
      [/\$[a-zA-Z_~][a-zA-Z0-9_.~]*/, 'variable.local'],

      // Let variables ~
      [/~[a-zA-Z_][a-zA-Z0-9_.]*/, 'variable.let'],

      // Field references: Table::Field
      [/[A-Za-z_][A-Za-z0-9_ ]*::[A-Za-z_][A-Za-z0-9_ ]*/, 'field.reference'],

      // Parameter labels: "Layout:", "Parameter:", "With dialog:", etc.
      [/[A-Za-z][A-Za-z ]*:(?=\s)/, 'parameter.label'],

      // Constants
      [/\b(True|False|On|Off|None|All)\b/, 'constant'],

      // FM functions: Get ( ... ), Let ( ... ), etc.
      [/\b[A-Z][a-zA-Z]+\s*\(/, 'function'],

      // Numbers
      [/\b\d+(\.\d+)?\b/, 'number'],

      // Semicolon separator
      [/;/, 'delimiter'],

      // Operators
      [/[=<>≠≤≥&+-/*^]/, 'operator'],

      // Parentheses
      [/[()]/, 'delimiter.paren'],

      // Other text
      [/./, ''],
    ],

    string: [
      [/[^"]+/, 'string'],
      [/"/, 'string', '@pop'],
    ],
  },
};

export const languageConfiguration: monaco.languages.LanguageConfiguration = {
  comments: {
    lineComment: '#',
  },
  brackets: [
    ['[', ']'],
    ['(', ')'],
  ],
  autoClosingPairs: [
    { open: '[', close: ']' },
    { open: '(', close: ')' },
    { open: '"', close: '"' },
  ],
  surroundingPairs: [
    { open: '[', close: ']' },
    { open: '(', close: ')' },
    { open: '"', close: '"' },
  ],
  indentationRules: {
    increaseIndentPattern: /^\s*(If|Else If|Else|Loop)\b/,
    decreaseIndentPattern: /^\s*(End If|Else If|Else|End Loop)\b/,
  },
  folding: {
    markers: {
      start: /^\s*(If|Loop)\b/,
      end: /^\s*(End If|End Loop)\b/,
    },
  },
};
