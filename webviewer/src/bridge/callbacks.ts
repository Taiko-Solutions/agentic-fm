/**
 * Register global callback functions that FileMaker can invoke
 * via "Perform JavaScript in Web Viewer".
 *
 * These are set up in App.tsx and wired to React state setters.
 * This module provides type definitions and documentation.
 */

declare global {
  interface Window {
    /** Push CONTEXT.json data from FileMaker */
    pushContext?: (jsonString: string) => void;
    /** Load script content into the editor */
    loadScript?: (content: string, format?: string) => void;
    /** Notify that clipboard operation completed */
    onClipboardReady?: () => void;
  }
}

export {};
