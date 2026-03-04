import { useState, useEffect } from 'preact/hooks';
import { listProviders, getProvider } from '../providers/registry';
import { fetchSettings, saveSettings } from '@/api/client';

interface AISettingsProps {
  onClose: () => void;
}

export function AISettings({ onClose }: AISettingsProps) {
  const providers = listProviders();
  const [providerId, setProviderId] = useState('anthropic');
  const [model, setModel] = useState('');
  const [apiKey, setKey] = useState('');
  const [promptMarker, setPromptMarker] = useState('prompt');
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);

  // Load current settings from server
  useEffect(() => {
    fetchSettings()
      .then((s) => {
        setProviderId(s.provider);
        setModel(s.model);
        setPromptMarker(s.promptMarker || 'prompt');
        setConfiguredProviders(s.configuredProviders);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  // Update model when provider changes
  useEffect(() => {
    const provider = getProvider(providerId);
    if (provider && (!model || !provider.models.includes(model))) {
      setModel(provider.defaultModel);
    }
  }, [providerId]);

  const handleSave = async () => {
    setSaving(true);
    setStatus('');
    try {
      // Save provider + model + prompt marker
      const result = await saveSettings({ provider: providerId, model, promptMarker });

      // Save API key if entered
      if (apiKey) {
        const keyResult = await saveSettings({ apiKey, apiKeyProvider: providerId });
        setConfiguredProviders(keyResult.configuredProviders);
      } else {
        setConfiguredProviders(result.configuredProviders);
      }

      setKey('');
      setStatus('Saved');
    } catch {
      setStatus('Error saving');
    } finally {
      setSaving(false);
    }
  };

  const currentProvider = getProvider(providerId);
  const hasKey = configuredProviders.includes(providerId);
  const needsKey = currentProvider?.requiresKey !== false;

  if (loading) {
    return (
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div class="bg-neutral-800 rounded-lg shadow-xl w-96 p-6 text-neutral-400 text-sm">
          Loading settings...
        </div>
      </div>
    );
  }

  return (
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-neutral-800 rounded-lg shadow-xl w-96 max-w-[90vw]">
        <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-700">
          <h2 class="text-sm font-semibold text-neutral-200">AI Settings</h2>
          <button onClick={onClose} class="text-neutral-400 hover:text-neutral-200 text-lg">&times;</button>
        </div>

        <div class="p-4 space-y-4">
          {/* Provider */}
          <div>
            <label class="block text-xs text-neutral-400 mb-1">Provider</label>
            <select
              value={providerId}
              onChange={(e) => setProviderId((e.target as HTMLSelectElement).value)}
              class="w-full bg-neutral-700 text-neutral-200 text-sm rounded px-2 py-1.5 outline-none"
            >
              {providers.map(p => (
                <option key={p.id} value={p.id}>
                  {p.displayName}
                  {p.requiresKey === false
                    ? ' (CLI)'
                    : configuredProviders.includes(p.id) ? ' (key set)' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Model */}
          <div>
            <label class="block text-xs text-neutral-400 mb-1">Model</label>
            <select
              value={model}
              onChange={(e) => setModel((e.target as HTMLSelectElement).value)}
              class="w-full bg-neutral-700 text-neutral-200 text-sm rounded px-2 py-1.5 outline-none"
            >
              {currentProvider?.models.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {/* API Key — hidden for providers that use CLI auth */}
          {needsKey ? (
            <div>
              <label class="block text-xs text-neutral-400 mb-1">
                API Key
                {hasKey && <span class="text-green-400 ml-1">(configured)</span>}
              </label>
              <input
                type="password"
                value={apiKey}
                onInput={(e) => setKey((e.target as HTMLInputElement).value)}
                placeholder={hasKey ? 'Enter new key to replace' : `Enter ${currentProvider?.displayName} API key`}
                class="w-full bg-neutral-700 text-neutral-200 text-sm rounded px-2 py-1.5 outline-none placeholder:text-neutral-500"
              />
              <p class="text-xs text-neutral-500 mt-1">
                Stored in <code>.env.local</code> on the server. Never sent to the browser.
              </p>
            </div>
          ) : (
            <div class="bg-neutral-700/50 rounded px-3 py-2">
              <p class="text-xs text-green-400">Uses your Claude Code login session</p>
              <p class="text-xs text-neutral-500 mt-1">
                No API key needed. Make sure you are logged in via <code>claude login</code>.
              </p>
            </div>
          )}

          {/* Prompt Marker */}
          <div>
            <label class="block text-xs text-neutral-400 mb-1">Prompt marker keyword</label>
            <input
              type="text"
              value={promptMarker}
              onInput={(e) => setPromptMarker((e.target as HTMLInputElement).value)}
              placeholder="prompt"
              class="w-full bg-neutral-700 text-neutral-200 text-sm rounded px-2 py-1.5 outline-none placeholder:text-neutral-500"
            />
            <p class="text-xs text-neutral-500 mt-1">
              Script comments starting with <code># {promptMarker}:</code> are treated as AI instructions.
            </p>
          </div>
        </div>

        <div class="flex items-center justify-between px-4 py-3 border-t border-neutral-700">
          {status && (
            <span class={`text-xs ${status === 'Saved' ? 'text-green-400' : 'text-red-400'}`}>
              {status}
            </span>
          )}
          <div class="flex gap-2 ml-auto">
            <button
              onClick={onClose}
              class="px-3 py-1 rounded text-xs bg-neutral-700 hover:bg-neutral-600 text-neutral-300"
            >
              Close
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              class="px-3 py-1 rounded text-xs bg-blue-700 hover:bg-blue-600 text-white disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
