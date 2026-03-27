import { CONTEXT_VERSION_CURRENT } from '@/context/types';

interface StatusBarProps {
  status: string;
  solution?: string;
  layout?: string;
  generatedAt?: string;
  contextVersion?: number;
  onDetail?: () => void;
}

export function StatusBar({ status, solution, layout, generatedAt, contextVersion, onDetail }: StatusBarProps) {
  const ageMs = generatedAt ? Date.now() - new Date(generatedAt).getTime() : null;
  const ageMin = ageMs !== null ? Math.floor(ageMs / 60000) : null;

  let contextIndicator: { label: string; className: string } | null = null;
  if (ageMin !== null && ageMin >= 5) {
    if (ageMin > 15) {
      contextIndicator = { label: `Context: stale (${ageMin}m)`, className: 'text-red-400' };
    } else {
      contextIndicator = { label: `Context: ${ageMin}m ago`, className: 'text-amber-400' };
    }
  }

  // Version check: missing or outdated Context() function
  const versionOutdated = generatedAt && (
    contextVersion === undefined || contextVersion < CONTEXT_VERSION_CURRENT
  );

  return (
    <div class="flex items-center gap-3 px-3 py-1 bg-blue-900 text-xs text-blue-200 select-none">
      <span>{status}</span>
      {onDetail && (
        <button
          onClick={onDetail}
          class="text-blue-400 hover:text-blue-200 underline underline-offset-2 transition-colors"
        >
          Details
        </button>
      )}
      <div class="flex-1" />
      {versionOutdated && (
        <span class="text-amber-400" title={`Expected context_version ${CONTEXT_VERSION_CURRENT}, got ${contextVersion ?? 'none'}. Update the Context() custom function in your solution.`}>
          Context() outdated — update to v{CONTEXT_VERSION_CURRENT}
        </span>
      )}
      {contextIndicator && (
        <span class={contextIndicator.className}>{contextIndicator.label}</span>
      )}
      {solution && <span class="text-blue-300">{solution}</span>}
      {layout && (
        <>
          <span class="text-blue-500">|</span>
          <span class="text-blue-300">{layout}</span>
        </>
      )}
    </div>
  );
}
