import type { FMContext } from '@/context/types';

interface ToolbarProps {
  context: FMContext | null;
  showXmlPreview: boolean;
  showChat: boolean;
  onToggleXmlPreview: () => void;
  onToggleChat: () => void;
  onRefreshContext: () => void;
  onNewScript: () => void;
  onValidate: () => void;
  onClipboard: () => void;
  onLoadScript: () => void;
  onOpenSettings: () => void;
}

export function Toolbar({
  context,
  showXmlPreview,
  showChat,
  onToggleXmlPreview,
  onToggleChat,
  onRefreshContext,
  onNewScript,
  onValidate,
  onClipboard,
  onLoadScript,
  onOpenSettings,
}: ToolbarProps) {
  return (
    <div class="flex items-center gap-2 px-3 py-1.5 bg-neutral-800 border-b border-neutral-700 text-sm select-none">
      <span class="font-semibold text-neutral-200">agentic-fm</span>

      <div class="h-4 w-px bg-neutral-600 mx-1" />

      <ToolbarButton onClick={onNewScript} title="Create a new script">
        New
      </ToolbarButton>

      <ToolbarButton onClick={onValidate} title="Validate XML output">
        Validate
      </ToolbarButton>

      <ToolbarButton onClick={onClipboard} title="Convert to XML and copy to clipboard">
        Clipboard
      </ToolbarButton>

      <ToolbarButton onClick={onLoadScript} title="Search and load an existing script">
        Load Script
      </ToolbarButton>

      <div class="h-4 w-px bg-neutral-600 mx-1" />

      <ToolbarButton
        onClick={onToggleXmlPreview}
        active={showXmlPreview}
        title="Toggle XML preview panel"
      >
        XML
      </ToolbarButton>

      <ToolbarButton
        onClick={onToggleChat}
        active={showChat}
        title="Toggle AI chat panel"
      >
        AI Chat
      </ToolbarButton>

      <div class="flex-1" />

      {context?.task && (
        <span class="text-neutral-400 text-xs truncate max-w-sm" title={context.task}>
          {context.task}
        </span>
      )}

      <ToolbarButton onClick={onOpenSettings} title="AI provider settings">
        Settings
      </ToolbarButton>

      <ToolbarButton onClick={onRefreshContext} title="Refresh context from CONTEXT.json">
        Refresh
      </ToolbarButton>
    </div>
  );
}

function ToolbarButton({
  onClick,
  title,
  active,
  children,
}: {
  onClick: () => void;
  title?: string;
  active?: boolean;
  children: preact.ComponentChildren;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      class={`px-2 py-0.5 rounded text-xs transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-neutral-700 hover:bg-neutral-600 text-neutral-300'
      }`}
    >
      {children}
    </button>
  );
}
