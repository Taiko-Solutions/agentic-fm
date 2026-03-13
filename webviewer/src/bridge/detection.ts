/**
 * Detect the runtime environment.
 */

/** Running inside a FileMaker web viewer */
export function isFileMakerWebViewer(): boolean {
  return typeof window.FileMaker !== 'undefined';
}

/** Running in a standard browser (development mode) */
export function isStandaloneBrowser(): boolean {
  return !isFileMakerWebViewer();
}

/**
 * Get the WebKit version if available.
 * FileMaker's web viewer uses WebKit on macOS.
 */
export function getWebKitVersion(): string | null {
  const match = navigator.userAgent.match(/AppleWebKit\/([\d.]+)/);
  return match ? match[1] : null;
}
