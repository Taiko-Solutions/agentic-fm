import { useState, useEffect, useRef, useCallback } from 'preact/hooks';
import { searchScripts, loadScript, fetchContext } from '@/api/client';
import type { ScriptSearchResult } from '@/api/client';
import { isFileMakerWebViewer, requestContext } from '@/bridge/fm-bridge';
import type { FMContext } from '@/context/types';

export interface LoadScriptOptions {
  resetChat: boolean;
}

interface LoadScriptDialogProps {
  context: FMContext | null;
  editorContent: string;
  onLoad: (hr: string, scriptName: string, options: LoadScriptOptions) => void;
  onContextUpdate: (ctx: FMContext) => void;
  onClose: () => void;
}

export function LoadScriptDialog({ context, editorContent, onLoad, onContextUpdate, onClose }: LoadScriptDialogProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ScriptSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<ScriptSearchResult | null>(null);
  const [error, setError] = useState('');
  const [resetChat, setResetChat] = useState(true);
  const [contextPushed, setContextPushed] = useState(false);
  const [waitingForContext, setWaitingForContext] = useState(false);
  const contextHashRef = useRef<string | null>(null);
  const inFileMaker = isFileMakerWebViewer();

  // Poll /api/context while waiting for FileMaker to push a new context.
  // Comparing JSON hashes detects any change regardless of how the file was written.
  useEffect(() => {
    if (!waitingForContext) return;
    const interval = setInterval(async () => {
      try {
        const fresh = await fetchContext();
        const newHash = JSON.stringify(fresh);
        if (contextHashRef.current !== null && newHash !== contextHashRef.current) {
          onContextUpdate(fresh);
          setContextPushed(true);
          setWaitingForContext(false);
        }
      } catch {
        // Server unreachable — keep waiting
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [waitingForContext, onContextUpdate]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const resultRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(-1);
    resultRefs.current = [];
  }, [results]);

  // Minimum characters before triggering a search (numeric queries are exempt — ID lookup)
  const MIN_SEARCH_CHARS = 3;

  // Debounced search
  const handleInput = useCallback((value: string) => {
    setQuery(value);
    setError('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = value.trim();
    const isNumeric = /^\d+$/.test(trimmed);
    if (!trimmed || (!isNumeric && trimmed.length < MIN_SEARCH_CHARS)) {
      setResults([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchScripts(trimmed);
        setResults(res);
      } catch (err) {
        setResults([]);
        setError(`Search failed: ${err instanceof Error ? err.message : String(err)}`);
      } finally {
        setSearching(false);
      }
    }, 300);
  }, []);

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
      onLoad(content, result.name ?? script.name, { resetChat });
    } catch {
      setError('Failed to load script');
      setLoading(false);
    }
  }, [onLoad, resetChat]);

  const handleSelect = useCallback((script: ScriptSearchResult) => {
    const hasContent = editorContent.trim().length > 0;
    setContextPushed(false);
    setWaitingForContext(false);
    contextHashRef.current = null;
    if (hasContent) {
      setConfirmTarget(script);
    } else {
      doLoad(script);
    }
  }, [editorContent, doLoad]);

  // Keyboard navigation + Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (confirmTarget) {
          setConfirmTarget(null);
        } else {
          onClose();
        }
        return;
      }
      if (confirmTarget) {
        if (e.key === 'Enter') {
          e.preventDefault();
          doLoad(confirmTarget);
        }
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(i => {
          const next = Math.min(i + 1, results.length - 1);
          resultRefs.current[next]?.scrollIntoView({ block: 'nearest' });
          return next;
        });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(i => {
          const next = Math.max(i - 1, 0);
          resultRefs.current[next]?.scrollIntoView({ block: 'nearest' });
          return next;
        });
      } else if (e.key === 'Enter' && selectedIndex >= 0 && results[selectedIndex]) {
        e.preventDefault();
        handleSelect(results[selectedIndex]);
      }
    };
    window.addEventListener('keydown', handleKey, { capture: true });
    return () => window.removeEventListener('keydown', handleKey, { capture: true });
  }, [onClose, confirmTarget, results, selectedIndex, handleSelect, doLoad]);

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
            placeholder="Search by name (3+ chars) or script ID..."
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

          {!loading && !searching && query.trim() && !(/^\d+$/.test(query.trim())) && query.trim().length < MIN_SEARCH_CHARS && (
            <div class="text-neutral-500 text-xs py-4 text-center">Type at least {MIN_SEARCH_CHARS} characters to search</div>
          )}

          {!loading && !searching && query.trim() && ((/^\d+$/.test(query.trim())) || query.trim().length >= MIN_SEARCH_CHARS) && results.length === 0 && !error && (
            <div class="text-neutral-500 text-xs py-4 text-center">No scripts found</div>
          )}

          {!loading && !searching && results.length > 0 && (
            <div class="space-y-0.5">
              {results.map((script, i) => (
                <button
                  key={script.id}
                  ref={(el) => { resultRefs.current[i] = el; }}
                  onClick={() => handleSelect(script)}
                  onMouseEnter={() => setSelectedIndex(i)}
                  class={`w-full text-left px-3 py-2 rounded transition-colors group ${
                    selectedIndex === i ? 'bg-neutral-700' : 'hover:bg-neutral-700'
                  }`}
                >
                  <div class="flex items-center justify-between">
                    <span class={`text-sm ${selectedIndex === i ? 'text-white' : 'text-neutral-200 group-hover:text-white'}`}>
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
          <div class="px-4 py-3 border-t border-neutral-700 space-y-3">
            <p class="text-xs text-amber-400">
              Loading <span class="font-medium text-amber-300">"{confirmTarget.name}"</span> will replace the current editor content.
            </p>

            {/* Reset chat option */}
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={resetChat}
                onChange={(e) => setResetChat((e.target as HTMLInputElement).checked)}
                class="rounded"
              />
              <span class="text-xs text-neutral-300">Reset AI chat history</span>
            </label>

            {/* Context push */}
            <div class="space-y-1">
              {inFileMaker ? (
                <div class="flex items-center gap-2">
                  <button
                    onClick={() => {
                      contextHashRef.current = JSON.stringify(context);
                      setWaitingForContext(true);
                      setContextPushed(false);
                      requestContext();
                    }}
                    class={`px-2 py-1 rounded text-xs transition-colors ${
                      contextPushed
                        ? 'bg-green-700 text-green-200 cursor-default'
                        : waitingForContext
                          ? 'bg-neutral-700 text-neutral-400 cursor-wait'
                          : 'bg-neutral-600 hover:bg-neutral-500 text-neutral-200'
                    }`}
                    disabled={contextPushed || waitingForContext}
                  >
                    {contextPushed
                      ? '✓ Context updated'
                      : waitingForContext
                        ? 'Waiting for FileMaker…'
                        : 'Push Context from FileMaker'}
                  </button>
                  {!contextPushed && !waitingForContext && (
                    <span class="text-xs text-neutral-500">recommended when switching layouts</span>
                  )}
                </div>
              ) : (
                <p class="text-xs text-neutral-500">
                  Run <span class="text-neutral-400 font-mono">Push Context</span> in FileMaker before loading to update field and layout references.
                </p>
              )}
            </div>

            <div class="flex gap-2 justify-end pt-1">
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
                Load Script
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
