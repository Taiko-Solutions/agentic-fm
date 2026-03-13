/**
 * Auto-save and restore editor drafts.
 *
 * Primary: localStorage (fast, survives webviewer reloads in FileMaker)
 * Fallback: server-side file via /api/autosave (survives localStorage wipe)
 */

const LS_KEY = 'fm-autosave';
const DEBOUNCE_MS = 2000;

export interface AutosaveDraft {
  hr: string;
  scriptName: string;
  timestamp: number;
}

let debounceTimer: ReturnType<typeof setTimeout> | undefined;

/** Save draft to both localStorage and server, debounced */
export function saveDraft(hr: string, scriptName: string): void {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    const draft: AutosaveDraft = { hr, scriptName, timestamp: Date.now() };

    try {
      localStorage.setItem(LS_KEY, JSON.stringify(draft));
    } catch (e) {
      console.warn('[autosave] localStorage failed:', e);
    }

    console.log(`[autosave] saving to server (${hr.length} chars, name="${scriptName}")`);
    saveToServer(draft).catch((e) => {
      console.warn('[autosave] server save failed:', e);
    });
  }, DEBOUNCE_MS);
}

/** Restore draft: try localStorage first, then server fallback */
export async function restoreDraft(): Promise<AutosaveDraft | null> {
  // Try localStorage
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const draft = JSON.parse(raw) as AutosaveDraft;
      if (draft.hr && draft.timestamp) return draft;
    }
  } catch { /* corrupted or unavailable */ }

  // Fallback to server
  try {
    return await loadFromServer();
  } catch {
    return null;
  }
}

/** Clear saved draft from both stores */
export function clearDraft(): void {
  try { localStorage.removeItem(LS_KEY); } catch {}
  clearFromServer().catch(() => {});
}

// --- Server endpoints ---

async function saveToServer(draft: AutosaveDraft): Promise<void> {
  await fetch('/api/autosave', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draft),
  });
}

async function loadFromServer(): Promise<AutosaveDraft | null> {
  const res = await fetch('/api/autosave');
  if (!res.ok) return null;
  const draft = await res.json();
  if (draft.hr && draft.timestamp) return draft as AutosaveDraft;
  return null;
}

async function clearFromServer(): Promise<void> {
  await fetch('/api/autosave', { method: 'DELETE' });
}
