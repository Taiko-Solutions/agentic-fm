import { useState, useEffect, useRef, useCallback } from 'preact/hooks';
import { searchScripts, loadScript } from '@/api/client';
import type { ScriptSearchResult } from '@/api/client';

interface LoadScriptDialogProps {
  editorContent: string;
  onLoad: (hr: string, scriptName: string) => void;
  onClose: () => void;
}

export function LoadScriptDialog({ editorContent, onLoad, onClose }: LoadScriptDialogProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ScriptSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<ScriptSearchResult | null>(null);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (confirmTarget) {
          setConfirmTarget(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose, confirmTarget]);

  // Debounced search
  const handleInput = useCallback((value: string) => {
    setQuery(value);
    setError('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!value.trim()) {
      setResults([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchScripts(value.trim());
        setResults(res);
      } catch {
        setResults([]);
        setError('Search failed');
      } finally {
        setSearching(false);
      }
    }, 300);
  }, []);

  const handleSelect = useCallback((script: ScriptSearchResult) => {
    const hasContent = editorContent.trim().length > 0;
    if (hasContent) {
      setConfirmTarget(script);
    } else {
      doLoad(script);
    }
  }, [editorContent]);

  const doLoad = useCallback(async (script: ScriptSearchResult) => {
    setLoading(true);
    setError('');
    setConfirmTarget(null);
    try {
      const result = await loadScript(script.id, script.name);
      const content = result.hr ?? '';
      if (!content) {
        setError('No human-readable script found');
        setLoading(false);
        return;
      }
      onLoad(content, result.name ?? script.name);
    } catch {
      setError('Failed to load script');
      setLoading(false);
    }
  }, [onLoad]);

  const handleBackdropClick = useCallback((e: MouseEvent) => {
    if ((e.target as HTMLElement).dataset.backdrop) {
      onClose();
    }
  }, [onClose]);

  return (
    <div
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      data-backdrop="true"
      onClick={handleBackdropClick}
    >
      <div class="bg-neutral-800 rounded-lg shadow-xl w-[32rem] max-w-[90vw] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-700">
          <h2 class="text-sm font-semibold text-neutral-200">Load Script</h2>
          <button onClick={onClose} class="text-neutral-400 hover:text-neutral-200 text-lg">&times;</button>
        </div>

        {/* Search input */}
        <div class="px-4 pt-3 pb-2">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onInput={(e) => handleInput((e.target as HTMLInputElement).value)}
            placeholder="Enter script name or ID..."
            class="w-full bg-neutral-700 text-neutral-200 text-sm rounded px-3 py-2 outline-none placeholder:text-neutral-500 focus:ring-1 focus:ring-blue-500"
            disabled={loading}
          />
        </div>

        {/* Results */}
        <div class="flex-1 min-h-0 overflow-y-auto px-4 pb-3">
          {loading && (
            <div class="text-neutral-400 text-xs py-4 text-center">Loading script...</div>
          )}

          {!loading && searching && (
            <div class="text-neutral-400 text-xs py-4 text-center">Searching...</div>
          )}

          {!loading && !searching && error && (
            <div class="text-red-400 text-xs py-2">{error}</div>
          )}

          {!loading && !searching && query.trim() && results.length === 0 && !error && (
            <div class="text-neutral-500 text-xs py-4 text-center">No scripts found</div>
          )}

          {!loading && !searching && results.length > 0 && (
            <div class="space-y-0.5">
              {results.map(script => (
                <button
                  key={script.id}
                  onClick={() => handleSelect(script)}
                  class="w-full text-left px-3 py-2 rounded hover:bg-neutral-700 transition-colors group"
                >
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-neutral-200 group-hover:text-white">
                      {script.name}
                    </span>
                    <span class="text-xs text-neutral-500 ml-2 shrink-0">
                      ID {script.id}
                    </span>
                  </div>
                  {script.folder && (
                    <div class="text-xs text-neutral-500 mt-0.5">{script.folder}</div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Confirmation prompt */}
        {confirmTarget && (
          <div class="px-4 py-3 border-t border-neutral-700 bg-neutral-750">
            <p class="text-xs text-amber-400 mb-2">
              Loading a script will replace the current editor content. Continue?
            </p>
            <div class="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmTarget(null)}
                class="px-3 py-1 rounded text-xs bg-neutral-700 hover:bg-neutral-600 text-neutral-300"
              >
                Cancel
              </button>
              <button
                onClick={() => doLoad(confirmTarget)}
                class="px-3 py-1 rounded text-xs bg-blue-700 hover:bg-blue-600 text-white"
              >
                Replace
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
