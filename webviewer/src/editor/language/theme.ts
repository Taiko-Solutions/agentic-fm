import type * as monaco from 'monaco-editor';

export const filemakerDarkTheme: monaco.editor.IStandaloneThemeData = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    // Comments
    { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
    { token: 'comment.disabled', foreground: '6A9955', fontStyle: 'italic strikethrough' },

    // Keywords
    { token: 'keyword.control', foreground: 'C586C0', fontStyle: 'bold' },
    { token: 'keyword.step', foreground: '569CD6' },

    // Variables
    { token: 'variable.local', foreground: '9CDCFE' },
    { token: 'variable.global', foreground: '4EC9B0', fontStyle: 'bold' },
    { token: 'variable.let', foreground: 'B5CEA8' },

    // Field references
    { token: 'field.reference', foreground: 'DCDCAA' },

    // Strings
    { token: 'string', foreground: 'CE9178' },

    // Parameter labels
    { token: 'parameter.label', foreground: '808080' },

    // Constants
    { token: 'constant', foreground: '569CD6', fontStyle: 'bold' },

    // Functions
    { token: 'function', foreground: 'DCDCAA' },

    // Numbers
    { token: 'number', foreground: 'B5CEA8' },

    // Operators & delimiters
    { token: 'operator', foreground: 'D4D4D4' },
    { token: 'delimiter', foreground: 'D4D4D4' },
    { token: 'delimiter.bracket', foreground: 'FFD700' },
    { token: 'delimiter.paren', foreground: 'D4D4D4' },
  ],
  colors: {
    'editor.background': '#1E1E1E',
    'editor.foreground': '#D4D4D4',
    'editor.lineHighlightBackground': '#2A2D2E',
    'editorCursor.foreground': '#AEAFAD',
    'editor.selectionBackground': '#264F78',
    'editor.inactiveSelectionBackground': '#3A3D41',
  },
};
