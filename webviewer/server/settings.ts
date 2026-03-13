/**
 * Server-side settings manager.
 * Stores AI provider config in webviewer/.env.local (gitignored by Vite convention).
 *
 * Format:
 *   AI_PROVIDER=anthropic
 *   AI_MODEL=claude-sonnet-4-20250514
 *   AI_KEY_ANTHROPIC=sk-ant-...
 *   AI_KEY_OPENAI=sk-...
 */

import fs from 'node:fs';
import path from 'node:path';

const ENV_FILE = path.resolve(process.cwd(), '.env.local');

export interface AISettings {
  provider: string;
  model: string;
  /** Which providers have keys configured (never exposes actual values) */
  configuredProviders: string[];
  /** Keyword used to mark script comments as AI-actionable prompts */
  promptMarker: string;
}

interface FullSettings {
  provider: string;
  model: string;
  keys: Record<string, string>;
  promptMarker: string;
}

/** Read settings from .env.local */
function readEnv(): FullSettings {
  const settings: FullSettings = {
    provider: 'anthropic',
    model: '',
    keys: {},
    promptMarker: 'prompt',
  };

  try {
    const content = fs.readFileSync(ENV_FILE, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eq = trimmed.indexOf('=');
      if (eq < 0) continue;
      const key = trimmed.substring(0, eq).trim();
      const value = trimmed.substring(eq + 1).trim();

      if (key === 'AI_PROVIDER') settings.provider = value;
      else if (key === 'AI_MODEL') settings.model = value;
      else if (key === 'AI_PROMPT_MARKER') settings.promptMarker = value;
      else if (key.startsWith('AI_KEY_')) {
        const providerId = key.substring('AI_KEY_'.length).toLowerCase();
        settings.keys[providerId] = value;
      }
    }
  } catch {
    // File doesn't exist yet — defaults are fine
  }

  return settings;
}

/** Write settings to .env.local, preserving any non-AI_ lines */
function writeEnv(settings: FullSettings): void {
  const existingLines: string[] = [];
  try {
    const content = fs.readFileSync(ENV_FILE, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      // Keep non-AI lines and comments
      if (trimmed.startsWith('#') || (!trimmed.startsWith('AI_') && trimmed)) {
        existingLines.push(line);
      }
    }
  } catch {
    // File doesn't exist
  }

  const aiLines: string[] = [
    `AI_PROVIDER=${settings.provider}`,
    `AI_MODEL=${settings.model}`,
    `AI_PROMPT_MARKER=${settings.promptMarker}`,
  ];

  for (const [providerId, key] of Object.entries(settings.keys)) {
    if (key) {
      aiLines.push(`AI_KEY_${providerId.toUpperCase()}=${key}`);
    }
  }

  const output = [...existingLines, ...aiLines].join('\n') + '\n';
  fs.writeFileSync(ENV_FILE, output, 'utf-8');
}

/** Providers that use CLI auth and never need an API key */
const KEYLESS_PROVIDERS = ['claude-code'];

/** Get settings (safe for client — no key values) */
export function getSettings(): AISettings {
  const full = readEnv();
  const keyedProviders = Object.entries(full.keys)
    .filter(([, v]) => v.length > 0)
    .map(([k]) => k);
  return {
    provider: full.provider,
    model: full.model,
    configuredProviders: [...keyedProviders, ...KEYLESS_PROVIDERS],
    promptMarker: full.promptMarker,
  };
}

/** Update settings. apiKey is optional — only updates if provided. */
export function updateSettings(update: {
  provider?: string;
  model?: string;
  apiKey?: string;
  apiKeyProvider?: string;
  promptMarker?: string;
}): AISettings {
  const full = readEnv();

  if (update.provider) full.provider = update.provider;
  if (update.model) full.model = update.model;
  if (update.promptMarker !== undefined) full.promptMarker = update.promptMarker || 'prompt';
  if (update.apiKey !== undefined && update.apiKeyProvider) {
    full.keys[update.apiKeyProvider] = update.apiKey;
  }

  writeEnv(full);
  return getSettings();
}

/** Get the API key for a given provider (server-side only, never exposed to client) */
export function getApiKeyForProvider(providerId: string): string {
  const full = readEnv();
  return full.keys[providerId] ?? '';
}

/** Get the active provider ID and model */
export function getActiveConfig(): { provider: string; model: string } {
  const full = readEnv();
  return { provider: full.provider, model: full.model };
}
